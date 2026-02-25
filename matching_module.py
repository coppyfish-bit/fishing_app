import streamlit as st
import pandas as pd
from datetime import datetime

def show_matching_page(df):
    # --- 1. スタイル設定（変更なし） ---
    st.markdown("""
        <style>
        .match-container { background: linear-gradient(180deg, #1e2630 0%, #0e1117 100%); padding: 30px; border-radius: 30px; text-align: center; border: 1px solid #333; }
        .recommend-card { background: #262730; border-radius: 20px; padding: 20px; margin: 15px auto; border-left: 5px solid #ff416c; text-align: left; }
        .highlight { color: #ff416c; font-weight: bold; font-size: 1.2rem; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🏹 SEABASS STRATEGY ARCHIVE")
    st.caption("過去の成功データから、今日の最適解を導き出す")

    if df is None or df.empty:
        st.warning("釣果データが不足しています。まずはデータを蓄積しましょう！")
        return

    # --- 2. 現在の状況設定 ---
    st.markdown("### 🌀 現在のフィールドコンディションを入力")
    col1, col2 = st.columns(2)
    
    with col1:
        c_tide = st.selectbox("現在の潮名", ["大潮", "中潮", "小潮", "長潮", "若潮"])
        c_wind_speed = st.slider("風速 (m/s)", 0.0, 15.0, 3.0)
    with col2:
        c_wdir = st.selectbox("風向", ["北", "北東", "東", "南東", "南", "南西", "西", "北西"])
        c_month = datetime.now().month

    # --- 3. マッチング・分析ロジック ---
    # 過去のデータから、現在の条件（潮・月・風向）に近い釣果をフィルタリング
    # 1. 同じ潮名
    match_df = df[df['潮名'] == c_tide].copy()
    
    # 2. 季節感（前後1ヶ月を含める）
    season_months = [(c_month-2)%12+1, (c_month-1)%12+1, c_month, (c_month%12)+1]
    match_df = match_df[match_df['日付'].dt.month.isin(season_months)]

    st.markdown("---")
    
    if not match_df.empty:
        # 最も釣果が多い「釣り場」を特定
        best_place = match_df['釣り場'].mode()[0] if not match_df['釣り場'].empty else "不明"
        # 最も釣果が多い「時合（フェーズ）」を特定
        best_phase = match_df['潮位フェーズ'].mode()[0] if not match_df['潮位フェーズ'].empty else "不明"
        # その条件での平均サイズ
        avg_size = match_df['全長(cm)'].mean()
        # ヒットルアーの傾向
        best_lure = match_df['使用ルアー'].mode()[0] if '使用ルアー' in match_df.columns and not match_df['使用ルアー'].empty else "過去のヒットルアーを参照"

        # --- 4. 提案の表示 ---
        st.subheader("🎯 今日の推奨戦略")
        
        st.markdown(f"""
        <div class="match-container">
            <div style="font-size: 1.1rem; color: #ccc; margin-bottom: 10px;">あなたの過去の統計に基づくと...</div>
            <div style="font-size: 1.5rem; color: white; margin-bottom: 20px;">
                今日は <span class="highlight">{best_place}</span> での <span class="highlight">{best_phase}</span> が最も期待できます！
            </div>
            
            <div class="recommend-card">
                <div style="color: #888; font-size: 0.8rem;">REASON / 根拠</div>
                <div style="margin-top: 5px;">
                    この時期の<b>{c_tide}</b>では、過去に平均 <b>{avg_size:.1f}cm</b> のスズキがキャッチされています。<br>
                    特に<b>{c_wdir}風</b>が絡むと、{best_place}の特定のピンポイントが熱くなる傾向があります。
                </div>
            </div>

            <div class="recommend-card" style="border-left-color: #00ffd0;">
                <div style="color: #888; font-size: 0.8rem;">RECOMMENDED LURE / 推奨</div>
                <div style="margin-top: 5px; color: #00ffd0; font-weight: bold;">
                    {best_lure}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 関連する過去の釣果写真を表示
        with st.expander("📸 類似条件での過去の釣果を確認"):
            cols = st.columns(3)
            for i, row in match_df.head(3).iterrows():
                with cols[i % 3]:
                    if 'filename' in row and row['filename']:
                        st.image(row['filename'], caption=f"{row['日付'].strftime('%Y/%m/%d')} - {row['全長(cm)']}cm")

    else:
        st.error("😭 現在の条件（潮・季節）に一致する過去のデータが見つかりませんでした。")
        st.info("新しい条件で調査し、データを蓄積して次回のマッチング精度を高めましょう！")

    # 最後に全体的な統計を表示
    st.markdown("### 📊 この条件のヒット率（月別）")
    tide_stats = df[df['潮名'] == c_tide]['日付'].dt.month.value_counts().sort_index()
    st.bar_chart(tide_stats)
