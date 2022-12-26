import os, glob
import mido
import soundfile as sf
import pandas as pd
import cfg
import json_utils
from pathlib import Path


def mismatch_error_tables():
    channel_error = pd.DataFrame(columns=["json","wav"])
    sample_rate_error = pd.DataFrame(columns=["json","wav"])
    bit_depth_error = pd.DataFrame(columns=["json","wav"])
    play_time_error = pd.DataFrame(columns=["json","wav"])

    wav_open_error = pd.DataFrame(columns=["msg"])

    JSON_FILES = glob.glob(os.path.join(cfg.DATASET_DIR, "*.json"))

    WAV_FILES = glob.glob(os.path.join(cfg.DATASET_DIR, "*.wav"))

    # fields to be checked
    # play_time, samplingRate, bitDepth, channel
    for JSON_FILE in JSON_FILES:
        # load json & wav files on memory
        FILE = Path(JSON_FILE).stem
        WAV_FILE = JSON_FILE.replace(".json", ".wav")

        if WAV_FILE in WAV_FILES:
            try:
                with sf.SoundFile(WAV_FILE) as sf_reader:
                    sampling_rate_wav=sf_reader.samplerate
                    duration_wav = sf_reader.frames/sampling_rate_wav
                    channel_wav=sf_reader.channels
                    subtype = sf_reader.subtype
                    bitDepth_wav = 24 if subtype=="PCM_24" else 16 if subtype=="PCM_16" else 32
            except Exception as e:
                # 1 : pcm
                # 3 : ieee float
                # 65534 : extensible
                print(e)
                wav_open_error = pd.concat([wav_open_error,pd.DataFrame({"msg":e},index=[FILE])])
                continue
        else:
            print(f"{WAV_FILE} not found!")
            continue

        JSON = json_utils.loadjson(JSON_FILE)
        try: # json의 파라미터 가져오기
            channel_json = 1 if JSON["music_source_info"]["channel"]=="M" else 2 if JSON["music_source_info"]["channel"]=="S" else -1
            sampling_rate_json = JSON["music_source_info"]["samplingRate"]
            duration_json = JSON["music_source_info"]["play_time"]
            bitDepth_json = JSON["music_source_info"]["bitDepth"]
        except KeyError as k:
            print(f"{JSON_FILE} don't have key {k}")
            channel_error = pd.concat([channel_error, pd.DataFrame({"json":f"don't have key {k}","wav":channel_wav},index=[FILE])])
            sample_rate_error = pd.concat([sample_rate_error, pd.DataFrame({"json":f"don't have key {k}","wav":sampling_rate_wav},index=[FILE])])
            play_time_error = pd.concat([play_time_error, pd.DataFrame({"json":f"don't have key {k}","wav":duration_wav},index=[FILE])])
            bit_depth_error = pd.concat([bit_depth_error, pd.DataFrame({"json":f"don't have key {k}","wav":bitDepth_wav},index=[FILE])])
            continue

        # compare json & wav
        if channel_wav != channel_json:
            channel_error = pd.concat([channel_error, pd.DataFrame({"json":channel_json,"wav":channel_wav},index=[FILE])])
        # if (duration_wav - duration_json) > cfg.DURATION_TOLERANCE: # 1초 이상 차이나면 다른 것으로 판단
        if round(duration_wav) != round(duration_json): # 정수로 rounding 했을 때 같은지/다른지 판단
            play_time_error = pd.concat([play_time_error, pd.DataFrame({"json":duration_json,"wav":duration_wav},index=[FILE])])
        if sampling_rate_wav != sampling_rate_json:
            sample_rate_error = pd.concat([sample_rate_error, pd.DataFrame({"json":sampling_rate_json,"wav":sampling_rate_wav},index=[FILE])])
        if bitDepth_wav != bitDepth_json:
            bit_depth_error = pd.concat([bit_depth_error, pd.DataFrame({"json":bitDepth_json,"wav":bitDepth_wav},index=[FILE])])



    bpm_error = pd.DataFrame(columns=["json","mid"])
    MIDI_FILES = glob.glob(os.path.join(cfg.DATASET_DIR, "*.mid"))
    for JSON_FILE in JSON_FILES:
        # load json & wav files on memory
        FILE = Path(JSON_FILE).stem
        if Path(cfg.DATASET_DIR).stem == "221011" and FILE in ["AP_C11_01549","AP_F02_00331"]:
            print("invlid file", FILE)
            continue

        MIDI_FILE = JSON_FILE.replace(".json", ".mid")
        if MIDI_FILE in MIDI_FILES:
            midi = mido.MidiFile(MIDI_FILE)
            for msg in midi:
                if msg.type=='set_tempo':
                    bpm_midi = mido.tempo2bpm(msg.tempo)
                    break
        else:
            print(f"{MIDI_FILE} not found!")
            continue

        JSON = json_utils.loadjson(JSON_FILE)
        try:
            bpm_json = JSON["annotation_data_info"]["tempo"][0]["annotation_code"]
        except KeyError as k:
            print(f"{JSON_FILE} don't have key {k}")
            bpm_error = pd.concat([bpm_error, pd.DataFrame({"json":f"don't have key {k}","mid":bpm_midi},index=[FILE])])
            continue
        except IndexError as i:
            print(f"{JSON_FILE}'s tempo field is empty")
            bpm_error = pd.concat([bpm_error, pd.DataFrame({"json":"tempo field is empty","mid":bpm_midi},index=[FILE])])
            continue

        # compare json & wav
        try:
            if (bpm_midi - bpm_json) > cfg.BPM_TOLERANCE:
                bpm_error = pd.concat([bpm_error, pd.DataFrame({"json":bpm_json,"mid":bpm_midi},index=[FILE])])
        except TypeError as t:
            print(JSON_FILE, f"has None value in ['annotation_data_info']['tempo'][0]['annotation_code'] field")
            bpm_error = pd.concat([bpm_error, pd.DataFrame({"json":"None","mid":bpm_midi},index=[FILE])])
            continue
    
    return channel_error, sample_rate_error, bit_depth_error, play_time_error, bpm_error, wav_open_error




if __name__=="__main__":
    channel_error, sample_rate_error, bit_depth_error, play_time_error, bpm_error, wav_open_error = mismatch_error_tables()

    excel_dir = Path(cfg.DATASET_DIR).name
    if not os.path.exists(excel_dir):
        os.mkdir(excel_dir)
    excel_path = os.path.join(excel_dir,f'{Path(cfg.DATASET_DIR).name}.error_mismatch.xlsx')

    with pd.ExcelWriter(path=excel_path) as writer:
        channel_error.to_excel(writer,sheet_name="channel")
        sample_rate_error.to_excel(writer,sheet_name="sample_rate")
        bit_depth_error.to_excel(writer,sheet_name="bit_depth")
        play_time_error.to_excel(writer,sheet_name="play_time")
        bpm_error.to_excel(writer,sheet_name="bpm")
        wav_open_error.to_excel(writer,sheet_name="wav_open_error")