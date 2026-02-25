import streamlit as st
import pandas as pd
from datetime import datetime

def show_matching_page(df):
    # --- 1. デザインCSS（二重波括弧でSyntaxErrorを防止） ---
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
        .status-badge {{
            background: rgba(0, 255, 208, 0.1);
            color: #00ffd0;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.8rem;
            margin: 5px;
            display: inline-block;
        }}
        </style>
    """, unsafe_allow_html=True)

    st.title("💖 SEABASS MATCH")
    
    # --- 2. セッション状態の初期化 ---
    if 'current_match_data' not in st.session_state:
        st.session_state.current_match_data = {
            'tide': "中潮", 'wind': 3.0, 'phase': "上げ3分", 'wdir': "北"
        }

    # --- 3. リアルタイムデータ取得ボタン ---
    st.markdown("### 1. 今のコンディションを提示する")
    
if st.button("🌊 本渡瀬戸の今を自動取得する", use_container_width=True, type="primary"):
        with st.spinner("本渡瀬戸のデータを同期中..."):
            try:
                # --- ここを修正 ---
                # app.py全体をインポートせず、関数だけをピンポイントで取り出す
                from app import get_weather_data_openmeteo, get_tide_details, get_moon_age, get_tide_name 
                
                LAT_HONDO = 32.4333
                LON_HONDO = 130.2167
                now = datetime.now()
                
                # 関数を直接呼び出す（app. をつけない）
                temp, wind_s, wind_d, rain = get_weather_data_openmeteo(LAT_HONDO, LON_HONDO, now)
                tide_data = get_tide_details('HS', now)
                m_age = get_moon_age(now)
                t_name = get_tide_name(m_age)
                # -----------------
                
                st.session_state.current_match_data['tide'] = t_name
                st.session_state.current_match_data['wind'] = float(wind_s) if wind_s else 3.0
                st.session_state.current_match_data['wdir'] = wind_d if wind_d else "北"
                if tide_data and 'phase' in tide_data:
                    st.session_state.current_match_data['phase'] = tide_data['phase']
                
                st.toast("✅ 本渡瀬戸の最新データを取得しました！")
                st.rerun()
            except Exception as e:
                st.error(f"データ取得エラー: {e}")

    # --- 4. 入力エリア ---
    col1, col2 = st.columns(2)
    
    tide_options = ["大潮", "中潮", "小潮", "長潮", "若潮"]
    phase_options = ["上げ1分", "上げ2分", "上げ3分", "上げ4分", "上げ5分", "上げ6分", "上げ7分", "上げ8分", "上げ9分",
                     "下げ1分", "下げ2分", "下げ3分", "下げ4分", "下げ5分", "下げ6分", "下げ7分", "下げ8分", "下げ9分",
                     "満潮付近", "干潮付近"]
    wdir_options = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]

    with col1:
        t_val = st.session_state.current_match_data['tide']
        t_idx = tide_options.index(t_val) if t_val in tide_options else 0
        c_tide = st.selectbox("現在の潮", tide_options, index=t_idx)
        
        c_wind = st.slider("現在の風速 (m/s)", 0.0, 15.0, st.session_state.current_match_data['wind'])
        
    with col2:
        p_val = st.session_state.current_match_data['phase']
        p_idx = phase_options.index(p_val) if p_val in phase_options else 2
        c_phase = st.selectbox("現在の時合", phase_options, index=p_idx)
        
        wd_val = st.session_state.current_match_data['wdir']
        wd_idx = wdir_options.index(wd_val) if wd_val in wdir_options else 0
        c_wdir = st.selectbox("現在の風向", wdir_options, index=wd_idx)

    # --- 5. 分析ロジック（スズキの好み） ---
    if df is not None and not df.empty:
        df_s = df[df['魚種'].str.contains('スズキ', na=False)].copy()
        if df_s.empty:
            df_s = df.copy()

        fav_tide = df_s['潮名'].mode()[0] if not df_s['潮名'].empty else "大潮"
        fav_phase = df_s['潮位フェーズ'].mode()[0] if not df_s['潮位フェーズ'].empty else "上げ3分"
        fav_wind_dir = df_s['風向'].mode()[0] if not df_s['風向'].empty else "北"
        sample_img = df_s['filename'].iloc[0] if 'filename' in df_s.columns and not df_s['filename'].empty else "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"
    else:
        fav_tide, fav_phase, fav_wind_dir = "大潮", "上げ3分", "北"
        sample_img = "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"

    # --- 6. スコア計算 ---
    match_score = 10
    if c_tide == fav_tide: match_score += 30
    if c_phase == fav_phase: match_score += 40
    if c_wdir == fav_wind_dir: match_score += 20
    
    # --- 7. 結果表示 ---
    st.markdown("---")
    html_content = f"""
        <div class="match-container">
            <div class="profile-card">
                <img src="{sample_img}" class="seabass-img">
                <div style="padding:15px; text-align:left;">
                    <h2 style="margin:0; color:white;">スズキ (Seabass) <span style="font-size:1rem; color:#888;">24歳</span></h2>
                    <p style="color:#ccc; font-size:0.9rem; margin-top:10px;">
                        「{fav_tide}の{fav_phase}に、{fav_wind_dir}風が吹いてるとつい口を使っちゃうかも...💋」
                    </p>
                    <div class="status-badge">#偏食家</div><div class="status-badge">#シャロー好き</div>
                </div>
            </div>
            <div style="font-size: 1.2rem; color: #eee;">マッチング度</div>
            <div style="font-size: 5rem; font-weight: 900; color: #ff416c; line-height:1; margin-bottom:20px;">{match_score}%</div>
        </div>
    """
    st.markdown(html_content, unsafe_allow_html=True)

    if match_score >= 80:
        st.balloons()
        st.success("🔥 運命の出会い！今すぐ本渡瀬戸へ向かってください。")
    elif match_score >= 50:
        st.info("⚡ 悪くない相性です。粘ればチャンスがあるかも？")
    else:
        st.error("💤 スズキは今、寝ているようです。家でルアーを磨きましょう。")

