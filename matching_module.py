import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import requests

def get_realtime_weather():
    """本渡瀬戸の現況を同期（潮位・48h降雨・8方位風向）"""
    LAT, LON = 32.4333, 130.2167
    now = datetime.now()
    data = {
        'tide': "中潮", 'temp': 15.0, 'wind': 3.0, 'wdir': "北",
        'tide_level': 100, 'phase': "上げ5分", 'precip_48h': 0.0
    }
    
    try:
        # 1. 気象API (気温・風速・48h降水)
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current_weather=true&hourly=precipitation&past_days=2&timezone=Asia%2FTokyo"
        w_res = requests.get(w_url, timeout=5).json()
        if 'current_weather' in w_res:
            cw = w_res['current_weather']
            data['temp'] = float(cw.get('temperature', 15.0))
            data['wind'] = float(cw.get('windspeed', 3.0))
            deg = cw.get('winddirection', 0)
            directions = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
            data['wdir'] = directions[int((deg + 22.5) / 45) % 8]
            if 'hourly' in w_res:
                h_idx = 48 + now.hour
                p_list = w_res['hourly'].get('precipitation', [0.0]*72)
                data['precip_48h'] = round(sum(p_list[max(0, h_idx-48):h_idx+1]), 1)

        # 2. 海洋API (sea_level_height を使用して潮位同期)
        t_url = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT}&longitude={LON}&hourly=sea_level_height&timezone=Asia%2FTokyo"
        t_res = requests.get(t_url, timeout=5).json()
        if 'hourly' in t_res:
            h_list = t_res['hourly'].get('sea_level_height', [0.0]*24)
            h0 = h_list[now.hour]
            h1 = h_list[(now.hour + 1) % 24]
            
            # メートルをセンチに変換し、日本の基準に合わせるためオフセット調整（簡易）
            # Open-Meteoの sea_level_height は平均海面基準のため、+100cm程度で実測に近づくことが多いです
            data['tide_level'] = int(h0 * 100) + 100 
            
            # フェーズ判定
            diff = h1 - h0
            status = "上げ" if diff > 0 else "下げ"
            # 潮位の高さから「分」を推測 (0.1m刻みで判定)
            p_val = min(max(int(abs(h0) * 4) + 1, 1), 9)
            data['phase'] = f"{status}{p_val}分"
            
    except: pass
    return data

def show_matching_page(df):
    # --- スタイル設定 ---
    st.markdown("""
        <style>
        .stButton>button { background-color: #ff4b6c; color: white; border-radius: 25px; border: none; padding: 12px; font-weight: bold; width: 100%; }
        .input-card { background-color: #1e1e1e; padding: 20px; border-radius: 15px; border: 1px solid #333; margin-bottom: 20px; }
        .recommend-card { background: linear-gradient(135deg, #2c3e50 0%, #000000 100%); padding: 20px; border-radius: 15px; border-left: 5px solid #ff4b6c; margin-bottom: 15px; color: white; position: relative; }
        .score-badge { position: absolute; top: 20px; right: 20px; font-size: 1.8rem; font-weight: bold; color: #ff4b6c; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🏹 SeaBass Match AI v3.1")

    if 'm_data' not in st.session_state:
        st.session_state.m_data = get_realtime_weather()

    st.markdown("<div class='input-card'>", unsafe_allow_html=True)
    if st.button("🔄 潮位・気象・48h降雨を同期"):
        st.session_state.m_data = get_realtime_weather()
        st.rerun()

    md = st.session_state.m_data
    c1, c2 = st.columns(2)
    with c1:
        tide_in = st.selectbox("潮名", ["大潮", "中潮", "小潮", "長潮", "若潮"], index=["大潮", "中潮", "小潮", "長潮", "若潮"].index(md.get('tide','中潮')))
        level_in = st.number_input("潮位 (cm)", value=int(md.get('tide_level', 100)))
        temp_in = st.number_input("気温 (℃)", value=float(md.get('temp', 15.0)))
    with c2:
        phase_list = ["上げ1分","上げ3分","上げ5分","上げ7分","上げ9分","満潮","下げ1分","下げ3分","下げ5分","下げ7分","下げ9分","干潮"]
        phase_in = st.selectbox("潮位フェーズ", phase_list, index=phase_list.index(md.get('phase','上げ5分')) if md.get('phase') in phase_list else 2)
        wdir_list = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
        wdir_in = st.selectbox("風向", wdir_list, index=wdir_list.index(md.get('wdir','北')) if md.get('wdir') in wdir_list else 0)
        wind_in = st.number_input("風速 (m/s)", value=float(md.get('wind', 3.0)))
    precip_in = st.number_input("48h降水量合計 (mm)", value=float(md.get('precip_48h', 0.0)))
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("🎯 こだわりアルゴリズムで診断"):
        if df is not None and not df.empty:
            df['is_bouzu'] = df['魚種'].astype(str).str.contains('ボウズ', na=False)
            results = []
            for place in df['場所'].unique():
                p_df = df[df['場所'] == place]
                success_df = p_df[~p_df['is_bouzu']]
                
                if not success_df.empty:
                    # --- 🥇 指定優先順位による新スコアリング (100点満点) ---
                    # 1. 潮位フェーズ (35点) - 最優先
                    phase_score = 35 if not success_df[success_df['潮位フェーズ'] == phase_in].empty else 0
                    # 2. 潮位 (25点) - ±20cm以内
                    level_score = 25 if not success_df[abs(success_df['潮位_cm'] - level_in) <= 20].empty else 0
                    # 3. 風向き (15点)
                    wdir_score = 15 if not success_df[success_df['風向'] == wdir_in].empty else 0
                    # 4. 気温 (10点) - ±3度以内
                    temp_score = 10 if not success_df[abs(success_df['気温'] - temp_in) <= 3].empty else 0
                    # 5. 風速 / 潮名 / 降水量 (各5点 = 計15点)
                    wind_score = 5 if not success_df[abs(success_df['風速'] - wind_in) <= 2].empty else 0
                    tname_score = 5 if not success_df[success_df['潮名'] == tide_in].empty else 0
                    precip_score = 5 if '48時間降水量' in success_df.columns and not success_df[abs(success_df['48時間降水量'] - precip_in) <= 15].empty else 0
                    
                    total = phase_score + level_score + wdir_score + temp_score + wind_score + tname_score + precip_score
                    
                    lure_mode = success_df['ルアー'].dropna().mode()
                    results.append({
                        'place': place, 'score': min(total, 99),
                        'hits': len(success_df), 'lure': lure_mode[0] if not lure_mode.empty else "未登録"
                    })
            
            results = sorted(results, key=lambda x: x['score'], reverse=True)
            for i, res in enumerate(results):
                st.markdown(f"<div class='recommend-card'><div class='score-badge'>{res['score']}%</div><div style='font-size:1.2rem; font-weight:bold;'>{i+1}位: {res['place']}</div><div>過去ヒット: {res['hits']}件 / 推奨: {res['lure']}</div></div>", unsafe_allow_html=True)
