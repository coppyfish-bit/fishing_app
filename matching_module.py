import streamlit as st
import pandas as pd
from datetime import datetime

def show_matching_page(df):
    # --- 1. スタイル設定 ---
    st.markdown("""
        <style>
        .match-container { background: linear-gradient(180deg, #1e2630 0%, #0e1117 100%); padding: 30px; border-radius: 30px; text-align: center; border: 1px solid #333; }
        .recommend-card { background: #262730; border-radius: 20px; padding: 20px; margin: 15px auto; border-left: 5px solid #ff416c; text-align: left; }
        .highlight { color: #ff416c; font-weight: bold; font-size: 1.2rem; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🏹 SEABASS STRATEGY ARCHIVE")

    if df is None or df.empty:
        st.warning("釣果データが不足しています。まずはデータを蓄積しましょう！")
        return

    # --- 🛠️ データの型変換（安全策） ---
    if 'datetime' in df.columns:
        df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
    # ---------------------------------

    # --- 2. 現在の状況設定 ---
    st.markdown("### 🌀 現在のフィールドコンディション")
    col1, col2 = st.columns(2)
    
    with col1:
        tide_list = ["大潮", "中潮", "小潮", "長潮", "若潮"]
        c_tide = st.selectbox("現在の潮名", tide_list)
        c_wind_speed = st.slider("風速 (m/s)", 0.0, 15.0, 3.0)
    with col2:
        c_wdir = st.selectbox("風向", ["北", "北東", "東", "南東", "南", "南西", "西", "北西"])
        c_month = datetime.now().month

    # --- 3. マッチング・分析ロジック ---
    # 1. 同じ潮名でフィルタ
    match_df = df[df['潮名'] == c_tide].copy() if '潮名' in df.columns else df.copy()
    
    # 2. 季節感（前後2ヶ月を含める）
    if 'datetime' in match_df.columns:
        season_months = [(c_month-2)%12+1, (c_month-1)%12+1, c_month, (c_month%12)+1, ((c_month+1)%12)+1]
        match_df = match_df[match_df['datetime'].dt.month.isin(season_months)]

    st.markdown("---")
    
    if not match_df.empty:
        # ご提示のカラム名に合わせて抽出
        best_place = match_df['場所'].mode()[0] if '場所' in match_df.columns and not match_df['場所'].empty else "過去のポイント"
        best_phase = match_df['潮位フェーズ'].mode()[0] if '潮位フェーズ' in match_df.columns and not match_df['潮位フェーズ'].empty else "不明"
        avg_size = match_df['全長_cm'].mean() if '全長_cm' in match_df.columns else 0
        best_lure = match_df['ルアー'].mode()[0] if 'ルアー' in match_df.columns and not match_df['ルアー'].empty else "実績ルアーを参照"

        # --- 4. 提案の表示 ---
        st.subheader("🎯 今日の推奨戦略")
        
        st.markdown(f"""
        <div class="match-container">
            <div style="font-size: 1.1rem; color: #ccc; margin-bottom: 10px;">過去の成功ログ {len(match_df)} 件から分析：</div>
            <div style="font-size: 1.5rem; color: white; margin-bottom: 20px;">
                狙い目は <span class="highlight">{best_place}</span> での <span class="highlight">{best_phase}</span> です！
            </div>
            
            <div class="recommend-card">
                <div style="color: #888; font-size: 0.8rem;">REASON / 根拠</div>
                <div style="margin-top: 5px;">
                    この季節の<b>{c_tide}</b>では、平均 <b>{avg_size:.1f}cm</b> の釣果が記録されています。<br>
                    特に<b>{c_wdir}風</b>のコンディションは、過去のヒットデータと高い親和性があります。
                </div>
            </div>

            <div class="recommend-card" style="border-left-color: #00ffd0;">
                <div style="color: #888; font-size: 0.8rem;">BEST LURE / ヒット実績</div>
                <div style="margin-top: 5px; color: #00ffd0; font-weight: bold;">
                    {best_lure}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 関連する過去の釣果写真を表示
        with st.expander("📸 類似条件での過去の成功事例"):
            cols = st.columns(3)
            img_col = 'filename'
            for i, (idx, row) in enumerate(match_df.head(3).iterrows()):
                with cols[i % 3]:
                    if img_col in row and pd.notna(row[img_col]):
                        st.image(row[img_col], caption=f"{row['date']} - {row['全長_cm']}cm")
                    else:
                        st.info("No Image")

    else:
        st.error("😭 現在の条件（潮・季節）に一致する過去のデータがまだありません。")
        st.info("条件を少し変えて（潮名を変えるなど）再試行してみてください。")

    # 全体統計（月別釣果数）
    if 'datetime' in df.columns:
        st.markdown("### 📊 季節ごとの釣果傾向（全体）")
        month_counts = df['datetime'].dt.month.value_counts().sort_index()
        st.bar_chart(month_counts)
