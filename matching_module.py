import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import requests

def get_realtime_weather():
    """本渡瀬戸の現況（降水量・潮位フェーズ含むすべて）を同期"""
    LAT, LON = 32.4333, 130.2167
    now = datetime.now()
    # 初期値
    data = {
        'tide': "中潮", 'temp': 15.0, 'wind': 3.0, 
        'tide_level': 100, 'phase': "下げ5分", 'precip': 0.0
    }
    
    try:
        # 1. 気象予報API（気温・風速・降水量）
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current_weather=true&hourly=precipitation&timezone=Asia%2FTokyo"
        w_res = requests.get(w_url, timeout=5).json()
        if 'current_weather' in w_res:
            data['temp'] = float(w_res['current_weather'].get('temperature', 15.0))
            data['wind'] = float(w_res['current_weather'].get('windspeed', 3.0))
            if 'hourly' in w_res:
                # 現在時刻の降水量を抽出
                h_idx = now.hour
                data['precip'] = float(w_res['hourly'].get('precipitation', [0.0]*24)[h_idx])

        # 2. 海洋予報API（潮位・フェーズ）
        t_url = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT}&longitude={LON}&hourly=tide_height&timezone=Asia%2FTokyo"
        t_res = requests.get(t_url, timeout=5).json()
        if 'hourly' in t_res:
            h_list = t_res['hourly'].get('tide_height', [0.0]*24)
            h0, h1 = h_list[now.hour], h_list[(now.hour+1)%24]
            data['tide_level'] = int(h0 * 100)
            
            # 変化量からフェーズを精密判定
            status = "上げ" if h1 - h0 > 0 else "下げ"
            # 潮位の絶対値から「○分」を計算
            p_val = min(max(int(abs(h0) * 5) + 1, 1), 9)
            data['phase'] = f"{status}{p_val}分"

        # 3. 潮名（月齢）
        y, m, d = now.year, now.month, now.day
        moon_age = (((y - 2009) % 19) * 11 + [0, 2, 0, 2, 2, 4, 5, 6, 7, 8, 9, 10][m-1] + d) % 30
        if moon_age in [0,1,2,14,15,16,29]: data['tide'] = "大潮"
        elif moon_age in [3,4,5,12,13,17,18,19,27,28]: data['tide'] = "中潮"
        else: data['tide'] = "小潮"
        
    except Exception as e:
        st.error(f"同期中にエラーが発生しました: {e}")
        
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

    st.title("🏹 SeaBass Match AI v2.5")

    if 'm_data' not in st.session_state:
        st.session_state.m_data = get_realtime_weather()

    # --- 入力・同期 ---
    st.markdown("<div class='input-card'>", unsafe_allow_html=True)
    if st.button("🔄 本渡瀬戸の全データを同期する"):
        st.session_state.m_data = get_realtime_weather()
        st.toast("降水量・潮位フェーズを同期しました")
        st.rerun()

    md = st.session_state.m_data
    col1, col2 = st.columns(2)
    
    with col1:
        # 同期された値をデフォルト値として使用
        tide_in = st.selectbox("潮名", ["大潮", "中潮", "小潮", "長潮", "若潮"], index=["大潮", "中潮", "小潮", "長潮", "若潮"].index(md['tide']))
        temp_in = st.number_input("気温 (℃)", value=md['temp'])
        precip_in = st.number_input("降水量 (mm/h)", value=md['precip'])
    
    with col2:
        # フェーズも同期された値を反映
        phase_list = ["上げ1分","上げ3分","上げ5分","上げ7分","上げ9分","満潮","下げ1分","下げ3分","下げ5分","下げ7分","下げ9分","干潮"]
        current_p_idx = phase_list.index(md['phase']) if md['phase'] in phase_list else 2
        phase_in = st.selectbox("潮位フェーズ", phase_list, index=current_p_idx)
        wind_in = st.number_input("風速 (m/s)", value=md['wind'])
    st.markdown("</div>", unsafe_allow_html=True)

    # --- ランキング診断 ---
    if st.button("💘 この条件でランキングを生成"):
        if df is not None and not df.empty:
            df['is_bouzu'] = df['魚種'].astype(str).str.contains('ボウズ', na=False)
            match_df = df[df['潮名'] == tide_in].copy()
            
            if not match_df.empty:
                results = []
                for place in match_df['場所'].unique():
                    p_df = match_df[match_df['場所'] == place]
                    success_df = p_df[~p_df['is_bouzu']]
                    
                    if not success_df.empty:
                        # スコア計算（成功率 + 気象類似度）
                        base_score = (len(success_df) / len(p_df)) * 50
                        
                        # 気象の近さ（気温・風・降雨）をスコア化
                        weather_diff = abs(success_df['気温'].mean() - temp_in) * 2 + \
                                       abs(success_df['風速'].mean() - wind_in) * 2 + \
                                       abs(success_df.get('降水量', pd.Series([0]*len(success_df))).mean() - precip_in) * 5
                        weather_score = max(0, 40 - weather_diff)
                        
                        # 時合一致ボーナス
                        phase_bonus = 10 if not success_df[success_df['潮位フェーズ'] == phase_in].empty else 0
                        
                        total_score = min(int(base_score + weather_score + phase_bonus), 99)
                        
                        lure_mode = success_df['ルアー'].dropna().mode()
                        results.append({
                            'place': place, 'score': total_score, 
                            'hits': len(success_df), 'lure': lure_mode[0] if not lure_mode.empty else "未登録"
                        })
                
                results = sorted(results, key=lambda x: x['score'], reverse=True)
                
                for i, res in enumerate(results):
                    st.markdown(f"""
                        <div class='recommend-card'>
                            <div class='score-badge'>{res['score']}%</div>
                            <div style='font-size:1.2rem; font-weight:bold;'>{i+1}位: {res['place']}</div>
                            <div>実績: {res['hits']}件 / 鉄板: {res['lure']}</div>
                        </div>
                    """, unsafe_allow_html=True)
