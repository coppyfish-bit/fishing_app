import streamlit as st
import pandas as pd
from datetime import datetime

def show_matching_page(df):
    # --- 1. デザインCSS ---
    st.markdown("""
        <style>
        .match-container {{
            background: linear-gradient(180deg, #1e2630 0%, #0e1117 100%);
            padding: 30px;
            border-radius: 30px;
            text-align: center;
            border: 1px solid #333;
        }}
        .profile-card {{
            background: #262730;
            border-radius: 20px;
            padding: 10px;
            margin: 20px auto;
            max-width: 400px;
            box-shadow: 0 15px 35px rgba(255, 65, 108, 0.3);
            border: 2px solid #ff416c;
        }}
        .seabass-img {{
            width: 100%;
            border-radius: 15px;
            aspect-ratio: 1/1;
            object-fit: cover;
        }}
        </style>
    """, unsafe_allow_html=True)

    st.title("💖 SEABASS MATCH")
    st.info("📍 ターゲットエリア: 熊本県 天草市 本渡瀬戸")
    
    # --- 2. セッション状態の初期化 ---
    if 'current_match_data' not in st.session_state:
        st.session_state.current_match_data = {
            'tide': "中潮", 'wind': 3.0, 'phase': "上げ3分", 'wdir': "北", 'temp': 15.0
        }

    # --- 3. リアルタイムデータ取得（本渡瀬戸） ---
    if st.button("🌊 本渡瀬戸の直近データを取得・同期", use_container_width=True, type="primary"):
        with st.spinner("本渡瀬戸の気象・潮汐を解析中..."):
            try:
                import app  # ロジックを借用
                
                # 本渡瀬戸の定数
                LAT_HONDO = 32.4333
                LON_HONDO = 130.2167
                now = datetime.now()
                
                # app.py の解析関数を実行
                temp, wind_s, wind_d, rain = app.get_weather_data_openmeteo(LAT_HONDO, LON_HONDO, now)
                tide_data = app.get_tide_details('HS', now) # HS=本渡瀬戸
                m_age = app.get_moon_age(now)
                t_name = app.get_tide_name(m_age)
                
                # セッションへ保存
                st.session_state.current_match_data['tide'] = t_name
                st.session_state.current_match_data['wind'] = float(wind_s) if wind_s else 3.0
                st.session_state.current_match_data['wdir'] = wind_d if wind_d else "北"
                st.session_state.current_match_data['temp'] = temp if temp else 15.0
                if tide_data and 'phase' in tide_data:
                    st.session_state.current_match_data['phase'] = tide_data['phase']
                
                st.toast(f"✅ {now.strftime('%H:%M')} の本渡瀬戸データを同期しました！")
                st.rerun()
            except Exception as e:
                if "multiple file_uploader" in str(e):
                    st.rerun()
                else:
                    st.error(f"データ取得エラー: {e}")

    # --- 4. 入力エリア（自動取得された値が入る） ---
    col1, col2 = st.columns(2)
    tide_options = ["大潮", "中潮", "小潮", "長潮", "若潮"]
    phase_options = ["上げ1分", "上げ2分", "上げ3分", "上げ4分", "上げ5分", "上げ6分", "上げ7分", "上げ8分", "上げ9分",
                     "下げ1分", "下げ2分", "下げ3分", "下げ4分", "下げ5分", "下げ6分", "下げ7分", "下げ8分", "下げ9分",
                     "満潮付近", "干潮付近"]
    wdir_options = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]

    with col1:
        t_idx = tide_options.index(st.session_state.current_match_data['tide']) if st.session_state.current_match_data['tide'] in tide_options else 0
        c_tide = st.selectbox("現在の潮", tide_options, index=t_idx)
        c_wind = st.slider("現在の風速 (m/s)", 0.0, 15.0, st.session_state.current_match_data['wind'])
        
    with col2:
        p_val = st.session_state.current_match_data['phase']
        p_idx = phase_options.index(p_val) if p_val in phase_options else 2
        c_phase = st.selectbox("現在の時合", phase_options, index=p_idx)
        wd_val = st.session_state.current_match_data['wdir']
        wd_idx = wdir_options.index(wd_val) if wd_val in wdir_options else 0
        c_wdir = st.selectbox("現在の風向", wdir_options, index=wd_idx)

    # --- 5. あなたの過去データから「スズキの好み」を抽出 ---
    if df is not None and not df.empty:
        df_s = df[df['魚種'].str.contains('スズキ', na=False)].copy()
        if df_s.empty: df_s = df.copy()

        fav_tide = df_s['潮名'].mode()[0] if not df_s['潮名'].empty else "大潮"
        fav_phase = df_s['潮位フェーズ'].mode()[0] if not df_s['潮位フェーズ'].empty else "上げ3分"
        fav_wind_dir = df_s['風向'].mode()[0] if not df_s['風向'].empty else "北"
        sample_img = df_s['filename'].iloc[0] if 'filename' in df_s.columns and not df_s['filename'].empty else "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"
    else:
        fav_tide, fav_phase, fav_wind_dir = "大潮", "上げ3分", "北"
        sample_img = "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"

    # --- 6. マッチングスコア計算 ---
    match_score = 10
    if c_tide == fav_tide: match_score += 30
    if c_phase == fav_phase: match_score += 40
    if c_wdir == fav_wind_dir: match_score += 20
    
    # --- 7. 結果表示 ---
    st.markdown("---")
    st.markdown(f"""
        <div class="match-container">
            <div class="profile-card">
                <img src="{sample_img}" class="seabass-img">
                <div style="padding:15px; text-align:left;">
                    <h2 style="margin:0; color:white;">本渡瀬戸のスズキ <span style="font-size:1rem; color:#888;">Now</span></h2>
                    <p style="color:#ccc; font-size:0.9rem; margin-top:10px;">
                        「気温{st.session_state.current_match_data['temp']}℃かぁ。{fav_tide}の{fav_phase}、{fav_wind_dir}風のタイミングなら、あなたに釣られてもいいかな...💋」
                    </p>
                </div>
            </div>
            <div style="font-size: 1.2rem; color: #eee;">現在のマッチング度</div>
            <div style="font-size: 5rem; font-weight: 900; color: #ff416c; line-height:1; margin-bottom:20px;">{match_score}%</div>
        </div>
    """, unsafe_allow_html=True)

    if match_score >= 80:
        st.balloons()
        st.success("🔥 激アツ相性！今すぐ本渡瀬戸へエントリーしてください。")
    elif match_score >= 50:
        st.info("⚡ まずまずの相性。潮の変化に期待しましょう。")
    else:
        st.error("💤 今は「既読スルー」の状態。少し時間を置きましょう。")
