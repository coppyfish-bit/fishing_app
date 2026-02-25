import streamlit as st
import pandas as pd

def show_matching_page(df):
    # --- デザインCSS ---
    st.markdown("""
        <style>
        .match-container {
            background: linear-gradient(180deg, #1e2630 0%, #0e1117 100%);
            padding: 30px;
            border-radius: 30px;
            text-align: center;
            border: 1px solid #333;
        }
        .profile-card {
            background: #262730;
            border-radius: 20px;
            padding: 10px;
            margin: 20px auto;
            max-width: 400px;
            box-shadow: 0 15px 35px rgba(255, 65, 108, 0.3);
            border: 2px solid #ff416c;
        }
        .seabass-img {
            width: 100%;
            border-radius: 15px;
            aspect-ratio: 1/1;
            object-fit: cover;
        }
        .heart-btn {
            background: #ff416c;
            color: white;
            padding: 15px 30px;
            border-radius: 50px;
            font-size: 1.5rem;
            font-weight: bold;
            display: inline-block;
            margin-top: 20px;
            box-shadow: 0 5px 15px rgba(255, 65, 108, 0.4);
            text-decoration: none;
        }
        .status-badge {
            background: rgba(0, 255, 208, 0.1);
            color: #00ffd0;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.8rem;
            margin: 5px;
            display: inline-block;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("💖 SEABASS MATCH")
    st.caption("KTD Matching Algorithm v1.0")

    if df is None or df.empty:
        st.warning("まだデータがありません。釣果を記録してスズキの『タイプ』を分析しましょう。")
        return

    # --- 分析ロジック ---
    # スズキ系のみ抽出
    df_s = df[df['魚種'].str.contains('スズキ', na=False)]
    if df_s.empty: df_s = df

    # スズキの好みを抽出
    fav_tide = df_s['潮名'].mode()[0] if not df_s['潮名'].empty else "大潮"
    fav_phase = df_s['潮位フェーズ'].mode()[0] if not df_s['潮位フェーズ'].empty else "上げ3分"
    fav_wind_dir = df_s['風向'].mode()[0] if not df_s['風向'].empty else "北"

    # --- 入力エリア ---
    st.markdown("### 今日のコンディションを提示する")
    col1, col2 = st.columns(2)
    with col1:
        c_tide = st.selectbox("現在の潮", ["大潮", "中潮", "小潮", "長潮", "若潮"])
        c_wind = st.slider("現在の風速 (m/s)", 0.0, 15.0, 3.0)
    with col2:
        c_phase = st.selectbox("現在の時合", ["上げ3分", "上げ7分", "下げ3分", "下げ7分", "干潮付近", "満潮付近"])
        c_wdir = st.selectbox("現在の風向", ["北", "北東", "東", "南東", "南", "南西", "西", "北西"])

    # --- スコア計算 ---
    match_score = 10
    if c_tide == fav_tide: match_score += 30
    if c_phase == fav_phase: match_score += 40
    if c_wdir == fav_wind_dir: match_score += 20
    
    # --- 結果表示 ---
    st.markdown("---")
    
    # 代表的な1枚を取得（なければデフォルト画像）
    sample_img = df_s['filename'].iloc[0] if not df_s['filename'].empty else "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"

    st.markdown(f"""
        <div class="match-container">
            <div class="profile-card">
                <img src="{sample_img}" class="seabass-img">
                <div style="padding:15px; text-align:left;">
                    <h2 style="margin:0;">スズキ (Seabass) <span style="font-size:1rem; color:#888;">24歳</span></h2>
                    <p style="color:#ccc; font-size:0.9rem;">「{fav_tide}の{fav_phase}に、{fav_wdir}風が吹いてるとつい口を使っちゃうかも...💋」</p>
                    <div class="status-badge">#偏食家</div><div class="status-badge">#シャロー好き</div>
                </div>
            </div>
            <div style="font-size: 1.2rem; color: #eee;">マッチング度</div>
            <div style="font-size: 4rem; font-weight: 900; color: #ff416c; line-height:1;">{match_score}%</div>
        </div>
    """, unsafe_allow_html=True)

    if match_score >= 80:
        st.balloons()
        st.success("🔥 運命の出会い！今すぐポイントへ向かってください。")
    elif match_score >= 50:
        st.info("⚡ 悪くない相性です。粘ればチャンスがあるかも？")
    else:
        st.error("💤 スズキは今、寝ているようです。家でルアーを磨きましょう。")