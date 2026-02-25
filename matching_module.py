import streamlit as st
import pandas as pd
from datetime import datetime
import requests

def get_realtime_weather():
    """本渡瀬戸の基本3項目（潮名・気温・風）を取得"""
    LAT, LON = 32.4333, 130.2167
    now = datetime.now()
    data = {'tide': "中潮", 'wind': 3.0, 'temp': 15.0}
    try:
        # 気象
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current_weather=true"
        w_res = requests.get(w_url, timeout=5).json()
        if 'current_weather' in w_res:
            data['temp'] = w_res['current_weather']['temperature']
            data['wind'] = w_res['current_weather']['windspeed']
        # 潮名（月齢判定）
        y, m, d = now.year, now.month, now.day
        moon_age = (((y - 2009) % 19) * 11 + [0, 2, 0, 2, 2, 4, 5, 6, 7, 8, 9, 10][m-1] + d) % 30
        if moon_age in [0, 1, 2, 14, 15, 16, 29]: data['tide'] = "大潮"
        elif moon_age in [3, 4, 5, 12, 13, 17, 18, 19, 27, 28]: data['tide'] = "中潮"
        else: data['tide'] = "小潮"
    except: pass
    return data

def show_matching_page(df):
    # --- スタイリング（マッチングアプリ風） ---
    st.markdown("""
        <style>
        .stButton>button { background-color: #ff4b6c; color: white; border-radius: 25px; border: none; padding: 10px 20px; font-weight: bold; width: 100%; }
        .input-card { background-color: #1e1e1e; padding: 20px; border-radius: 15px; border: 1px solid #333; margin-bottom: 20px; }
        .match-header { text-align: center; color: #ff4b6c; font-family: 'Helvetica Neue', sans-serif; }
        .result-card { background: linear-gradient(135deg, #ff4b6c 0%, #ff8e53 100%); padding: 25px; border-radius: 20px; color: white; text-align: center; margin-top: 20px; box-shadow: 0 10px 20px rgba(0,0,0,0.3); }
        .profile-img { border-radius: 50%; border: 3px solid #ff4b6c; margin-bottom: 10px; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h1 class='match-header'>SeaBass Match</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#888;'>理想の釣果と出会うための条件入力</p>", unsafe_allow_html=True)

    # セッション状態の初期化
    if 'm_tide' not in st.session_state:
        st.session_state.m_tide = "中潮"
        st.session_state.m_temp = 15.0
        st.session_state.m_wind = 3.0

    # --- 入力セクション ---
    with st.container():
        st.markdown("<div class='input-card'>", unsafe_allow_html=True)
        
        # 同期ボタン
        if st.button("🔄 今日の条件を同期する"):
            real_data = get_realtime_weather()
            st.session_state.m_tide = real_data['tide']
            st.session_state.m_temp = real_data['temp']
            st.session_state.m_wind = real_data['wind']
            st.rerun()

        col1, col2 = st.columns(2)
        with col1:
            tide = st.selectbox("希望する潮名", ["大潮", "中潮", "小潮", "長潮", "若潮"], index=["大潮", "中潮", "小潮", "長潮", "若潮"].index(st.session_state.m_tide))
            temp = st.number_input("現在の気温 (℃)", value=float(st.session_state.m_temp))
        with col2:
            wind = st.number_input("許容する風速 (m/s)", value=float(st.session_state.m_wind))
            target_place = st.selectbox("気になるエリア", df['場所'].unique() if df is not None else ["本渡瀬戸"])

        st.markdown("</div>", unsafe_allow_html=True)

    # --- マッチング開始ボタン ---
    if st.button("💓 釣果との相性を診断する"):
        if df is not None and not df.empty:
            # フィルタリング
            match_df = df[(df['潮名'] == tide) & (df['場所'] == target_place)].copy()
            df['is_bouzu'] = df['魚種'].str.contains('ボウズ', na=False)
            
            if not match_df.empty:
                success_count = len(match_df[match_df['is_bouzu'] == False])
                total_count = len(match_df)
                match_rate = int((success_count / total_count) * 100)
                
                best_phase = match_df[match_df['is_bouzu'] == False]['潮位フェーズ'].mode()[0] if success_count > 0 else "不明"
                
                # 結果表示
                st.markdown(f"""
                    <div class='result-card'>
                        <div style='font-size: 1.2rem; margin-bottom: 10px;'>{target_place} との相性</div>
                        <div style='font-size: 4rem; font-weight: bold;'>{match_rate}%</div>
                        <div style='margin-top: 10px;'>狙い目の時合: <span style='font-size: 1.5rem; font-weight: bold;'>{best_phase}</span></div>
                    </div>
                """, unsafe_allow_html=True)
                
                if match_rate > 70:
                    st.balloons()
                    st.success("運命の出会いです！今すぐ準備をしましょう。")
                elif match_rate < 30:
                    st.warning("今日は「ボウズ」という名のミスマッチが起きやすいようです。")
            else:
                st.info("まだこの条件でのデータがありません。初デートを記録しましょう！")
        else:
            st.error("分析するための釣果ログがまだ登録されていません。")

    # フッター
    st.markdown("<br><p style='text-align:center; color:#444; font-size: 0.8rem;'>© 2026 SeaBass Match. No privacy leaks.</p>", unsafe_allow_html=True)
