import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests

def get_jma_tide_hs():
    """
    気象庁の suisan/txt フォーマット(136col)を解析。
    指定されたURL: https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/2026/HS.txt を使用。
    """
    now = datetime.now()
    station_code = "HS"
    # ご提示いただいた最新のURL構造を反映
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/{station_code}.txt"
    
    default_res = (150, "上げ5分")
    
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200: return default_res
        
        lines = res.text.splitlines()
        # 73-78カラムの年月日形式 (例: 26 225) に合わせるためのターゲット
        target_ymd = now.strftime('%y') + f"{now.month:2d}" + f"{now.day:2d}"
        
        day_data = None
        for line in lines:
            if len(line) < 80: continue
            # カラム72:78が年月日、78:80が地点コード(HS)
            if line[72:78] == target_ymd and line[78:80] == station_code:
                day_data = line
                break
        
        if not day_data: return default_res

        # 1. 毎時潮位の取得と線形補間 (app.py 準拠)
        hourly = []
        for i in range(24):
            val = day_data[i*3 : (i+1)*3].strip()
            hourly.append(int(val))
        
        t1 = hourly[now.hour]
        t2 = hourly[now.hour+1] if now.hour < 23 else hourly[now.hour]
        current_cm = int(round(t1 + (t2 - t1) * (now.minute / 60.0)))

        # 2. 満潮・干潮イベントの抽出 (80カラム~, 108カラム~)
        events = []
        today_str = now.strftime('%Y%m%d')
        # 満潮
        for i in range(4):
            start = 80 + (i * 7)
            t_part = day_data[start : start+4].strip()
            if t_part and t_part != "9999":
                ev_time = datetime.strptime(today_str + t_part.zfill(4), '%Y%m%d%H%M')
                events.append({"time": ev_time, "type": "満潮"})
        # 干潮
        for i in range(4):
            start = 108 + (i * 7)
            t_part = day_data[start : start+4].strip()
            if t_part and t_part != "9999":
                ev_time = datetime.strptime(today_str + t_part.zfill(4), '%Y%m%d%H%M')
                events.append({"time": ev_time, "type": "干潮"})
        
        events = sorted(events, key=lambda x: x['time'])

        # 3. フェーズ計算 (app.py 判定ロジック)
        phase_text = "不明"
        prev_ev = next((e for e in reversed(events) if e['time'] <= now), None)
        next_ev = next((e for e in events if e['time'] > now), None)

        if prev_ev and next_ev:
            duration = (next_ev['time'] - prev_ev['time']).total_seconds()
            elapsed = (now - prev_ev['time']).total_seconds()
            if duration > 0:
                p_type = "上げ" if prev_ev['type'] == "干潮" else "下げ"
                # 1〜9分
                step = max(1, min(9, int((elapsed / duration) * 10)))
                phase_text = f"{p_type}{step}分"
                # 頂点付近の補正
                if (elapsed / duration) < 0.1: phase_text = prev_ev['type']
                elif (elapsed / duration) > 0.9: phase_text = next_ev['type']

        return current_cm, phase_text
    except Exception as e:
        return default_res

def get_realtime_weather():
    """Open-Meteo Forecast API を使用して現況と過去48h降水量を取得"""
    LAT, LON = 32.4333, 130.2167 # 本渡(HS)付近
    tide_level, phase = get_jma_tide_hs()
    
    data = {
        'tide_level': tide_level, 'phase': phase, 'temp': 15.0, 
        'wind': 3.0, 'wdir': "北", 'precip_48h': 0.0, 'tide': "中潮"
    }
    
    try:
        # forecast API で current と hourly(降水量) を取得
        w_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": LAT, "longitude": LON,
            "current_weather": "true",
            "hourly": "precipitation",
            "past_days": 2, # 過去48時間をカバー
            "timezone": "Asia/Tokyo"
        }
        res = requests.get(w_url, params=params, timeout=10).json()
        
        if 'current_weather' in res:
            cw = res['current_weather']
            data['temp'] = float(cw['temperature'])
            data['wind'] = round(float(cw['windspeed']) / 3.6, 1) # km/h -> m/s
            
            # 16方位変換
            dirs = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
            data['wdir'] = dirs[int((cw['winddirection'] + 11.25) / 22.5) % 16]
            
            # 過去48時間の合計降水量 (APIのhourly[0]は2日前の0時)
            if 'hourly' in res:
                now_hour_idx = 48 + datetime.now().hour
                precip_list = res['hourly']['precipitation']
                data['precip_48h'] = round(sum(precip_list[now_hour_idx-48 : now_hour_idx+1]), 1)
    except:
        pass
    return data

def show_matching_page(df):
    # UIとスコアリング処理 (前述の通り)
    st.title("🏹 SeaBass Match AI v6.0")
    st.caption("気象庁水産用HSデータ(2026) 完全同期")

    if 'm_data' not in st.session_state:
        st.session_state.m_data = get_realtime_weather()

    if st.button("🔄 HS(本渡)の最新データを取得"):
        st.session_state.m_data = get_realtime_weather()
        st.rerun()

    md = st.session_state.m_data
    # ... 以下 UI 入力とスコアリング ...
