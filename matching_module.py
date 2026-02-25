import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import requests

def get_realtime_weather():
    """本渡瀬戸の現況（気象・潮汐）を取得"""
    LAT, LON = 32.4333, 130.2167
    now = datetime.now()
    data = {'tide': "中潮", 'temp': 15.0, 'wind': 3.0, 'tide_level': 100, 'phase': "上げ5分", 'precip': 0.0}
    try:
        # 気象 (気温・風・降水量)
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current_weather=true&hourly=precipitation"
        w_res = requests.get(w_url, timeout=5).json()
        if 'current_weather' in w_res:
            data['temp'] = w_res['current_weather']['temperature']
            data['wind'] = w_res['current_weather']['windspeed']
            # 直近の降水量
            if 'hourly' in w_res:
                data['precip'] = w_res['hourly']['precipitation'][now.hour]
        
        # 潮汐
        t_url = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT}&longitude={LON}&hourly=tide_height&timezone=Asia%2FTokyo"
        t_res = requests.get(t_url, timeout=5).json()
        if 'hourly' in t_res:
            idx = now.hour
            h0, h1 = t_res['hourly']['tide_height'][idx], t_res['hourly']['tide_height'][idx+1]
            data['tide_level'] = int(h0 * 100)
            status = "上げ" if h1 - h0 > 0 else "下げ"
            p_num = min(max(int(abs(h0) * 5) + 1, 1), 9)
            data['phase'] = f"{status}{p_num}分"
            
        y, m, d = now.year, now.month, now.day
        moon_age = (((y - 2009) % 19) * 11 + [0, 2, 0, 2, 2, 4, 5, 6, 7, 8, 9, 10][m-1] + d) % 30
        if moon_age in [0, 1, 2, 14, 15, 16, 29]: data['tide'] = "大潮"
        elif moon_age in [3, 4, 5, 12, 13, 17, 18, 19, 27, 28]: data['tide'] = "中潮"
        else: data['tide'] = "小潮"
    except: pass
    return data

def show_matching_page(df):
    st.markdown("""
        <style>
        .stButton>button { background-color: #ff4b6c; color: white; border-radius: 25px; border: none; padding: 12px; font-weight: bold; width: 100%; }
        .input-card { background-color: #1e1e1e; padding: 20px; border-radius: 15px; border: 1px solid #333; margin-bottom: 20px; }
        .recommend-card { background: linear-gradient(135deg, #2c3e50 0%, #000000 100%); padding: 20px; border-radius: 15px; border-left: 5px solid #ff4b6c; margin-bottom: 15px; color: white; position: relative; }
        .score-badge { position: absolute; top: 20px; right: 20px; font-size: 1.8rem; font-weight: bold; color: #ff4b6c; }
        .data-label { color: #888; font-size: 0.8rem; margin-right: 5px; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🏹 SeaBass Match AI v2")

    if 'm_data' not in st.session_state:
        st.session_state.m_data = get_realtime_weather()

    # --- 条件入力セクション ---
    st.markdown("<div class='input-card'>", unsafe_allow_html=True)
    if st.button("🔄 今の本渡瀬戸に同期する"):
        st.session_state.m_data = get_realtime_weather()
        st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        tide = st.selectbox("潮名", ["大潮", "中潮", "小潮", "長潮", "若潮"], index=["大潮", "中潮", "小潮", "長潮", "若潮"].index(st.session_state.m_data['tide']))
        temp = st.number_input("気温 (℃)", value=float(st.session_state.m_data['temp']))
        precip = st.number_input("降水量 (mm/h)", value=float(st.session_state.m_data['precip']))
    with col2:
        phase = st.selectbox("潮位フェーズ", ["上げ1分","上げ3分","上げ5分","上げ7分","上げ9分","満潮","下げ1分","下げ3分","下げ5分","下げ7分","下げ9分","干潮"], index=2)
        wind = st.number_input("風速 (m/s)", value=float(st.session_state.m_data['wind']))
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("💘 最高のエリアをランキング表示"):
        if df is not None and not df.empty:
            df['is_bouzu'] = df['魚種'].astype(str).str.contains('ボウズ', na=False)
            # 潮名が一致する過去データを母集団とする
            match_df = df[df['潮名'] == tide].copy()
            
            if not match_df.empty:
                results = []
                for place in match_df['場所'].unique():
                    p_df = match_df[match_df['場所'] == place]
                    success_df = p_df[p_df['is_bouzu'] == False]
                    
                    if not success_df.empty:
                        # --- 🎓 スコア計算アルゴリズム ---
                        # 1. 基本成功率 (40点満点)
                        base_score = (len(success_df) / len(p_df)) * 40
                        
                        # 2. 時合(フェーズ)一致 (20点ボーナス)
                        phase_bonus = 20 if not success_df[success_df['潮位フェーズ'] == phase].empty else 0
                        
                        # 3. 気象類似度 (40点満点) 
                        # 気温・風速・降水量の平均値との「差」を計算
                        avg_temp = success_df['気温'].mean()
                        avg_wind = success_df['風速'].mean()
                        avg_precip = success_df['降水量'].mean() if '降水量' in success_df.columns else 0
                        
                        # 差が小さいほど高得点になるよう減点方式で計算
                        temp_diff = abs(avg_temp - temp)
                        wind_diff = abs(avg_wind - wind)
                        precip_diff = abs(avg_precip - precip)
                        
                        weather_score = 40 - (temp_diff * 2 + wind_diff * 3 + precip_diff * 5)
                        weather_score = max(0, weather_score)
                        
                        total_score = int(base_score + phase_bonus + weather_score)
                        total_score = min(total_score, 99) # 100%は出さないリアリティ

                        lure_mode = success_df['ルアー'].dropna().mode()
                        results.append({
                            'place': place, 'score': total_score, 
                            'hits': len(success_df), 'lure': lure_mode[0] if not lure_mode.empty else "未登録",
                            'max': success_df['全長_cm'].max() if '全長_cm' in success_df.columns else 0
                        })
                
                # スコア順にソート
                results = sorted(results, key=lambda x: x['score'], reverse=True)

                st.subheader("🏁 エリアマッチング・ランキング")
                for i, res in enumerate(results):
                    medal = "🥇" if i==0 else "🥈" if i==1 else "🥉" if i==2 else "🔹"
                    st.markdown(f"""
                        <div class='recommend-card'>
                            <div class='score-badge'>{res['score']}%</div>
                            <div style='font-size:1.3rem; font-weight:bold;'>{medal} {res['place']}</div>
                            <div style='margin: 8px 0;'>
                                <span class='data-label'>実績:</span>{res['hits']}件 / 
                                <span class='data-label'>最大:</span>{res['max']}cm
                            </div>
                            <div style='font-size:0.9rem;'>
                                推奨ルアー: <span style='color:#00ffd0;'>{res['lure']}</span>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                
                if results[0]['score'] > 85: st.balloons()
            else:
                st.info(f"{tide}でのデータがありません。")
