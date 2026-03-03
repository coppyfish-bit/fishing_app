import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import re

def get_nearest_tide(date, station_code):
    station_code = station_code.upper()
    
    # --- 1. データ取得 ---
    url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{date.year}/{station_code}.txt"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200: return "取得失敗", None
        
        lines = res.text.splitlines()
        yy = date.strftime('%y')
        pattern = rf"{yy}\s+{date.month}\s+{date.day}\s*{station_code}"
        
        target_line = None
        for line in lines:
            if re.search(pattern, line):
                target_line = line
                break
        
        if not target_line: return "該当日なし", None

        # --- 2. 毎時潮位の塊を24個抽出 ---
        # 地点記号(HS)より前にある数値をすべて抜き出す
        pos_code = target_line.find(station_code)
        hourly_nums = re.findall(r'-?\d+', target_line[:pos_code])
        
        if len(hourly_nums) < 24: return "データ欠損", None
        
        # --- 3. 最も近い時間のインデックスを特定 ---
        # 10:30未満なら10時、10:30以上なら11時を「最も近い」とする
        if date.minute < 30:
            nearest_hour = date.hour
        else:
            nearest_hour = (date.hour + 1) % 24
            
        nearest_cm = int(hourly_nums[nearest_hour])
        return nearest_cm, nearest_hour

    except:
        return "解析エラー", None

# --- UI部 ---
st.title("🌊 本渡瀬戸・直近潮位ピンポイント抽出")

code = st.text_input("地点", "HS").upper()
now = datetime.now()

if st.button("🔥 現在の直近潮位を奪取"):
    cm, hour = get_nearest_tide(now, code)
    
    if isinstance(cm, int):
        # ど真ん中に大きく表示
        st.markdown(f"### 🎯 現在時刻 {now.strftime('%H:%M')} に最も近い潮位")
        st.metric(label=f"{hour}:00 の観測値", value=f"{cm} cm")
        
        st.info(f"💡 30分単位で四捨五入し、{hour}時ちょうどのデータを採用した。")
    else:
        st.error(f"エラー: {cm}")
