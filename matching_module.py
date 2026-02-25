import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import requests

def get_jma_tide_hs():
    """気象庁の地点コード'HS'(本渡)から天文潮位を同期"""
    now = datetime.now()
    year = now.year
    # 本渡(HS)の予測データURL
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/pre/txt/{year}/HS.txt"
    
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            lines = response.text.splitlines()
            # 行インデックスは「日 - 1」
            day_line = lines[now.day - 1]
            
            # 1時間ごとの潮位(3桁)が24時間分並んでいる
            hour_tides = []
            for i in range(24):
                start = 3 + i * 3
                val = day_line[start:start+3].strip()
                hour_tides.append(int(val) if val else 0)
            
            curr_h = hour_tides[now.hour]
            next_h = hour_tides[(now.hour + 1) % 24]
            
            # --- 精密フェーズ判定 ---
            t_max, t_min = max(hour_tides), min(hour_tides)
            rel_pos = (curr_h - t_min) / (t_max - t_min) if (t_max - t_min) != 0 else 0.5
            status = "上げ" if next_h > curr_h else "下げ"
            
            # 0~100%を9分割して「○分」を計算
            p_val = int(rel_pos * 9) + 1 if status == "上げ" else int((1 - rel_pos) * 9) + 1
            phase = f"{status}{min(max(p_val, 1), 9)}分"
            
            if rel_pos > 0.97: phase = "満潮"
            elif rel_pos < 0.03: phase = "干潮"
            
            return curr_h, phase
    except Exception as e:
        return 160, "上げ5分" # 取得失敗時のデフォルト

def get_realtime_weather():
    """HS潮位 + Open-Meteo気象を統合"""
    tide_level, phase = get_jma_tide_hs()
    
    # 苓北・本渡エリアの座標
    LAT, LON = 32.4333, 130.2167
    data = {'tide': "中潮", 'temp': 15.0, 'wind': 3.0, 'wdir': "北", 
            'tide_level': tide_level, 'phase': phase, 'precip_48h': 0.0}
    
    try:
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current_weather=true&hourly=precipitation&past_days=2&timezone=Asia%2FTokyo"
        w_res = requests.get(w_url, timeout=5).json()
        if 'current_weather' in w_res:
            cw = w_res['current_weather']
            data['temp'] = float(cw.get('temperature', 15.0))
            data['wind'] = float(cw.get('windspeed', 3.0))
            # 風向 8方位変換
            directions = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
            data['wdir'] = directions[int((cw.get('winddirection', 0) + 22.5) / 45) % 8]
            # 48時間降水量（現在から遡る）
            if 'hourly' in w_res:
                h_idx = 48 + datetime.now().hour
                p_list = w_res['hourly'].get('precipitation', [0.0]*72)
                data['precip_48h'] = round(sum(p_list[h_idx-48:h_idx+1]), 1)
    except: pass
    return data

def show_matching_page(df):
    st.markdown("""
        <style>
        .stButton>button { background-color: #ff4b6c; color: white; border-radius: 25px; border: none; padding: 12px; font-weight: bold; width: 100%; }
        .input-card { background-color: #1e1e1e; padding: 20px; border-radius: 15px; border: 1px solid #333; margin-bottom: 20px; }
        .recommend-card { background: linear-gradient(135deg, #2c3e50 0%, #000000 100%); padding: 20px; border-radius: 15px; border-left: 5px solid #ff4b6c; margin-bottom: 15px; color: white; position: relative; }
        .score-badge { position: absolute; top: 20px; right: 20px; font-size: 1.8rem; font-weight: bold; color: #ff4b6c; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🏹 SeaBass Match AI v4.5")
    st.caption("地点：本渡(HS) / 気象庁データ完全同期")

    if 'm_data' not in st.session_state:
        st.session_state.m_data = get_realtime_weather()

    st.markdown("<div class='input-card'>", unsafe_allow_html=True)
    if st.button("🔄 HS(本渡)の潮汐・気象を同期"):
        st.session_state.m_data = get_realtime_weather()
        st.toast("気象庁HS地点のデータを読み込みました")
        st.rerun()

    md = st.session_state.m_data
    c1, c2 = st.columns(2)
    with c1:
        tide_in = st.selectbox("潮名", ["大潮", "中潮", "小潮", "長潮", "若潮"], index=1)
        level_in = st.number_input("潮位 (cm)", value=int(md['tide_level']))
        temp_in = st.number_input("気温 (℃)", value=float(md['temp']))
    with c2:
        p_list = ["上げ1分","上げ3分","上げ5分","上げ7分","上げ9分","満潮","下げ1分","下げ3分","下げ5分","下げ7分","下げ9分","干潮"]
        phase_in = st.selectbox("潮位フェーズ", p_list, index=p_list.index(md['phase']) if md['phase'] in p_list else 2)
        wdir_in = st.selectbox("風向", ["北", "北東", "東", "南東", "南", "南西", "西", "北西"], index=["北", "北東", "東", "南東", "南", "南西", "西", "北西"].index(md['wdir']))
        wind_in = st.number_input("風速 (m/s)", value=float(md['wind']))
    precip_in = st.number_input("48h降水量合計 (mm)", value=float(md['precip_48h']))
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("🎯 独自優先順位でランキング診断"):
        if df is not None and not df.empty:
            df['is_bouzu'] = df['魚種'].astype(str).str.contains('ボウズ', na=False)
            results = []
            for place in df['場所'].unique():
                p_df = df[df['場所'] == place]
                success_df = p_df[~p_df['is_bouzu']]
                if not success_df.empty:
                    # --- 🥇 スコア計算（優先順位：フェーズ > 潮位 > 風向 > 気温 > 他） ---
                    # 1. フェーズ(35)
                    s_phase = 35 if not success_df[success_df['潮位フェーズ'] == phase_in].empty else 0
                    # 2. 潮位(25) - ±15cm
                    s_level = 25 if not success_df[abs(success_df.get('潮位_cm',0) - level_in) <= 15].empty else 0
                    # 3. 風向き(15)
                    s_wdir = 15 if not success_df[success_df['風向'] == wdir_in].empty else 0
                    # 4. 気温(10) - ±3度
                    s_temp = 10 if not success_df[abs(success_df['気温'] - temp_in) <= 3].empty else 0
                    # 5. その他(15: 各5)
                    s_others = (5 if not success_df[success_df['潮名'] == tide_in].empty else 0) + \
                               (5 if not success_df[abs(success_df['風速'] - wind_in) <= 2].empty else 0) + \
                               (5 if not success_df[abs(success_df.get('48時間降水量',0) - precip_in) <= 10].empty else 0)
                    
                    total = min(s_phase + s_level + s_wdir + s_temp + s_others, 99)
                    lure_mode = success_df['ルアー'].dropna().mode()
                    results.append({'place': place, 'score': total, 'hits': len(success_df), 'lure': lure_mode[0] if not lure_mode.empty else "未登録"})
            
            results = sorted(results, key=lambda x: x['score'], reverse=True)
            for i, res in enumerate(results):
                st.markdown(f"<div class='recommend-card'><div class='score-badge'>{res['score']}%</div><b>{i+1}位: {res['place']}</b><br>過去実績: {res['hits']}件 / 推奨: {res['lure']}</div>", unsafe_allow_html=True)
