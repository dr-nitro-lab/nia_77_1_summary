from argparse import ArgumentParser
from datetime import datetime
from typing import Dict, Optional, Tuple, List
import os, glob
from pathlib import Path

import pandas as pd
import numpy as np
import librosa
import soundfile as sf
import wave

from json_utils import json2list

import cfg


def __get_indices(m2M_json: dict)->List:
    indices = [0]
    for i, cd in enumerate(m2M_json.values()):
        if i==0:
            prev_cd = cd
        if cd != prev_cd:
            indices.append(i)
            prev_cd = cd
    indices.append(i+1)
    return indices

def update_table(excel_path: str):
    """
    inputs
    --------------
    json_list :     "파일명":{json객체} 쌍으로 저장된 dictionary
    classJsons :    classJson 폴더의 json파일들을 모두 load한 dict를 입력한다. 각 파일들의 내용은 파일명으로 접근할 수 있다.
    excel_path :    if not None, excel_path에 excel 파일 저장
    """

    metadatas = json2list(cfg.DATASET_DIR)
    classJsons = json2list(cfg.CONFIG_JSONS)

    # load JSONs
    genre_cd = classJsons["genreCode2Name"].keys()
    genre_nm = classJsons["genreCode2Name"].values()

    inst_cd = classJsons["instCode2Name"].keys()
    inst_nm = classJsons["instCode2Name"].values()

    beat_cd = classJsons["beatCode2Name"].keys()
    beat_nm = classJsons["beatCode2Name"].values()

    mode_cd = classJsons["modeCode2Name"].keys()
    mode_nm = classJsons["modeCode2Name"].values()

    singleTonguing_cd = classJsons["singleTonguingCode2Name"].keys()
    singleTonguing_nm = classJsons["singleTonguingCode2Name"].values()

    # define main DataFrame
    # col이 악기 코드, row가 장르 코드인 DataFrame 생성
    table = pd.DataFrame(columns=inst_cd, index=genre_cd)
    beat_stat = pd.DataFrame(0,columns=["대분류", "time(대분류)", "ratio(%)(대분류)", "중분류",
                             "time(중분류)", "ratio(%)(중분류)", "소분류", "time", "ratio(%)"], index=beat_cd)
    mode_stat = pd.DataFrame(0,columns=["대분류", "time(대분류)", "ratio(%)(대분류)", "소분류", "Code", "time", "ratio(%)"], index=mode_cd)
    mode_stat["대분류"] = classJsons["modeCode2Major"].values()
    singleTonguing_stat = pd.DataFrame(0,columns=["대분류", "time(대분류)", "ratio(%)(대분류)", "소분류", "Code", "time", "ratio(%)"], index=singleTonguing_cd)
    singleTonguing_stat["대분류"] = classJsons["singleTonguingCode2Major"].values()


    ###########################################################################################
    # Construct main table and calculate main statistics
    for json_filename, json_dict in metadatas.items():
        try:
            wav_filename = json_dict["music_source_info"]["music_src_nm"]+'.'+json_dict["music_source_info"]["music_src_fmt"]
            wav_filepath = os.path.join(cfg.DATASET_DIR, wav_filename)
            genre = json_dict["music_type_info"]["music_genre_cd"]
            inst = json_dict["music_type_info"]["instrument_cd"]
            beat = json_dict["annotation_data_info"]["gukak_beat_cd"]
            mode = json_dict["annotation_data_info"]["mode_cd"]
            singleTonguings = json_dict["annotation_data_info"]["single_tonguing_cd"]
            # main_inst = json_dict["music_type_info"]["main_instrmt_cd"]
            wav_dur = librosa.get_duration(filename=wav_filepath)

        except FileNotFoundError:
            print(f"{wav_filepath} is not found.")
            continue

        except EOFError:
            print(f"{wav_filepath} is cannot readable.")
            continue

        except KeyError as k:
            print(f"{json_filename} don't have key '{k}'")
            continue

        # except Exception as e:
        #     print(e)

        # 현재는 "instrument_cd" 또는 "main_instrmt_cd" 둘 중 하나만 채워져 있음을 반영
        finally:
            if inst != "":
                if pd.isnull(table.loc[genre, inst]):
                    table.loc[genre, inst] = wav_dur
                else:
                    table.loc[genre, inst] += wav_dur
        #     elif main_inst != "":
        #         if pd.isnull(table.loc[genre, main_inst]):
        #             table.loc[genre, main_inst] = wav_dur
        #         else:
        #             table.loc[genre, main_inst] += wav_dur

        try:
            beat_stat.loc[beat,"time"]+=wav_dur
        except KeyError as k:
            print(f"KeyError has occured because '{json_filename}' has invalid beat code {k}")

        try:
            mode_stat.loc[mode, "time"]+=wav_dur
        except KeyError as k:
            if inst[0]!='P':
                print(f"KeyError has occured because '{json_filename}' has invalid mode code {k}, and has inst code '{inst}'")

        for singleTonguing in singleTonguings:
            try:
                if isinstance(singleTonguing["end_time"],str) or isinstance(singleTonguing["end_time"],str):
                    singleTonguing_stat.loc[singleTonguing["annotation_code"],"time"]+=(float(singleTonguing["end_time"])-float(singleTonguing["start_time"]))
                    # print(f'{json_filename} has string type of time')
                else:
                    singleTonguing_stat.loc[singleTonguing["annotation_code"],"time"]+=(singleTonguing["end_time"]-singleTonguing["start_time"])
            except KeyError as k:
                print(f"{json_filename}.json has invalid single tonguing code {singleTonguing['annotation_code']}")

    # Column Multi Index 생성
    idx=[]
    for M,m,n,c in zip(classJsons["instCode2Major"].values(),\
        classJsons["instCode2Minor"].values(),\
            classJsons["instCode2Name"].values(),\
                classJsons["instCode2Name"].keys()):
            idx.append((M,m,n,c))

    table.columns = pd.MultiIndex.from_tuples(idx, names=["대분류","중분류","악기","소분류_코드"])

    # Row Multi Index 생성
    table["대분류"]=classJsons["genreCode2Major"].values()
    table["중분류"]=classJsons["genreCode2Minor"].values()
    table["소분류(Genre)"]=classJsons["genreCode2Name"].values()
    table["분류코드"]=classJsons["genreCode2Name"].keys()
        
    # 행(장르), 열(악기)별로 total 값 구하기
    inst_wise_total = table.drop(["대분류","중분류","소분류(Genre)","분류코드"],axis=1).sum(axis=0, skipna=True)
    table.loc['total'] = inst_wise_total
    genre_wise_total = table.drop(["대분류","중분류","소분류(Genre)","분류코드"],axis=1).sum(axis=1, skipna=True)
    table['total'] = genre_wise_total

    TOTAL = int(genre_wise_total["total"])  # 전체 total

    # 행, 열별로 백분위 % ratio(%) 구하기
    print(TOTAL)
    inst_wise_ratio = inst_wise_total/TOTAL*100
    inst_wise_ratio =inst_wise_ratio.astype(float).round(decimals=2)
    table.loc['ratio(%)'] = inst_wise_ratio
    genre_wise_ratio = genre_wise_total[:-1]/TOTAL*100
    genre_wise_ratio = genre_wise_ratio.astype(float).round(decimals=2)
    table['ratio(%)'] = genre_wise_ratio

    # 열 옮기기
    for c in ["분류코드","소분류(Genre)","중분류","대분류"]:
        table.insert(0,c,table.pop(c))

    table = table.set_index(["대분류","중분류","소분류(Genre)"])
    # table.iloc[:39,1:29] = table.iloc[:39,1:29].fillna(0).astype('int')

    # 악기별 통계 테이블 만들기
    inst_stat = pd.DataFrame(0,columns=["대분류", "time(대분류)", "ratio(%)(대분류)", "중분류",
                             "time(중분류)", "ratio(%)(중분류)", "악기", "소분류_코드", "time", "ratio(%)"], index=inst_cd)
    # M stands for Major class of instrument
    # m stands for minor class of instrument
    inst_stat["악기"] = inst_nm
    inst_stat["소분류_코드"] = inst_cd
    inst_stat["중분류"] = np.array(list(classJsons["instCode2Minor"].values()))
    inst_stat["대분류"] = np.array(list(classJsons["instCode2Major"].values()))
    inst_stat["time"] = inst_wise_total.values
    inst_stat["ratio(%)"] = inst_wise_ratio.values

    # inst_stat, indices= __map_minor2major(inst_stat, "소분류_코드", "대분류", classJsons["instCode2Major"])
    indices= __get_indices(classJsons["instCode2Major"])
    for i in range(len(indices)-1):
        inst_stat.iloc[indices[i]:indices[i+1], 4] = inst_stat.iloc[indices[i]:indices[i+1]].loc[:,"time"].sum()
    inst_stat["ratio(%)(중분류)"] = (inst_stat["time(중분류)"]/TOTAL*100).astype(float).round(decimals=2)

    # inst_stat, indices= __map_minor2major(inst_stat, "소분류_코드", "대분류", classJsons["instCode2Major"])
    indices= __get_indices(classJsons["instCode2Major"])
    for i in range(len(indices)-1):
        inst_stat.iloc[indices[i]:indices[i+1], 1] = inst_stat.iloc[indices[i]:indices[i+1]].loc[:,"time"].sum()
    inst_stat["ratio(%)(대분류)"] = (inst_stat["time(대분류)"]/TOTAL*100).astype(float).round(decimals=2)

    inst_stat = inst_stat.astype({"time(대분류)":"int","time(중분류)":"int","time":"int"})
    inst_stat = inst_stat.set_index(["대분류", "time(대분류)", "ratio(%)(대분류)", "중분류", "time(중분류)", "ratio(%)(중분류)", "악기"])

    ################################################################################
    # 장르별 통계 테이블 만들기
    genre_stat = pd.DataFrame(columns=["대분류", "time(대분류)", "ratio(%)(대분류)", "중분류", "time(중분류)", "ratio(%)(중분류)", "소분류", "Code", "time", "ratio(%)"], index=genre_cd)
    genre_stat["Code"] = genre_cd
    genre_stat["소분류"] = genre_nm
    genre_stat["중분류"] = np.array(list(classJsons["genreCode2Minor"].values()))
    genre_stat["대분류"] = np.array(list(classJsons["genreCode2Major"].values()))
    genre_stat["time"] = genre_wise_total
    genre_stat["ratio(%)"] = genre_wise_ratio

    indices = __get_indices(classJsons["genreCode2Minor"])
    for i in range(len(indices)-1):
        genre_stat.iloc[indices[i]:indices[i+1], 4] = genre_stat.loc[:,"time"].iloc[indices[i]:indices[i+1]].sum()
    genre_stat["ratio(%)(중분류)"] = (genre_stat["time(중분류)"]/TOTAL*100).astype(float).round(decimals=2)

    indices = __get_indices(classJsons["genreCode2Major"])
    for i in range(len(indices)-1):
        genre_stat.iloc[indices[i]:indices[i+1], 1] = genre_stat.loc[:,"time"].iloc[indices[i]:indices[i+1]].sum()
    genre_stat["ratio(%)(대분류)"] = (genre_stat["time(대분류)"]/TOTAL*100).astype(float).round(decimals=2)

    genre_stat = genre_stat.astype({"time(대분류)":"int","time(중분류)":"int","time":"int"})
    genre_stat = genre_stat.set_index(["대분류", "time(대분류)","ratio(%)(대분류)", "중분류", "time(중분류)", "ratio(%)(중분류)", "소분류"])
    ################################################################################
    # 장단별 통계 테이블 만들기
    beat_stat["Code"] = beat_cd
    beat_stat["소분류"] = beat_nm
    beat_stat["중분류"] = np.array(list(classJsons["beatCode2Minor"].values()))
    beat_stat["대분류"] = np.array(list(classJsons["beatCode2Major"].values()))
    beat_stat["ratio(%)"] = (beat_stat["time"]/sum(beat_stat["time"])*100).astype(float).round(decimals=2)
    
    indices = __get_indices(classJsons["beatCode2Minor"])
    for i in range(len(indices)-1):
        beat_stat.iloc[indices[i]:indices[i+1], 4] = beat_stat.loc[:,"time"].iloc[indices[i]:indices[i+1]].sum()
    beat_stat["ratio(%)(중분류)"] = (beat_stat["time(중분류)"]/TOTAL*100).astype(float).round(decimals=2)

    indices = __get_indices(classJsons["beatCode2Major"])
    for i in range(len(indices)-1):
        beat_stat.iloc[indices[i]:indices[i+1], 1] = beat_stat.loc[:,"time"].iloc[indices[i]:indices[i+1]].sum()
    beat_stat["ratio(%)(대분류)"] = (beat_stat["time(대분류)"]/TOTAL*100).astype(float).round(decimals=2)

    beat_stat = beat_stat.astype({"time(대분류)":"int","time(중분류)":"int","time":"int"})
    beat_stat = beat_stat.set_index(["대분류", "time(대분류)","ratio(%)(대분류)", "중분류", "time(중분류)", "ratio(%)(중분류)", "Code", "소분류"])
    ################################################################################
    # 음조직별 통계 테이블 만들기
    mode_stat["Code"] = mode_cd
    mode_stat["소분류"] = mode_nm
    mode_stat["대분류"] = np.array(list(classJsons["modeCode2Major"].values()))
    mode_stat["ratio(%)"] = (mode_stat["time"]/sum(mode_stat["time"])*100).astype(float).round(decimals=2)

    indices = __get_indices(classJsons["modeCode2Major"])
    for i in range(len(indices)-1):
        mode_stat.iloc[indices[i]:indices[i+1],1] = mode_stat.loc[:,"time"].iloc[indices[i]:indices[i+1]].sum()
    mode_stat["ratio(%)(대분류)"] = (mode_stat["time(대분류)"]/TOTAL*100).astype(float).round(decimals=2)

    mode_stat = mode_stat.set_index(["대분류", "time(대분류)", "ratio(%)(대분류)", "소분류"])
    ################################################################################
    # 시김새별 통계 테이블 만들기
    singleTonguing_stat["Code"] = singleTonguing_cd
    singleTonguing_stat["소분류"] = singleTonguing_nm
    singleTonguing_stat["대분류"] = np.array(list(classJsons["singleTonguingCode2Major"].values()))
    singleTonguing_stat["ratio(%)"] = (singleTonguing_stat["time"]/sum(singleTonguing_stat["time"])*100).astype(float).round(decimals=2)

    indices = __get_indices(classJsons["singleTonguingCode2Major"])
    for i in range(len(indices)-1):
        singleTonguing_stat.iloc[indices[i]:indices[i+1], 1] = singleTonguing_stat.loc[:,"time"].iloc[indices[i]:indices[i+1]].sum()
    singleTonguing_stat.loc[:,"ratio(%)(대분류)"] = (singleTonguing_stat["time(대분류)"]/TOTAL*100).astype(float).round(decimals=2)

    singleTonguing_stat = singleTonguing_stat.set_index(["대분류", "time(대분류)", "ratio(%)(대분류)", "소분류"])
    ###################################################################################
    # save
    with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
        table.to_excel(writer, sheet_name="장르악기분포집계")
        inst_stat.to_excel(writer, sheet_name="악기분포집계")
        genre_stat.to_excel(writer, sheet_name="장르분포집계")
        singleTonguing_stat.to_excel(writer, sheet_name="시김새분포집계")
        beat_stat.to_excel(writer, sheet_name="장단분포집계")
        mode_stat.to_excel(writer, sheet_name="음조직분포집계")


if __name__ == "__main__":
    excel_dir = Path(cfg.DATASET_DIR).name
    if not os.path.exists(excel_dir):
        os.mkdir(excel_dir)

    excel_path = os.path.join(excel_dir,f'{excel_dir}.time.xlsx')

    update_table(excel_path)