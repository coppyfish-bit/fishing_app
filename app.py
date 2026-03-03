import streamlit as st
import requests
from datetime import datetime
import re

def get_perfect_hourly_tide(date, station_code):
    station_code = station_code.upper()
    url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{date.year}/{station_code}.txt"
    
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200: return "取得失敗", None
        
        lines = res.text.splitlines()
        # 日付と地点記号で行を特定
        yy = date.strftime('%y')
        pattern = rf"{yy}\s+{date.month}\s+{date.day}\s*{station_code}"
        
        target_line = None
        for line in lines:
            if re.search(pattern, line):
                target_line = line
                break
        
        if not target_line: return "該当日なし", None

        # --- 仕様書通り：1〜72カラムを3文字ずつ分断 ---
        hourly_data = []
        for i in range(24):
            # 0時(0-3カラム), 1時(3-6カラム)... 
            # Pythonのスライスは [start:end] なので [0:3], [3:6] となる
            start = i * 3
            end = start + 3
            val_str = target_line[start:end].strip()
            if val_str:
                hourly_data.append(int(val_str))
            else:
                hourly_data.append(0) # 万が一空なら0

        # --- 最も近い時間を判定 ---
        # 10:29なら10時、10:30なら11時
        if date.minute < 30:
            nearest_hour = date.hour
        else:
            nearest_hour = (date.hour + 1) % 24
            
        return hourly_data[nearest_hour], nearest_hour

    except Exception as e:
        return f"解析エラー: {e}", None

# --- UI部 ---
st.title("🌊 本渡瀬戸・3桁固定長 潮位奪取")

code = st.text_input("地点", "HS").upper()
now = datetime.now()

if st.button("🔥 現在時刻の潮位をピンポイントで引く"):
    cm, hour = get_perfect_hourly_tide(now, code)
    
    if isinstance(cm, int):
        st.markdown(f"### 🎯 基準時刻: {now.strftime('%H:%M')}")
        st.metric(label=f"【{hour}:00】の観測潮位", value=f"{cm} cm")
        st.caption(f"※仕様書に基づき、1〜72カラムから3桁ごとに抽出しました。")
    else:
        st.error(f"エラー: {cm}")
