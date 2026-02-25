import streamlit as st
import pandas as pd
from datetime import datetime
import app  # 気象取得関数を利用するためにインポート

def show_matching_page(df):
    # --- デザインCSS（既存のスタイルを維持） ---
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
    
    # --- 🛠️ 追加：リアルタイムデータ取得ボタン ---
    st.markdown("### 1. 今のコンディションを提示する")
    
    # セッション状態の初期化
    if 'current_match_data' not in st.session_state:
        st.session_state.current_match_data = {
            'tide': "中潮", 'wind': 3.0, 'phase': "上げ3分", 'wdir': "北"
        }

    if st.button("🌊 本渡瀬戸の今を自動取得する", use_container_width=True, type="primary"):
        with st.spinner("本渡瀬戸のデータを取得中..."):
            # 本渡瀬戸の座標 (app.pyのTIDE_STATIONSから引用)
            LAT_HONDO = 32.4333
            LON_HONDO = 130.2167
            now = datetime.now()
            
            # 1. 気象取得 (app.pyの関数を利用)
            temp, wind_s, wind_d, rain = app.get_weather_data_openmeteo(LAT_HONDO, LON_HONDO, now)
            
            # 2. 潮位取得 (app.pyの関数を利用)
            # 本渡瀬戸のコードは 'HS'
            tide_data = app.get_tide_details('HS', now)
            
            # 3. 潮名（月齢から算出）
            m_age = app.get_moon_age(now)
            t_name = app.get_tide_name(m_age)
            
            # セッションに保存
            st.session_state.current_match_data['tide'] = t_name
            st.session_state.current_match_data['wind'] = float(wind_s) if wind_s else 3.0
            st.session_state.current_match_data['wdir'] = wind_d if wind_d else "北"
            if tide_data and 'phase' in tide_data:
                st.session_state.current_match_data['phase'] = tide_data['phase']
            
            st.toast("✅ 本渡瀬戸の最新データを同期しました！")

    # --- 入力エリア (自動取得した値をデフォルトに設定) ---
    col1, col2 = st.columns(2)
    with col1:
        c_tide = st.selectbox("現在の潮", ["大潮", "中潮", "小潮", "長潮", "若潮"], 
                              index=["大潮", "中潮", "小潮", "長潮", "若潮"].index(st.session_state.current_match_data['tide']))
        c_wind = st.slider("現在の風速 (m/s)", 0.0, 15.0, st.session_state.current_match_data['wind'])
    with col2:
        # フェーズは選択肢にない場合を考慮して安全にインデックス取得
        phase_list = ["上げ3分", "上げ7分", "下げ3分", "下げ7分", "干潮付近", "満潮付近"]
        default_phase = st.session_state.current_match_data['phase']
        phase_idx = phase_list.index(default_phase) if default_phase in phase_list else 0
        
        c_phase = st.selectbox("現在の時合", phase_list, index=phase_idx)
        
        wdir_list = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
        default_wdir = st.session_state.current_match_data['wdir']
        wdir_idx = wdir_list.index(default_wdir) if default_wdir in wdir_list else 0
        c_wdir = st.selectbox("現在の風向", wdir_list, index=wdir_idx)

    # --- スコア計算 ---
    match_score = 10
    if c_tide == fav_tide: match_score += 30
    if c_phase == fav_phase: match_score += 40
    if c_wdir == fav_wind_dir: match_score += 20
    
    # --- 結果表示 ---
    st.markdown("---")
    
    # 代表的な1枚を取得
    sample_img = df_s['filename'].iloc[0] if 'filename' in df_s.columns and not df_s['filename'].empty else "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"

    # HTML表示部分（変数を確実に埋め込むために f-string を使用）
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
        st.success("🔥 運命の出会い！今すぐポイントへ向かってください。")
    elif match_score >= 50:
        st.info("⚡ 悪くない相性です。粘ればチャンスがあるかも？")
    else:
        st.error("💤 スズキは今、寝ているようです。家でルアーを磨きましょう。")

