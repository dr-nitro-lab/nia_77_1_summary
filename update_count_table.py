from typing import Dict, Optional, Tuple, List

import pandas as pd
import numpy as np

from json_utils import json2list

from pathlib import Path
import os
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

def update_table(excel_path:str):
    """
    inputs
    --------------
    json_list :     "파일명":{json객체} 쌍으로 저장된 dictionary
    classJsons :      classJson 폴더의 json파일들을 모두 load한 dict를 입력한다. 각 파일들의 내용은 파일명으로 접근할 수 있다.
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
    total_table = pd.DataFrame(0,columns=inst_cd, index=genre_cd)
    beat_stat = pd.DataFrame(0,columns=["대분류", "count(대분류)", "ratio(%)(대분류)", "중분류",
                             "count(중분류)", "ratio(%)(중분류)", "소분류", "count", "ratio(%)"], index=beat_cd)
    mode_stat = pd.DataFrame(0,columns=["대분류", "count(대분류)", "ratio(%)(대분류)", "소분류", "Code", "count", "ratio(%)"], index=mode_cd)
    mode_stat["대분류"] = classJsons["modeCode2Major"].values()
    singleTonguing_stat = pd.DataFrame(0,columns=["대분류", "count(대분류)", "ratio(%)(대분류)", "소분류", "Code", "count", "ratio(%)"], index=singleTonguing_cd)
    singleTonguing_stat["대분류"] = classJsons["singleTonguingCode2Major"].values()

    ###########################################################################################
    # Construct main table and calculate main statistics
    for json_filename, json_dict in metadatas.items():
        try:
            genre = json_dict["music_type_info"]["music_genre_cd"]
            inst = json_dict["music_type_info"]["instrument_cd"]
            beat = json_dict["annotation_data_info"]["gukak_beat_cd"]
            mode = json_dict["annotation_data_info"]["mode_cd"]
            singleTonguings = json_dict["annotation_data_info"]["single_tonguing_cd"]

        except KeyError as k:
            print(f"{json_filename} don't have key '{k}'")
            continue  # do something when wrong key detected!!

        total_table.loc[genre, inst] += 1
        
        try:
            beat_stat.loc[beat, "count"]+=1
        except KeyError as k:
            print(f"KeyError : '{json_filename}.json' has invalid beat code {k}")

        try:
            mode_stat.loc[mode, "count"]+=1
        except KeyError as k:
            if inst[0]!='P':
                # 악기코드가 P(타악기)로 시작하면 mode code는 empty string '' 여야 한다.
                # 그 외의 경우에 empty string은 허용되지 않는다.
                print(f"KeyError : '{json_filename}.json' has invalid mode code {k}, and has inst code '{inst}' (empty mode code is not permitted except for 'P(타악기)')")

        for singleTonguing in singleTonguings:
            try:
                singleTonguing_stat.loc[singleTonguing["annotation_code"], "count"]+=1
            except KeyError as k:
                print(f"KeyError : '{json_filename}.json' has invalid single tonguing code {singleTonguing['annotation_code']}")


    # Column Multi Index 생성
    idx=[]
    for M,m,n,c in zip(classJsons["instCode2Major"].values(),\
        classJsons["instCode2Minor"].values(),\
            classJsons["instCode2Name"].values(),\
                classJsons["instCode2Name"].keys()):
        idx.append((M,m,n,c))

    total_table.columns = pd.MultiIndex.from_tuples(idx, names=["대분류","중분류","악기","소분류_코드"])

    # 행(장르), 열(악기)별로 total 값 구하기
    inst_wise_total = total_table.sum(axis=0, skipna=True)
    genre_wise_total = total_table.sum(axis=1, skipna=True).astype('int16')

    # Row Multi Index 생성
    total_table["대분류"]=classJsons["genreCode2Major"].values()
    total_table["중분류"]=classJsons["genreCode2Minor"].values()
    total_table["소분류(Genre)"]=classJsons["genreCode2Name"].values()
    total_table["분류코드"]=classJsons["genreCode2Name"].keys()
        
    total_table.loc['total'] = inst_wise_total
    total_table['total'] = genre_wise_total

    TOTAL = genre_wise_total.sum() # 전체 total

    # 행, 열별로 백분위 % ratio(%) 구하기
    inst_wise_ratio = inst_wise_total/TOTAL*100
    inst_wise_ratio =inst_wise_ratio.astype(float).round(decimals=2)
    total_table.loc['ratio(%)'] = inst_wise_ratio
    genre_wise_ratio = genre_wise_total/TOTAL*100
    genre_wise_ratio = genre_wise_ratio.astype(float).round(decimals=2)
    total_table['ratio(%)'] = genre_wise_ratio

    # 열 옮기기
    for c in ["분류코드","소분류(Genre)","중분류","대분류"]:
        total_table.insert(0,c,total_table.pop(c))

    total_table=total_table.set_index(["대분류","중분류","소분류(Genre)"])

    ################################################################################
    # 악기별 통계 테이블 만들기
    inst_stat = pd.DataFrame(columns=["대분류", "count(대분류)", "ratio(%)(대분류)", "중분류",
                             "count(중분류)", "ratio(%)(중분류)", "악기", "소분류_코드", "count", "ratio(%)"], index=inst_cd)
    # M stands for Major class of instrument
    # m stands for minor class of instrument
    inst_stat["악기"] = inst_nm
    inst_stat["소분류_코드"] = inst_cd
    inst_stat["중분류"] = np.array(list(classJsons["instCode2Minor"].values()))
    inst_stat["대분류"] = np.array(list(classJsons["instCode2Major"].values()))
    inst_stat["count"] = inst_wise_total.values
    inst_stat["ratio(%)"] = inst_wise_ratio.values

    indices= __get_indices(classJsons["instCode2Major"])
    for i in range(len(indices)-1):
        inst_stat.iloc[indices[i]:indices[i+1], 4] = inst_stat.iloc[indices[i]:indices[i+1], 8].sum()
    inst_stat["ratio(%)(중분류)"] = (inst_stat["count(중분류)"]/TOTAL*100).astype(float).round(decimals=2)

    indices= __get_indices(classJsons["instCode2Major"])
    for i in range(len(indices)-1):
        inst_stat.iloc[indices[i]:indices[i+1], 1] = inst_stat.iloc[indices[i]:indices[i+1], 8].sum()
    inst_stat["ratio(%)(대분류)"] = (inst_stat["count(대분류)"]/TOTAL*100).astype(float).round(decimals=2)

    inst_stat = inst_stat.set_index(["대분류", "count(대분류)", "ratio(%)(대분류)", "중분류", "count(중분류)", "ratio(%)(중분류)", "악기"])

    ################################################################################
    # 장르별 통계 테이블 만들기
    genre_stat = pd.DataFrame(columns=["대분류", "count(대분류)", "ratio(%)(대분류)", "중분류", "count(중분류)", "ratio(%)(중분류)", "소분류", "Code", "count", "ratio(%)"], index=genre_cd)
    genre_stat["Code"] = genre_cd
    genre_stat["소분류"] = genre_nm
    genre_stat["중분류"] = np.array(list(classJsons["genreCode2Minor"].values()))
    genre_stat["대분류"] = np.array(list(classJsons["genreCode2Major"].values()))
    genre_stat["count"] = genre_wise_total
    genre_stat["ratio(%)"] = genre_wise_ratio

    indices = __get_indices(classJsons["genreCode2Minor"])
    for i in range(len(indices)-1):
        genre_stat.iloc[indices[i]:indices[i+1], 4] = genre_stat.iloc[indices[i]:indices[i+1], 8].sum()
    genre_stat["ratio(%)(중분류)"] = (genre_stat["count(중분류)"]/TOTAL*100).astype(float).round(decimals=2)

    indices = __get_indices(classJsons["genreCode2Major"])
    for i in range(len(indices)-1):
        genre_stat.iloc[indices[i]:indices[i+1], 1] = genre_stat.iloc[indices[i]:indices[i+1], 8].sum()
    genre_stat["ratio(%)(대분류)"] = (genre_stat["count(대분류)"]/TOTAL*100).astype(float).round(decimals=2)

    genre_stat = genre_stat.set_index(["대분류", "count(대분류)","ratio(%)(대분류)", "중분류", "count(중분류)", "ratio(%)(중분류)", "소분류"])
    ################################################################################
    # 장단별 통계 테이블 만들기
    beat_stat["Code"] = beat_cd
    beat_stat["소분류"] = beat_nm
    beat_stat["중분류"] = np.array(list(classJsons["beatCode2Minor"].values()))
    beat_stat["대분류"] = np.array(list(classJsons["beatCode2Major"].values()))
    beat_stat["ratio(%)"] = (beat_stat["count"]/sum(beat_stat["count"])*100).astype(float).round(decimals=2)

    indices = __get_indices(classJsons["beatCode2Minor"])
    for i in range(len(indices)-1):
        beat_stat.iloc[indices[i]:indices[i+1], 4] = beat_stat.loc[:,"count"].iloc[indices[i]:indices[i+1]].sum()
    beat_stat["ratio(%)(중분류)"] = (beat_stat["count(중분류)"]/TOTAL*100).astype(float).round(decimals=2)

    indices = __get_indices(classJsons["beatCode2Major"])
    for i in range(len(indices)-1):
        beat_stat.iloc[indices[i]:indices[i+1], 1] = beat_stat.loc[:,"count"].iloc[indices[i]:indices[i+1]].sum()
    beat_stat["ratio(%)(대분류)"] = (beat_stat["count(대분류)"]/TOTAL*100).astype(float).round(decimals=2)

    beat_stat = beat_stat.set_index(["대분류", "count(대분류)","ratio(%)(대분류)", "중분류", "count(중분류)", "ratio(%)(중분류)", "Code", "소분류"])
    ################################################################################
    # 음조직별 통계 테이블 만들기
    mode_stat["Code"] = mode_cd
    mode_stat["소분류"] = mode_nm
    mode_stat["대분류"] = np.array(list(classJsons["modeCode2Major"].values()))
    mode_stat["ratio(%)"] = (mode_stat["count"]/sum(mode_stat["count"])*100).astype(float).round(decimals=2)

    indices = __get_indices(classJsons["modeCode2Major"])
    for i in range(len(indices)-1):
        mode_stat.iloc[indices[i]:indices[i+1], 1] = mode_stat.iloc[indices[i]:indices[i+1], 5].sum()
    mode_stat["ratio(%)(대분류)"] = (mode_stat["count(대분류)"]/TOTAL*100).astype(float).round(decimals=2)

    mode_stat = mode_stat.set_index(["대분류", "count(대분류)", "ratio(%)(대분류)", "소분류"])
    ################################################################################
    # 시김새별 통계 테이블 만들기
    singleTonguing_stat["Code"] = singleTonguing_cd
    singleTonguing_stat["소분류"] = singleTonguing_nm
    singleTonguing_stat["대분류"] = np.array(list(classJsons["singleTonguingCode2Major"].values()))
    singleTonguing_stat["ratio(%)"] = (singleTonguing_stat["count"]/sum(singleTonguing_stat["count"])*100).astype(float).round(decimals=2)

    indices = __get_indices(classJsons["singleTonguingCode2Major"])
    for i in range(len(indices)-1):
        singleTonguing_stat.iloc[indices[i]:indices[i+1], 1] = singleTonguing_stat.iloc[indices[i]:indices[i+1], 5].sum()
    singleTonguing_stat["ratio(%)(대분류)"] = (singleTonguing_stat["count(대분류)"]/TOTAL*100).astype(float).round(decimals=2)

    singleTonguing_stat = singleTonguing_stat.set_index(["대분류", "count(대분류)", "ratio(%)(대분류)", "소분류"])
    ###################################################################################
    # save
    with pd.ExcelWriter(excel_path, engine='xlsxwriter') as writer:
        total_table.to_excel(writer, sheet_name="장르악기분포집계")
        inst_stat.to_excel(writer, sheet_name="악기분포집계")
        genre_stat.to_excel(writer, sheet_name="장르분포집계")
        singleTonguing_stat.to_excel(writer, sheet_name="시김새분포집계")
        beat_stat.to_excel(writer, sheet_name="장단분포집계")
        mode_stat.to_excel(writer, sheet_name="음조직분포집계")


if __name__ == "__main__":
    excel_dir = Path(cfg.DATASET_DIR).name
    if not os.path.exists(excel_dir):
        os.mkdir(excel_dir)

    excel_path = os.path.join(excel_dir,f'{excel_dir}.count.xlsx')

    update_table(excel_path)