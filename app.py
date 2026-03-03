import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import re

def get_tide_data_final_fix(date, station_code):
    station_code = station_code.upper()
    
    def fetch_day_data(d):
        # 2026年などのディレクトリ構造に対応
        url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{d.year}/{station_code}.txt"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code != 200: return None, []
            
            lines = res.text.splitlines()
            # 日付パターン: 2桁の年、1-2桁の月、1-2桁の日 + 地点記号
            # 例: "26  3  3HS" や "26 03 03HS" に対応
            yy = d.strftime('%y')
            pattern = rf"{yy}\s+{d.month}\s+{d.day}\s*{station_code}"
            
            target_line = None
            for line in lines:
                if re.search(pattern, line):
                    target_line = line
                    break
            
            if not target_line: return None, []

            # --- 基準点（地点記号）の特定 ---
            # 仕様書では地点記号は79-80カラム。ここを基準に前後を切り出す。
            pos_code = target_line.find(station_code)
            if pos_code < 70: # 異常に手前にある場合はスキップ
                 return None, []

            # 1. 毎時潮位 (地点記号の78文字前から24個の3桁数値)
            # 1-72カラム相当。地点記号(79-80)の直前までが年月日。
            hourly_part = target_line[:72]
            hourly_tides = []
            for i in range(0, 72, 3):
                val = hourly_part[i:i+3].strip()
                if val: hourly_tides.append(int(val))
            
            # 2. 満干潮イベント (地点記号の直後から)
            base_idx = pos_code + len(station_code)
            day_events = []
            d_str = d.strftime('%Y%m%d')

            # 満潮 (地点記号の直後 28文字)
            high_part = target_line[base_idx : base_idx + 28]
            for i in range(0, 28, 7):
                t, h = high_part[i:i+4].strip(), high_part[i+4:i+7].strip()
                if t and t != "9999":
                    day_events.append({
                        "time": datetime.strptime(d_str + t.zfill(4), '%Y%m%d%H%M'),
                        "type": "満潮", "cm": int(h)
                    })

            # 干潮 (満潮の直後 28文字)
            low_part = target_line[base_idx + 28 : base_idx + 56]
            for i in range(0, 28, 7):
                t, l = low_part[i:i+4].strip(), low_part[i+4:i+7].strip()
                if t and t != "9999":
                    day_events.append({
                        "time": datetime.strptime(d_str + t.zfill(4), '%Y%m%d%H%M'),
                        "type": "干潮", "cm": int(l)
                    })
            
            return hourly_tides, day_events
        except:
            return None, []

    # 三日分（前・今・後）の統合
    all_events = []
    today_hourly = None
    for i in [-1, 0, 1]:
        d = date + timedelta(days=i)
        h, e = fetch_day_data(d)
        if i == 0: today_hourly = h
        all_events.extend(e)
    
    all_events.sort(key=lambda x: x['time'])

    # 現在潮位の計算
    current_cm = None
    if today_hourly and len(today_hourly) >= 24:
        h_idx = date.hour
        t1 = today_hourly[h_idx]
        t2 = today_hourly[h_idx + 1] if h_idx < 23 else today_hourly[h_idx]
        current_cm = int(round(t1 + (t2 - t1) * (date.minute / 60.0)))

    # 直前・直後特定
    prev = next((e for e in reversed(all_events) if e['time'] <= date), None)
    nxt = next((e for e in all_events if e['time'] > date), None)

    return {"current": current_cm, "prev": prev, "next": nxt, "all": all_events}

# --- 表示部 ---
st.title("🌊 潮位・満干潮 最終補正システム")
code = st.text_input("地点コード (例: HS)", "HS").upper()
target_dt = datetime.now()

if st.button("🔥 解析実行"):
    res = get_tide_data_final_fix(target_dt, code)
    if res["all"]:
        col1, col2, col3 = st.columns(3)
        col1.metric("現在潮位", f"{res['current']} cm")
        if res["prev"]:
            col2.metric("🎯 直前", f"{res['prev']['type']}", f"{res['prev']['time'].strftime('%m/%d %H:%M')} ({res['prev']['cm']}cm)")
        if res["next"]:
            col3.metric("⌛ 次", f"{res['next']['type']}", f"{res['next']['time'].strftime('%m/%d %H:%M')} ({res['next']['cm']}cm)")
        
        st.table(pd.DataFrame(res["all"]).assign(時刻=lambda x: x['time'].dt.strftime('%m/%d %H:%M'))
