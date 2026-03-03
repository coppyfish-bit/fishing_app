import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import numpy as np

# --- 1. 設定 ---
st.set_page_config(page_title="Tide Debug Mode", layout="wide")

st.title("🌊 潮位解析デバッグモード")

# 観測所定義
TIDE_STATIONS = [
    {"name": "苓北", "lat": 32.4667, "lon": 130.0333, "code": "RH"},
    {"name": "三角", "lat": 32.6167, "lon": 130.4500, "code": "MS"},
    {"name": "本渡瀬戸", "lat": 32.4333, "lon": 130.2167, "code": "HS"},
    # ...他は適宜追加
]

# --- 2. 関数定義 (デバッグ用に詳細を表示) ---
def get_tide_details_debug(station_code, dt):
    try:
        base_dt = datetime.strptime(dt.strftime('%Y%m%d%H%M'), '%Y%m%d%H%M')
        st.write(f"### 🔍 解析対象日時: {base_dt}")
        st.write(f"### 📍 観測所コード: {station_code}")
        
        target_ymd = base_dt.strftime('%y') + f"{base_dt.month:02d}" + f"{base_dt.day:02d}"
        
        # URL生成 (年は現在年を使用しているため、過去データの場合は修正が必要)
        year = base_dt.year
        url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{year}/{station_code}.txt"
        st.write(f"### 🌐 データURL: {url}")
        
        res = requests.get(url, timeout=10)
        st.write(f"### 📡 HTTPステータス: {res.status_code}")
        
        if res.status_code != 200:
            st.error("気象庁データ取得失敗")
            return None
        
        lines = res.text.splitlines()
        day_data = None
        
        # データ行を探す
        for line in lines:
            if len(line) < 80: continue
            if line[72:78] == target_ymd and line[78:80] == station_code:
                day_data = line
                break
        
        if not day_data:
            st.error(f"❌ 該当する日のデータが見つかりません。")
            st.write(f"検索キー(YMD): {target_ymd}")
            return None
        
        st.success("✅ データ行を発見しました。")
        st.code(day_data)

        # 毎時潮位の取得
        hourly = []
        for i in range(24):
            val = day_data[i*3 : (i+1)*3].strip()
            hourly.append(int(val))
        
        # 潮位計算
        t1 = hourly[base_dt.hour]
        t2 = hourly[base_dt.hour+1] if base_dt.hour < 23 else hourly[base_dt.hour]
        current_cm = int(round(t1 + (t2 - t1) * (base_dt.minute / 60.0)))
        
        st.write(f"### 📈 計算された潮位: {current_cm} cm")

        # 潮汐イベントロジック
        event_times = []
        today_ymd = base_dt.strftime('%Y%m%d')

        # 満潮抽出
        for i in range(4):
            start = 80 + (i * 7)
            t_part = day_data[start : start+4].replace(" ", "")
            if t_part and t_part.isdigit() and t_part != "9999":
                ev_time = datetime.strptime(today_ymd + t_part.zfill(4), '%Y%m%d%H%M')
                event_times.append({"time": ev_time, "type": "満潮"})

        # 干潮抽出
        for i in range(4):
            start = 108 + (i * 7)
            t_part = day_data[start : start+4].replace(" ", "")
            if t_part and t_part.isdigit() and t_part != "9999":
                ev_time = datetime.strptime(today_ymd + t_part.zfill(4), '%Y%m%d%H%M')
                event_times.append({"time": ev_time, "type": "干潮"})

        event_times = sorted(event_times, key=lambda x: x['time'])
        st.write("### ⏱️ 潮汐イベント:")
        st.write(event_times)
        
        return {"cm": current_cm, "events": event_times}

    except Exception as e:
        st.error(f"❌ 致命的エラー: {e}")
        return None

# --- 3. UI部 ---
with st.sidebar:
    st.header("パラメータ設定")
    station_name = st.selectbox("観測所", [s['name'] for s in TIDE_STATIONS])
    selected_date = st.date_input("日付", datetime.now())
    selected_time = st.time_input("時刻", datetime.now().time())
    
    analyze_btn = st.button("潮位解析実行")

if analyze_btn:
    target_dt = datetime.combine(selected_date, selected_time)
    station_code = next(s['code'] for s in TIDE_STATIONS if s['name'] == station_name)
    
    get_tide_details_debug(station_code, target_dt)
