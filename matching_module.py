import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import requests

def get_realtime_weather():
    """本渡瀬戸の現況（潮位含むすべて）を同期"""
    LAT, LON = 32.4333, 130.2167
    now = datetime.now()
    data = {
        'tide': "中潮", 'temp': 15.0, 'wind': 3.0, 'wdir': "北",
        'tide_level': 100, 'phase': "上げ5分", 'precip_48h': 0.0
    }
    
    try:
        # 1. 気象予報API
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
                current_idx = 48 + now.hour
                p_list = w_res['hourly'].get('precipitation', [0.0]*72)
                data['precip_48h'] = round(sum(p_list[max(0, current_idx-48):current_idx+1]), 1)

        # 2. 海洋予報API (潮位・フェーズ)
        t_url = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT}&longitude={LON}&hourly=tide_height&timezone=Asia%2FTokyo"
        t_res = requests.get(t_url, timeout=5).json()
        if 'hourly' in t_res:
            h_list = t_res['hourly'].get('tide_height', [0.0]*24)
            h0, h1 = h_list[now.hour], h_list[(now.hour+1)%24]
            data['tide_level'] = int(h0 * 100) # cm単位で同期
            status = "上げ" if h1 - h0 > 0 else "下げ"
            p_val = min(max(int(abs(h0) * 5) + 1, 1), 9)
            data['phase'] = f"{status}{p_val}分"
            
    except: pass
    return data

def simplify_direction(wdir):
    mapping = {'北北東':'北東','東北東':'北東','東南東':'南東','南南東':'南東','南南西':'南西','西南西':'南西','西北西':'北西','北北西':'北西'}
    return mapping.get(str(wdir), str(wdir))

def show_matching_page(df):
    st.markdown("""
        <style>
        .stButton>button { background-color: #ff4b6c; color: white; border-radius: 25px; border: none; padding: 12px; font-weight: bold; width: 100%; }
        .input-card { background-color: #1e1e1e; padding: 20px; border-radius: 15px; border: 1px solid #333; margin-bottom: 20px; }
        .recommend-card { background: linear-gradient(135deg, #2c3e50 0%, #000000 100%); padding: 20px; border-radius: 15px; border-left: 5px solid #ff4b6c; margin-bottom: 15px; color: white; position: relative; }
        .score-badge { position: absolute; top: 20px; right: 20px; font-size: 1.8rem; font-weight: bold; color: #ff4b6c; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🏹 SeaBass Match AI v3.0")

    if 'm_data' not in st.session_state:
        st.session_state.m_data = get_realtime_weather()

    st.markdown("<div class='input-card'>", unsafe_allow_html=True)
    if st.button("🔄 潮位・気象・48h降雨を完全同期"):
        st.session_state.m_data = get_realtime_weather()
        st.rerun()

    md = st.session_state.m_data
    c1, c2 = st.columns(2)
    with c1:
        tide_in = st.selectbox("潮名", ["大潮", "中潮", "小潮", "長潮", "若潮"], index=["大潮", "中潮", "小潮", "長潮", "若潮"].index(md.get('tide','中潮')))
        level_in = st.number_input("潮位 (cm)", value=int(md.get('tide_level', 100)))
        temp_in = st.number_input("気温 (℃)", value=float(md.get('temp', 15.0)))
        precip_in = st.number_input("48h降水量 (mm)", value=float(md.get('precip_48h', 0.0)))
    with c2:
        phase_list = ["上げ1分","上げ3分","上げ5分","上げ7分","上げ9分","満潮","下げ1分","下げ3分","下げ5分","下げ7分","下げ9分","干潮"]
        phase_in = st.selectbox("潮位フェーズ", phase_list, index=phase_list.index(md.get('phase','上げ5分')) if md.get('phase') in phase_list else 2)
        wdir_list = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
        wdir_in = st.selectbox("風向", wdir_list, index=wdir_list.index(md.get('wdir','北')) if md.get('wdir') in wdir_list else 0)
        wind_in = st.number_input("風速 (m/s)", value=float(md.get('wind', 3.0)))
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("🎯 カスタムアルゴリズムで診断"):
        if df is not None and not df.empty:
            df['is_bouzu'] = df['魚種'].astype(str).str.contains('ボウズ', na=False)
            df['風向_8'] = df['風向'].apply(simplify_direction)
            
            # 今回は潮名フィルタを外して、全データから「条件の近さ」で抽出
            results = []
            for place in df['場所'].unique():
                p_df = df[df['場所'] == place]
                success_df = p_df[~p_df['is_bouzu']]
                
                if not success_df.empty:
                    # --- 🥇 ご指定の優先順位による配点 (100点満点) ---
                    # 1. 潮位フェーズ (30点)
                    phase_score = 30 if not success_df[success_df['潮位フェーズ'] == phase_in].empty else 0
                    # 2. 潮位 (25点: 誤差±20cm以内)
                    level_match = success_df[abs(success_df['潮位_cm'] - level_in) <= 20] if '潮位_cm' in success_df.columns else pd.DataFrame()
                    level_score = 25 if not level_match.empty else 0
                    # 3. 風向き (15点)
                    wdir_score = 15 if not success_df[success_df['風向_8'] == wdir_in].empty else 0
                    # 4. 気温 (10点: 誤差±3度以内)
                    temp_score = 10 if not success_df[abs(success_df['気温'] - temp_in) <= 3].empty else 0
                    # 5. 風速 / 潮名 / 降水量 (各5点 = 計15点)
                    wind_score = 5 if not success_df[abs(success_df['風速'] - wind_in) <= 2].empty else 0
                    tide_name_score = 5 if not success_df[success_df['潮名'] == tide_in].empty else 0
                    precip_score = 5 if '48時間降水量' in success_df.columns and not success_df[abs(success_df['48時間降水量'] - precip_in) <= 10].empty else 0
                    
                    total_score = phase_score + level_score + wdir_score + temp_score + wind_score + tide_name_score + precip_score
                    
                    lure_mode = success_df['ルアー'].dropna().mode()
                    results.append({
                        'place': place, 'score': min(total_score, 99),
                        'hits': len(success_df), 'lure': lure_mode[0] if not lure_mode.empty else "未登録"
                    })
            
            results = sorted(results, key=lambda x: x['score'], reverse=True)
            for i, res in enumerate(results):
                st.markdown(f"<div class='recommend-card'><div class='score-badge'>{res['score']}%</div><div style='font-size:1.2rem; font-weight:bold;'>{i+1}位: {res['place']}</div><div>実績: {res['hits']}件 / 推奨: {res['lure']}</div></div>", unsafe_allow_html=True)
