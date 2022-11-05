# nia_77_1

## json metadata 형식 무결성 확인방법
### 1) `cfg.py` 의 변수들을 설정한다. 
- `DATASET_DIR` : 데이터셋이 있는 폴더의 경로를 `DATASET_DIR`에 입력
- `CONFIG_JSONS` : 각 장르와 악기에 대한 코드와 분류를 서로 mapping한 json 파일을 모아둔 폴더. 이 repository를 clone 하여 그대로 사용한다면 바꾸지 않아도 된다.
- `STD_JSON` : key값이 다른 json들과 다르지 않으면서, 최대한 모든 key를 포함하는 json 파일을 선정한다. 여기서는 `single_tonguing_cd`, `tempo`, `lyrics` 모두에 대해 annotation을 가지는 AP_C11_01566.json을 선정했다.
```python
# dataset이 있는 directory의 경로
DATASET_DIR = "./221011"

# 분야, 악기 관련 코드에 대한 json파일들이 있는 directory의 경로
CONFIG_JSONS = "./classJson"

# json 파일의 무결성을 체크할때 비교기준으로 사용할 파일
STD_JSON = os.path.join(DATASET_DIR, "AP_C11_01566.json")
```

### 2) check_integrity.ipynb의 셀들을 순차적으로 실행시킨다.

## json과 wav, mid 데이터의 일치 확인방법
### 1) json, wav, mid 파일이 있는 폴더를 cfg.py 설정파일의 `DATASET_DIR` 변수에 설정한다.
### 2) `crossCheck_json_and_data.py`를 실행시키면 확인을 진행한 directory 내의 `Errors.txt`가 저장된 것을 확인할 수 있다.
- 이때 json의 무결성이 지켜지지 않은 경우의 에러는 터미널에 출력한다.
#### json과 wav
- json에 기록된 재생시간, sample rate, bit depth(wav의 subtype), channel 수가 wav파일과 일치하는지 확인한다.
- json에 기록된 재생시간과 wav의 실제 재생시간을 비교할때, 허용 가능한 차이를 `cfg.py` 의 `DURATION_TOLERANCE` 변수로 설정한다.
- wav 파일 자체의 문제로 열리지 않는 경우의 에러는 터미널에 출력한다.
#### json과 mid
- json에 기록된 tempo가 mid 파일의 bpm과 일치하는지 확인한다.
- json에 기록된 tempo와 mid 파일의 bpm 차이를 얼마나 허용할 것인지는 설정파일 `cfg.py` 의 `BPM_TOLERANCE`변수로 설정한다.

## error, count, time 테이블 생성방법
### 1) 위와 같은 방식으로 `cfg.py` 의 변수들을 설정한다.

### 2) error, count, time 테이블을 생성하기 위해 
- Windows에서 실행할 경우 update_table.bat을 실행시킨다.
- Linux 또는 git bash 에서 실행할 경우에는 update_table.sh를 실행시킨다.
- 또는 update_time_table.py, update_error_table.py, update_count_table.py 를 각각 실행시켜도 된다.

## 실행결과 터미널 출력 및 생성된 테이블(*.xlsx) 보는법
### 1) error table
- 누락 파일 목록 : 하나의 데이터에 대해 wav, json, mid 파일이 모두 있어야 누락되지 않은 것으로 간주한다. 밑의 예시는 AP_F02_00332.wav, AP_F02_00332.mid 는 존재하지만 AP_F02_00332.json은 존재하지 않는 경우

![image](https://user-images.githubusercontent.com/54995090/197339674-27db3564-e881-4227-8491-678882d9e863.png)

- 에러 json파일 목록 : key 값이 다른 json파일들의 형식과 다른 경우. check_integrity.ipynb 에서 확인한 결과와 동일하다.

![image](https://user-images.githubusercontent.com/54995090/197339682-296fa8f2-8899-4a54-9d81-8dafb82caada.png)



### 2) count table
다음과 같은 에러가 발생하는 경우 터미널에 에러를 출력하고, count 집계에 반영하지 않았다.
- json 키값이 다른 json 파일들과 다르거나 누락된 경우
- json에 기록된 beat(장단), mode(음조직), singleTonguing(시김새) 코드가 잘못된 경우


### 3) time table
다음과 같은 에러가 발생하는 경우 터미널에 에러를 출력하고, time 집계에 반영하지 않았다.
- json 파일에 대응되는 wav 파일이 존재하지 않는 경우
- json 파일에 필요한 key 값이 없는 경우
- json에 기록된 beat(장단), mode(음조직), singleTonguing(시김새) 코드가 잘못된 경우
- wav 파일이 열리지 않는 경우

![image](https://user-images.githubusercontent.com/54995090/197447272-97c6afc8-14d0-4318-a9c0-bbaea3606ba2.png)

- 위에서 cannot readable은 wav 파일이 읽히지 않는 경우이고, KeyError에 의한 오류메시지는 별도로 표시하였다. json 형식이 다른 파일에서 KeyError가 발생한다. 
