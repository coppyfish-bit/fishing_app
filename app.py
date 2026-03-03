import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import re

def get_tide_data_perfect(date, station_code):
    station_code = station_code.upper()
    
    def fetch_day_data(d):
        url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{d.year}/{station_code}.txt"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code != 200: return None, []
            
            lines = res.text.splitlines()
            # 日付パターン: "26 3 3HS" 等を探す
            yy = d.strftime('%y')
            pattern = rf"{yy}\s+{d.month}\s+{d.day}\s*{station_code}"
            
            target_line = None
            for line in lines:
                if re.search(pattern, line):
                    target_line = line
                    break
            
            if not target_line: return None, []

            # --- 基準点（地点記号）からの抽出 ---
            pos_code = target_line.find(station_code)
            
            # 1. 毎時潮位の抽出（地点記号の「直前」にある日付データの、さらに「左側」にあるはず）
            # 仕様書では1-72カラム。つまり地点記号(79-80)より前の72文字。
            # 確実を期すため、行の先頭から72文字を抜き出し、数字以外を排除して24個取る
            hourly_raw = target_line[:pos_code] # 地点記号より前をすべて取得
            # 日付部分（YY MM DD）を末尾から削る（約6〜8文字分）
            # だが、3文字ずつのスライスなら、先頭から72文字（24個分）取るのが最も安全
            hourly_tides = []
            for i in range(0, 72, 3):
                val = target_line[i:i+3].strip()
                if val:
                    try:
                        hourly_tides.append(int(val))
                    except:
                        continue # 数字じゃない場合は飛ばす
            
            # 2. 満干潮イベント（地点記号の「右側」）
            base_idx = pos_code + len(station_code)
            day_events = []
            d_str = d.strftime('%Y%m%d')

            # 満潮(28文字) + 干潮(28文字)
            event_part = target_line[base_idx : base_idx + 56]
            for i in range(0, 56, 7):
                t, cm = event_part[i:i+4].strip(), event_part[i+4:i+7].strip()
                if t and t != "9999":
                    etype = "満潮" if i < 28 else "干潮"
                    day_events.append({
                        "time": datetime.strptime(d_str + t.zfill(4), '%Y%m%d%H%M'),
                        "type": etype, "cm": int(cm)
                    })
            
            return hourly_tides, day_events
        except:
            return None, []

    # 三日分統合
    all_events = []
    today_h = None
    for i in [-1, 0, 1]:
        d = date + timedelta(days=i)
        h, e = fetch_day_data(d)
        if i == 0: today_h = h
        all_events.extend(e)
    
    all_events.sort(key=lambda x: x['time'])

    # 現在潮位の計算
    current_cm = "取得失敗"
    if today_h and len(today_h) >= 24:
        h_idx = date.hour
        t1 = today_h[h_idx]
        t2 = today_h[h_idx+1] if h_idx < 23 else today_h[h_idx]
        current_cm = int(round(t1 + (t2 - t1) * (date.minute / 60.0)))

    return {
        "current": current_cm,
        "prev": next((e for e in reversed(all_events) if e['time'] <= date), None),
        "next": next((e for e in all_events if e['time'] > date), None),
        "all": all_events
    }

# --- 表示部 ---
st.title("🌊 本渡瀬戸・完全攻略システム")
code = st.text_input("地点", "HS").upper()
if st.button("🔥 最終解析"):
    res = get_tide_data_perfect(datetime.now(), code)
    if res["all"]:
        st.metric("現在の潮位", f"{res['current']} cm")
        st.table(pd.DataFrame(res["all"]).assign(時刻=lambda x: x['time'].dt.strftime('%m/%d %H:%M')))
    else:
        st.error("データ解析不能。")
