import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import re

def get_tide_data_complete(date, station_code):
    """
    気象庁の仕様書に基づき、地点記号を基準にデータを切り出す最終奥義。
    前・今・明の3日分を連結して、直前・直後のイベントを特定する。
    """
    station_code = station_code.upper()
    
    def fetch_day_data(d):
        url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{d.year}/{station_code}.txt"
        try:
            res = requests.get(url, timeout=5)
            if res.status_code != 200: return None, []
            
            lines = res.text.splitlines()
            # 日付と地点記号で対象の行を特定（正規表現でスペースの揺らぎを吸収）
            pattern = rf"{d.strftime('%y')}\s+{d.month}\s+{d.day}\s*{station_code}"
            target_line = next((l for l in lines if re.search(pattern, l)), None)
            
            if not target_line: return None, []

            # --- 1. 毎時潮位の抽出 (1-72カラム) ---
            # 3桁×24時間。地点記号の場所に関わらず、行の先頭72文字をスライス
            hourly_tides = []
            for i in range(0, 72, 3):
                val = target_line[i:i+3].strip()
                if val: hourly_tides.append(int(val))

            # --- 2. 満干潮イベントの抽出 (地点記号の直後から) ---
            # 地点記号の位置を基準にする (仕様書: 81カラム目から満潮)
            base_idx = target_line.find(station_code) + len(station_code)
            day_events = []
            d_str = d.strftime('%Y%m%d')

            # 満潮 (4ペア: 28文字)
            high_part = target_line[base_idx : base_idx + 28]
            for i in range(0, 28, 7):
                t, h = high_part[i:i+4].strip(), high_part[i+4:i+7].strip()
                if t != "9999" and t != "":
                    day_events.append({
                        "time": datetime.strptime(d_str + t.zfill(4), '%Y%m%d%H%M'),
                        "type": "満潮", "cm": int(h)
                    })

            # 干潮 (4ペア: 28文字)
            low_part = target_line[base_idx + 28 : base_idx + 56]
            for i in range(0, 28, 7):
                t, l = low_part[i:i+4].strip(), low_part[i+4:i+7].strip()
                if t != "9999" and t != "":
                    day_events.append({
                        "time": datetime.strptime(d_str + t.zfill(4), '%Y%m%d%H%M'),
                        "type": "干潮", "cm": int(l)
                    })
            
            return hourly_tides, day_events
        except:
            return None, []

    # 三日分のデータを取得・統合
    all_hourly = {} # 日付をキーにした毎時潮位
    all_events = []
    for i in [-1, 0, 1]:
        target_d = date + timedelta(days=i)
        h, e = fetch_day_data(target_d)
        if h: all_hourly[target_d.date()] = h
        all_events.extend(e)
    
    all_events.sort(key=lambda x: x['time'])

    # 現在の潮位（線形補間）
    current_cm = None
    today_h = all_hourly.get(date.date())
    if today_h:
        h_idx = date.hour
        t1 = today_h[h_idx]
        t2 = today_h[h_idx + 1] if h_idx < 23 else today_h[h_idx]
        current_cm = int(round(t1 + (t2 - t1) * (date.minute / 60.0)))

    # 直前・直後イベントの特定
    prev_ev = next((e for e in reversed(all_events) if e['time'] <= date), None)
    next_ev = next((e for e in all_events if e['time'] > date), None)

    return {
        "current_cm": current_cm,
        "prev": prev_ev,
        "next": next_ev,
        "all_events": all_events,
        "hourly": today_h
    }

# --- Streamlit 表示用デバッグセクション ---
st.title("🌊 潮位・満干潮 最終解析システム")

code = st.text_input("地点コード", "HS").upper()
now = datetime.now()

if st.button("🔥 データを全抽出する"):
    data = get_tide_data_complete(now, code)
    
    if data["hourly"]:
        c1, c2, c3 = st.columns(3)
        c1.metric("現在の潮位", f"{data['current_cm']} cm")
        
        if data["prev"]:
            c2.metric("🎯 直前のイベント", f"{data['prev']['type']}", 
                      f"{data['prev']['time'].strftime('%H:%M')} ({data['prev']['cm']}cm)")
        
        if data["next"]:
            c3.metric("⌛ 次のイベント", f"{data['next']['type']}", 
                      f"{data['next']['time'].strftime('%H:%M')} ({data['next']['cm']}cm)")

        st.markdown("### 📋 三日間の連結イベント表")
        df = pd.DataFrame(data["all_events"])
        df['時刻'] = df['time'].dt.strftime('%m/%d %H:%M')
        st.table(df[['時刻', 'type', 'cm']].rename(columns={'type':'種別', 'cm':'潮位(cm)'}))
    else:
        st.error("データが取得できませんでした。地点コードや日付を確認せよ。")
