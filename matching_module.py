import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import requests

def get_jma_tide_hs():
    """
    気象庁の潮汐データ(HS:本渡)を解析して、現在の潮位とフェーズを返します。
    """
    now = datetime.now()
    station_code = "HS"
    # 2026年のデータURL
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/{station_code}.txt"
    
    # 万が一取得できなかった場合のデフォルト値
    default_res = (150, "取得失敗")
    
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            return default_res
        
        lines = res.text.splitlines()
        
        # 1. 今日のデータ行を特定
        # フォーマット: 73-75(年2桁), 76-77(月), 78-79(日)
        target_y = now.strftime('%y')
        target_m = now.strftime('%m')
        target_d = now.strftime('%d')
        
        day_line = None
        for line in lines:
            if len(line) < 80: continue
            line_y = line[72:75].strip().zfill(2)
            line_m = line[75:77].strip().zfill(2)
            line_d = line[77:79].strip().zfill(2)
            
            if line_y == target_y and line_m == target_m and line_d == target_d:
                day_line = line
                break
        
        if not day_line:
            return default_res

        # 2. 毎時潮位の取得 (1-72カラム、3文字ずつ24時間分)
        hourly = []
        for i in range(24):
            val_str = day_line[i*3 : (i+1)*3].strip()
            # 空欄や異常値のハンドリング
            hourly.append(int(val_str) if val_str and val_str != "" else 0)
        
        # 現在時刻の潮位を線形補間
        t1 = hourly[now.hour]
        t2 = hourly[now.hour+1] if now.hour < 23 else hourly[now.hour]
        current_cm = int(round(t1 + (t2 - t1) * (now.minute / 60.0)))

        # 3. 満潮・干潮時刻を抽出してフェーズ判定
        events = []
        today_str = now.strftime('%Y%m%d')
        
        # 満潮(80-107), 干潮(108-135) 各4つずつ
        for start_idx, ev_type in [(80, "満潮"), (108, "干潮")]:
            for i in range(4):
                pos = start_idx + (i * 7)
                t_part = day_line[pos : pos+4].strip()
                if t_part and t_part != "9999" and len(t_part) == 4:
                    ev_time = datetime.strptime(today_str + t_part, '%Y%m%d%H%M')
                    events.append({"time": ev_time, "type": ev_type})
        
        events = sorted(events, key=lambda x: x['time'])

        # フェーズ判定ロジック
        phase_text = "解析中"
        prev_ev = next((e for e in reversed(events) if e['time'] <= now), None)
        next_ev = next((e for e in events if e['time'] > now), None)

        if prev_ev and next_ev:
            duration = (next_ev['time'] - prev_ev['time']).total_seconds()
            elapsed = (now - prev_ev['time']).total_seconds()
            p_type = "上げ" if prev_ev['type'] == "干潮" else "下げ"
            step = max(1, min(9, int((elapsed / duration) * 10)))
            phase_text = f"{p_type}{step}分"
            
            # 潮止まり付近の表現
            ratio = elapsed / duration
            if ratio < 0.1: phase_text = prev_ev['type']
            elif ratio > 0.9: phase_text = next_ev['type']
        elif prev_ev: # 次のイベントが明日になる場合
            phase_text = f"{prev_ev['type']}直後"

        return current_cm, phase_text
    except Exception as e:
        print(f"Error in tide fetch: {e}")
        return default_res

def get_realtime_weather():
    """気象データと潮汐データを統合して取得"""
    # 本渡(HS)の座標
    LAT, LON = 32.4333, 130.2167 
    tide_level, phase = get_jma_tide_hs()
    
    data = {
        'tide_level': tide_level, 'phase': phase, 'temp': 15.0, 
        'wind': 3.0, 'wdir': "北", 'precip_48h': 0.0, 'tide': "中潮"
    }
    
    try:
        w_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": LAT, "longitude": LON,
            "current_weather": "true", "hourly": "precipitation",
            "past_days": 2, "timezone": "Asia/Tokyo"
        }
        res = requests.get(w_url, params=params, timeout=10).json()
        
        if 'current_weather' in res:
            cw = res['current_weather']
            data['temp'] = float(cw['temperature'])
            data['wind'] = round(float(cw['windspeed']) / 3.6, 1)
            dirs = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
            data['wdir'] = dirs[int((cw['winddirection'] + 11.25) / 22.5) % 16]
            
            if 'hourly' in res:
                # 現在時刻に合わせた降水量の抽出
                now_hour = datetime.now().hour
                precip_list = res['hourly']['precipitation']
                # 過去48時間分のインデックス(簡易版)
                data['precip_48h'] = round(sum(precip_list[48:48+now_hour]), 1)
    except:
        pass
    return data


