import streamlit as st
import pandas as pd
from datetime import datetime
import requests

def get_realtime_weather():
    """本渡瀬戸の現況を取得"""
    LAT, LON = 32.4333, 130.2167
    now = datetime.now()
    data = {'tide': "中潮", 'temp': 15.0, 'wind': 3.0, 'tide_level': 100, 'phase': "上げ5分"}
    try:
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current_weather=true"
        w_res = requests.get(w_url, timeout=5).json()
        if 'current_weather' in w_res:
            data['temp'] = w_res['current_weather']['temperature']
            data['wind'] = w_res['current_weather']['windspeed']
        
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
        .match-header { text-align: center; color: #ff4b6c; font-family: 'Helvetica Neue', sans-serif; font-weight: bold; }
        .recommend-card { background: linear-gradient(135deg, #2c3e50 0%, #000000 100%); padding: 20px; border-radius: 15px; border-left: 5px solid #ff4b6c; margin-bottom: 15px; color: white; position: relative; }
        .score-badge { position: absolute; top: 20px; right: 20px; font-size: 1.8rem; font-weight: bold; color: #ff4b6c; }
        .lure-tag { background: #444; color: #00ffd0; padding: 2px 8px; border-radius: 5px; font-size: 0.8rem; }
        .ranker-badge { color: #ffd700; font-size: 0.9rem; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 class='match-header'>SeaBass Match AI</h1>", unsafe_allow_html=True)

    if 'm_data' not in st.session_state:
        st.session_state.m_data = {'tide':"中潮", 'temp':15.0, 'wind':3.0, 'tide_level':100, 'phase':"上げ5分"}

    st.markdown("<div class='input-card'>", unsafe_allow_html=True)
    if st.button("🔄 今の本渡瀬戸に合わせる"):
        st.session_state.m_data = get_realtime_weather()
        st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        tide = st.selectbox("潮名", ["大潮", "中潮", "小潮", "長潮", "若潮"], index=["大潮", "中潮", "小潮", "長潮", "若潮"].index(st.session_state.m_data['tide']))
        tide_level = st.number_input("潮位 (cm)", value=int(st.session_state.m_data['tide_level']))
    with col2:
        phase = st.selectbox("潮位フェーズ", ["上げ1分","上げ3分","上げ5分","上げ7分","上げ9分","満潮","下げ1分","下げ3分","下げ5分","下げ7分","下げ9分","干潮"], 
                             index=["上げ1分","上げ3分","上げ5分","上げ7分","上げ9分","満潮","下げ1分","下げ3分","下げ5分","下げ7分","下げ9分","干潮"].index(st.session_state.m_data['phase']) if st.session_state.m_data['phase'] in ["上げ1分","上げ3分","上げ5分","上げ7分","上げ9分","満潮","下げ1分","下げ3分","下げ5分","下げ7分","下げ9分","干潮"] else 2)
        wind = st.number_input("風速 (m/s)", value=float(st.session_state.m_data['wind']))
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("💘 この条件で最高のエリアを探す"):
        if df is not None and not df.empty:
            df['is_bouzu'] = df['魚種'].astype(str).str.contains('ボウズ', na=False)
            match_df = df[df['潮名'] == tide].copy()
            
            if not match_df.empty:
                results = []
                for place in match_df['場所'].unique():
                    p_df = match_df[match_df['場所'] == place]
                    success_df = p_df[p_df['is_bouzu'] == False]
                    
                    if not p_df.empty:
                        success_rate = (len(success_df) / len(p_df)) * 100
                        phase_hits = len(success_df[success_df['潮位フェーズ'] == phase])
                        score = min(int(success_rate + (10 if phase_hits > 0 else 0)), 100)
                        
                        # 【修正】 modeの結果があるか安全に確認
                        lure_mode = success_df['ルアー'].dropna().mode()
                        best_lure = lure_mode[0] if not lure_mode.empty else "未登録"
                        
                        # 最大サイズ（ランカー実績）の取得
                        max_size = success_df['全長_cm'].max() if not success_df.empty else 0
                        
                        results.append({
                            'place': place, 'score': score, 'hits': len(success_df), 
                            'lure': best_lure, 'phase_match': phase_hits > 0,
                            'max_size': max_size
                        })
                
                results = sorted(results, key=lambda x: x['score'], reverse=True)

                st.subheader("📍 あなたにオススメのエリア")
                for res in results:
                    bonus_star = "⭐ 時合が完璧！" if res['phase_match'] else ""
                    ranker_info = f"🏆 最大実績: {res['max_size']}cm" if res['max_size'] > 0 else ""
                    
                    st.markdown(f"""
                        <div class='recommend-card'>
                            <div class='score-badge'>{res['score']}%</div>
                            <div style='font-size:1.3rem; font-weight:bold;'>{res['place']}</div>
                            <div style='margin: 5px 0;'>過去の釣果: {res['hits']}件 <span style='color:#ff8e53;'>{bonus_star}</span></div>
                            <div class='ranker-badge'>{ranker_info}</div>
                            <div style='margin-top:8px;'>実績ルアー: <span class='lure-tag'>{res['lure']}</span></div>
                        </div>
                    """, unsafe_allow_html=True)
                
                if results[0]['score'] > 80: st.balloons()
            else:
                st.info(f"{tide}でのデータがまだありません。")
