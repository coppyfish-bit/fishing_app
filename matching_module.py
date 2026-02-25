import streamlit as st
import pandas as pd
from datetime import datetime
import requests

def get_realtime_weather():
    """本渡瀬戸の基本項目（潮名・気温・風・潮位・フェーズ）を取得"""
    LAT, LON = 32.4333, 130.2167
    now = datetime.now()
    data = {
        'tide': "中潮", 'temp': 15.0, 'wind': 3.0, 
        'tide_level': 100, 'phase': "上げ5分"
    }
    try:
        # 気象 (Open-Meteo)
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current_weather=true"
        w_res = requests.get(w_url, timeout=5).json()
        if 'current_weather' in w_res:
            data['temp'] = w_res['current_weather']['temperature']
            data['wind'] = w_res['current_weather']['windspeed']
            
        # 潮汐 (Marine API)
        t_url = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT}&longitude={LON}&hourly=tide_height&timezone=Asia%2FTokyo"
        t_res = requests.get(t_url, timeout=5).json()
        if 'hourly' in t_res:
            idx = now.hour
            h0 = t_res['hourly']['tide_height'][idx]
            h1 = t_res['hourly']['tide_height'][idx+1]
            data['tide_level'] = int(h0 * 100) # cm変換
            status = "上げ" if h1 - h0 > 0 else "下げ"
            p_num = min(max(int(abs(h0) * 5) + 1, 1), 9)
            data['phase'] = f"{status}{p_num}分"
            
        # 潮名判定
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
        .result-card { background: linear-gradient(135deg, #2c3e50 0%, #000000 100%); padding: 20px; border-radius: 15px; border-left: 5px solid #ff4b6c; margin-bottom: 15px; color: white; }
        .match-score { font-size: 2rem; font-weight: bold; color: #ff4b6c; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 class='match-header'>SeaBass Match Pro</h1>", unsafe_allow_html=True)

    # セッション状態の初期化
    if 'm_data' not in st.session_state:
        st.session_state.m_data = {'tide':"中潮", 'temp':15.0, 'wind':3.0, 'tide_level':100, 'phase':"上げ5分"}

    # --- 条件入力セクション ---
    st.markdown("<div class='input-card'>", unsafe_allow_html=True)
    if st.button("🔄 本渡瀬戸の現況を自動入力"):
        st.session_state.m_data = get_realtime_weather()
        st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        tide = st.selectbox("潮名", ["大潮", "中潮", "小潮", "長潮", "若潮"], index=["大潮", "中潮", "小潮", "長潮", "若潮"].index(st.session_state.m_data['tide']))
        tide_level = st.number_input("潮位 (cm)", value=int(st.session_state.m_data['tide_level']))
        temp = st.number_input("気温 (℃)", value=float(st.session_state.m_data['temp']))
    with col2:
        phase = st.selectbox("潮位フェーズ", ["上げ1分","上げ3分","上げ5分","上げ7分","上げ9分","満潮","下げ1分","下げ3分","下げ5分","下げ7分","下げ9分","干潮"], 
                             index=["上げ1分","上げ3分","上げ5分","上げ7分","上げ9分","満潮","下げ1分","下げ3分","下げ5分","下げ7分","下げ9分","干潮"].index(st.session_state.m_data['phase']) if st.session_state.m_data['phase'] in ["上げ1分","上げ3分","上げ5分","上げ7分","上げ9分","満潮","下げ1分","下げ3分","下げ5分","下げ7分","下げ9分","干潮"] else 2)
        wind = st.number_input("風速 (m/s)", value=float(st.session_state.m_data['wind']))
        
        # 複数エリア選択
        all_places = df['場所'].unique().tolist() if df is not None else ["本渡瀬戸"]
        target_places = st.multiselect("気になるエリア（複数可）", all_places, default=all_places[:1])

    st.markdown("</div>", unsafe_allow_html=True)

    # --- マッチング実行 ---
    if st.button("💘 選択したエリアとの相性を一括診断"):
        if df is not None and not df.empty and target_places:
            df['is_bouzu'] = df['魚種'].str.contains('ボウズ', na=False)
            
            st.subheader("📊 診断結果")
            
            for place in target_places:
                # エリア × 潮名 で過去のデータを検索
                match_df = df[(df['場所'] == place) & (df['潮名'] == tide)].copy()
                
                if not match_df.empty:
                    success_df = match_df[match_df['is_bouzu'] == False]
                    # 指定したフェーズとの一致も考慮（ボーナス加点的なロジック）
                    phase_match = success_df[success_df['潮位フェーズ'] == phase]
                    
                    success_rate = (len(success_df) / len(match_df)) * 100
                    # フェーズまで一致するデータがあれば期待度アップ
                    bonus_text = "✨ 時合が過去の実績と完全一致！" if not phase_match.empty else ""
                    
                    st.markdown(f"""
                        <div class='result-card'>
                            <div style='display:flex; justify-content:between; align-items:center;'>
                                <div style='flex-grow:1;'>
                                    <span style='font-size:1.2rem; font-weight:bold;'>{place}</span><br>
                                    <small>{tide}の実績数: {len(match_df)}件</small><br>
                                    <span style='color:#00ffd0;'>{bonus_text}</span>
                                </div>
                                <div class='match-score'>{int(success_rate)}%</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='result-card' style='border-left-color:#555;'>{place}: データ不足のため未知数です</div>", unsafe_allow_html=True)
        else:
            st.warning("エリアを選択し、データが存在することを確認してください。")
