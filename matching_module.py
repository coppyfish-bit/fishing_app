import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import requests

def get_realtime_weather():
    """本渡瀬戸の現況（潮位・フェーズ・気象）を動的補正して同期"""
    LAT, LON = 32.4333, 130.2167
    now = datetime.now()
    data = {'tide': "中潮", 'temp': 15.0, 'wind': 3.0, 'wdir': "北", 'tide_level': 100, 'phase': "上げ5分", 'precip_48h': 0.0}
    
    try:
        # 1. 気象予報 (気温・風向・風速・48h降雨)
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current_weather=true&hourly=precipitation&past_days=2&timezone=Asia%2FTokyo"
        w_res = requests.get(w_url, timeout=5).json()
        if 'current_weather' in w_res:
            cw = w_res['current_weather']
            data['temp'] = float(cw.get('temperature', 15.0))
            data['wind'] = float(cw.get('windspeed', 3.0))
            # 風向 8方位変換
            directions = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
            data['wdir'] = directions[int((cw.get('winddirection', 0) + 22.5) / 45) % 8]
            # 48時間降水量合計
            if 'hourly' in w_res:
                p_list = w_res['hourly'].get('precipitation', [0.0]*72)
                data['precip_48h'] = round(sum(p_list[now.hour : now.hour+48]), 1)

        # 2. 潮汐 (sea_level_height) の動的解析
        t_url = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT}&longitude={LON}&hourly=sea_level_height&timezone=Asia%2FTokyo"
        t_res = requests.get(t_url, timeout=5).json()
        if 'hourly' in t_res:
            h_list = t_res['hourly'].get('sea_level_height', [0.0]*24)
            current_h = h_list[now.hour]
            next_h = h_list[(now.hour + 1) % 24]
            
            # --- 精密フェーズ計算 ---
            # 24時間内の満潮(max)と干潮(min)を特定
            t_max, t_min = max(h_list), min(h_list)
            range_h = t_max - t_min
            # 現在の高さが干満のどの位置にあるか (0.0~1.0)
            rel_pos = (current_h - t_min) / range_h if range_h != 0 else 0.5
            
            status = "上げ" if next_h > current_h else "下げ"
            # 日本の潮位(cm)に近似（最低位を0付近にするオフセット）
            data['tide_level'] = int((current_h - t_min) * 300) # 振幅を日本の干満差に合わせる
            
            # 位置から「分」を算出 (1~9分)
            p_val = int(rel_pos * 9) + 1 if status == "上げ" else int((1 - rel_pos) * 9) + 1
            data['phase'] = f"{status}{min(max(p_val, 1), 9)}分"
            
            # 満潮・干潮の端っこ判定
            if rel_pos > 0.95: data['phase'] = "満潮"
            elif rel_pos < 0.05: data['phase'] = "干潮"

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

    st.title("🏹 SeaBass Match AI v3.5")

    if 'm_data' not in st.session_state:
        st.session_state.m_data = get_realtime_weather()

    st.markdown("<div class='input-card'>", unsafe_allow_html=True)
    if st.button("🔄 本渡瀬戸のリアルタイム同期"):
        st.session_state.m_data = get_realtime_weather()
        st.rerun()

    md = st.session_state.m_data
    c1, c2 = st.columns(2)
    with c1:
        tide_in = st.selectbox("潮名", ["大潮", "中潮", "小潮", "長潮", "若潮"], index=["大潮", "中潮", "小潮", "長潮", "若潮"].index(md.get('tide','中潮')))
        level_in = st.number_input("潮位 (cm)", value=int(md.get('tide_level', 100)))
        temp_in = st.number_input("気温 (℃)", value=float(md.get('temp', 15.0)))
    with c2:
        p_list = ["上げ1分","上げ3分","上げ5分","上げ7分","上げ9分","満潮","下げ1分","下げ3分","下げ5分","下げ7分","下げ9分","干潮"]
        current_p = md.get('phase','上げ5分')
        p_idx = p_list.index(current_p) if current_p in p_list else 2
        phase_in = st.selectbox("潮位フェーズ", p_list, index=p_idx)
        wdir_list = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
        wdir_in = st.selectbox("風向", wdir_list, index=wdir_list.index(md.get('wdir','北')) if md.get('wdir') in wdir_list else 0)
        wind_in = st.number_input("風速 (m/s)", value=float(md.get('wind', 3.0)))
    precip_in = st.number_input("48h降水量 (mm)", value=float(md.get('precip_48h', 0.0)))
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("🎯 カスタム優先順位でランキング診断"):
        if df is not None and not df.empty:
            df['is_bouzu'] = df['魚種'].astype(str).str.contains('ボウズ', na=False)
            results = []
            for place in df['場所'].unique():
                p_df = df[df['場所'] == place]
                success_df = p_df[~p_df['is_bouzu']]
                if not success_df.empty:
                    # 優先順位スコアリング: 1.フェーズ(35), 2.潮位(25), 3.風向(15), 4.気温(10), 5.他(15)
                    s_phase = 35 if not success_df[success_df['潮位フェーズ'] == phase_in].empty else 0
                    s_level = 25 if not success_df[abs(success_df.get('潮位_cm',0) - level_in) <= 25].empty else 0
                    s_wdir = 15 if not success_df[success_df['風向'] == wdir_in].empty else 0
                    s_temp = 10 if not success_df[abs(success_df['気温'] - temp_in) <= 3].empty else 0
                    s_others = (5 if not success_df[success_df['潮名'] == tide_in].empty else 0) + \
                               (5 if not success_df[abs(success_df['風速'] - wind_in) <= 2].empty else 0) + \
                               (5 if not success_df[abs(success_df.get('48時間降水量',0) - precip_in) <= 15].empty else 0)
                    
                    total = min(s_phase + s_level + s_wdir + s_temp + s_others, 99)
                    lure_mode = success_df['ルアー'].dropna().mode()
                    results.append({'place': place, 'score': total, 'hits': len(success_df), 'lure': lure_mode[0] if not lure_mode.empty else "未登録"})
            
            results = sorted(results, key=lambda x: x['score'], reverse=True)
            for i, res in enumerate(results):
                st.markdown(f"<div class='recommend-card'><div class='score-badge'>{res['score']}%</div><b>{i+1}位: {res['place']}</b><br>実績: {res['hits']}件 / 推奨: {res['lure']}</div>", unsafe_allow_html=True)