def show_matching_page(df):
    """マッチングメイン画面"""
    st.markdown("""
        <style>
        .stButton>button { background-color: #ff4b6c; color: white; border-radius: 25px; border: none; padding: 12px; font-weight: bold; width: 100%; }
        .input-card { background-color: #1e1e1e; padding: 20px; border-radius: 15px; border: 1px solid #333; margin-bottom: 20px; }
        .recommend-card { background: linear-gradient(135deg, #2c3e50 0%, #000000 100%); padding: 20px; border-radius: 15px; border-left: 5px solid #ff4b6c; margin-bottom: 15px; color: white; position: relative; }
        .score-badge { position: absolute; top: 20px; right: 20px; font-size: 1.8rem; font-weight: bold; color: #ff4b6c; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🏹 SeaBass Match AI v6.3")
    st.caption("JMA(HS)実測データ解析モード")

    if 'm_data' not in st.session_state:
        st.session_state.m_data = get_realtime_weather()

    st.markdown("<div class='input-card'>", unsafe_allow_html=True)
    if st.button("🔄 海況・潮汐データを同期"):
        st.session_state.m_data = get_realtime_weather()
        st.rerun()

    md = st.session_state.m_data
    c1, c2 = st.columns(2)
    with c1:
        tide_name_in = st.selectbox("潮名", ["大潮", "中潮", "小潮", "長潮", "若潮"], index=1)
        level_in = st.number_input("潮位 (cm)", value=int(md.get('tide_level', 150)))
        temp_in = st.number_input("気温 (℃)", value=float(md.get('temp', 15.0)))
    with c2:
        p_list = ["上げ1分","上げ2分","上げ3分","上げ4分","上げ5分","上げ6分","上げ7分","上げ8分","上げ9分","満潮",
                  "下げ1分","下げ2分","下げ3分","下げ4分","下げ5分","下げ6分","下げ7分","下げ8分","下げ9分","干潮"]
        cur_p = md.get('phase', '上げ5分')
        p_idx = p_list.index(cur_p) if cur_p in p_list else 4
        phase_in = st.selectbox("潮位フェーズ", p_list, index=p_idx)
        
        wdir_list = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
        cur_wdir = md.get('wdir', '北')
        wdir_in = st.selectbox("風向", wdir_list, index=wdir_list.index(cur_wdir) if cur_wdir in wdir_list else 0)
        wind_in = st.number_input("風速 (m/s)", value=float(md.get('wind', 3.0)))
    
    precip_in = st.number_input("48h降水量合計 (mm)", value=float(md.get('precip_48h', 0.0)))
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("🎯 エリア診断ランキング"):
        if df is not None and not df.empty:
            df['is_bouzu'] = df['魚種'].astype(str).str.contains('ボウズ', na=False)
            results = []
            for place in df['場所'].unique():
                p_df = df[df['場所'] == place]
                success_df = p_df[~p_df['is_bouzu']]
                if not success_df.empty:
                    # スコア計算
                    s_phase = 35 if not success_df[success_df['潮位フェーズ'] == phase_in].empty else 0
                    s_level = 25 if not success_df[abs(success_df.get('潮位_cm', 0) - level_in) <= 15].empty else 0
                    s_wdir = 15 if not success_df[success_df['風向'] == wdir_in].empty else 0
                    s_temp = 10 if not success_df[abs(success_df['気温'] - temp_in) <= 3].empty else 0
                    s_others = (5 if not success_df[success_df['潮名'] == tide_name_in].empty else 0) + \
                               (5 if not success_df[abs(success_df['風速'] - wind_in) <= 2].empty else 0) + \
                               (5 if '降水量' in success_df.columns and not success_df[abs(success_df['降水量'] - precip_in) <= 10].empty else 0)
                    
                    total = min(s_phase + s_level + s_wdir + s_temp + s_others, 99)
                    lure_mode = success_df['ルアー'].dropna().mode()
                    results.append({'place': place, 'score': total, 'hits': len(success_df), 'lure': lure_mode[0] if not lure_mode.empty else "データ不明"})
            
            results = sorted(results, key=lambda x: x['score'], reverse=True)
            for i, res in enumerate(results):
                st.markdown(f"<div class='recommend-card'><div class='score-badge'>{res['score']}%</div><b>{i+1}位: {res['place']}</b><br>成功実績: {res['hits']}件 / 推奨: {res['lure']}</div>", unsafe_allow_html=True)

