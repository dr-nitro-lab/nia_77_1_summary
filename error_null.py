from json_utils import *
import matplotlib.pyplot as plt
import cfg
from typing import List, Dict, Union, Optional
import numpy as np
import os
import pandas as pd
from pathlib import Path

"""
추가고려사항
--------------------------
midi_status, score_status, lyrics_status(v)의 진위여부 검증
json으로 존재하는 code들 유효한지 검증 (시김새)
"""

class InvalidCounter:
    def __init__(self):
        self.num_null: Dict[str,Union[List[dict],List[str]]] = dict()
        self.keys_to_be_checked = ['gukak_beat_cd', 'music_genre_cd', 'instrument_cd', 'mode_cd', 'lyrics_status', 'midi_status']
        self.valid_beat_cd = list(loadjson('classJson/beatCode2Name.json').keys())
        self.valid_genre_cd = list(loadjson('classJson/genreCode2Name.json').keys())
        self.valid_inst_cd = list(loadjson('classJson/instCode2Name.json').keys())
        self.valid_mode_cd = list(loadjson('classJson/modeCode2Name.json').keys())

    def add_key(self, key):
        if key not in self.num_null.keys():
            self.num_null[key]=[]

    def check_null(self, key, val, json_name, parent:Optional[str]=None):
        if key=='tempo':
            if val == None or len(val)==0:
                val = "None" if val==None else "empty_string" if val=="" else val
                self.num_null[key].append({"name":json_name, key: val})
        elif val==None or val=='':
            if key=='mode_cd':
                # mode_cd 는 타악기(P)일 때 공란임을 고려.
                json_path = os.path.join(cfg.DATASET_DIR,json_name+".json")
                json_obj = loadjson(json_path)
                if json_obj['music_type_info']['instrument_cd'][0] == 'P':
                    return
            else:
                val = "None" if val==None else "empty_string" if val=="" else val
                if parent is not None:
                    val += f'({parent})'
                if {"name":json_name, key: val} not in self.num_null[key]:
                    self.num_null[key].append({"name":json_name, key: val})
        elif key in self.keys_to_be_checked:
            if key=='gukak_beat_cd':
                if val not in self.valid_beat_cd:
                    self.num_null[key].append({"name":json_name, key: val})
            elif key=='music_genre_cd':
                if val not in self.valid_genre_cd:
                    self.num_null[key].append({"name":json_name, key: val})
            elif key=='instrument_cd':
                if val not in self.valid_inst_cd:
                    self.num_null[key].append({"name":json_name, key: val})
            elif key=='mode_cd':
                if val not in self.valid_mode_cd:
                    self.num_null[key].append({"name":json_name, key: val})
            elif key=='lyrics_status':
                json_path = os.path.join(cfg.DATASET_DIR,json_name+".json")
                json_obj = loadjson(json_path)
                if val == 'Y' and len(json_obj['annotation_data_info']['lyrics'])==0:
                    self.num_null[key].append({"name":json_name, key: 'Y', "num_annotations": len(json_obj['annotation_data_info']['lyrics'])})
                elif val == 'N' and len(json_obj['annotation_data_info']['lyrics'])>0:
                    self.num_null[key].append({"name":json_name, key: 'N', "num_annotations": len(json_obj['annotation_data_info']['lyrics'])})
            elif key=='midi_status':
                if val=='N':
                    self.num_null[key].append({"name":json_name, key: val})
            

    def plot(self):
        key_names: List[str] = []
        num_absence: List[int] = []
        for k, v in self.num_null.items():
            key_names.append(k)
            num_absence.append(len(v))

        idx = np.arange(len(key_names))
        plt.bar(idx, num_absence)
        plt.xticks(idx, key_names, rotation=90)
        plt.show()

    def to_excel(self):
        excel_dir = Path(cfg.DATASET_DIR).name
        if not os.path.exists(excel_dir):
            os.mkdir(excel_dir)
        excel_path = os.path.join(excel_dir,f'{Path(cfg.DATASET_DIR).name}.error_empty_or_invalid_value.xlsx')
        with pd.ExcelWriter(path=excel_path, engine='xlsxwriter',mode='w') as writer:
            for key,vals in self.num_null.items():
                if len(vals)>0:
                    if isinstance(vals[0],Dict):
                        null_list = pd.DataFrame.from_records(data=vals)
                    else:
                        null_list = pd.DataFrame(vals)
                    null_list.to_excel(writer,sheet_name=key)

def detect_null():
    counter = InvalidCounter()
    std_json = loadjson(cfg.STD_JSON)
    for k1,v1 in std_json.items():
        counter.add_key(k1)
        for k2,v2 in v1.items():
            counter.add_key(k2)
            if isinstance(v2,List):
                for v2_5 in v2:
                    for k3,v3 in v2_5.items():
                        counter.add_key(k3)

    json_files = json2list(cfg.DATASET_DIR)
    for name, json_dict in json_files.items():
        for k1,v1 in json_dict.items():
            counter.check_null(k1, v1, name)
            for k2,v2 in v1.items():
                counter.check_null(k2, v2, name)
                if isinstance(v2,List):
                    for v2_5 in v2:
                        for k3,v3 in v2_5.items():
                            counter.check_null(k3, v3, name, parent=k2)

    # counter.plot()
    counter.to_excel()


if __name__=="__main__":
    detect_null()