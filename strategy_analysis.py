import streamlit as st
import pandas as pd
import plotly.express as px

def show_strategy_analysis(df):
    if df is None or df.empty:
        st.info("データがありません。")
        return

    # 1. データの準備
    df_suzuki = df.copy()
    df_suzuki = df_suzuki[(df_suzuki['魚種'] == "スズキ") & (~df_suzuki['魚種'].isin(["テスト", "ボウズ"]))]
    
    if df_suzuki.empty:
        st.warning("スズキのデータが不足しています。")
        return

    # 数値変換
    df_suzuki['length_num'] = pd.to_numeric(df_suzuki['全長_cm'], errors='coerce').fillna(0)
    df_suzuki['tide_cm'] = pd.to_numeric(df_suzuki['潮位_cm'], errors='coerce').fillna(0)
    
    # 8方位変換マップ
    wind_map = {
        '北': '北', '北北東': '北東', '北東': '北東', '東北東': '北東',
        '東': '東', '東南東': '南東', '南東': '南東', '南南東': '南東',
        '南': '南', '南南西': '南西', '南西': '南西', '西北西': '南西',
        '西': '西', '西北西': '北西', '北西': '北西', '北北西': '北西'
    }
    if '風向' in df_suzuki.columns:
        df_suzuki['風向_8'] = df_suzuki['風向'].map(wind_map).fillna(df_suzuki['風向'])

    st.header("🎯 スズキ専用 戦略分析")

    # --- 2. 場所の選択 ---
    places = [p for p in df_suzuki['場所'].unique() if p]
    selected_place = st.selectbox("分析する場所を選択してください", places)

    if selected_place:
        # その場所のデータだけに絞り込み
        p_df = df_suzuki[df_suzuki['場所'] == selected_place].copy()

        # --- 3. 場所別・特選データ (カード表示) ---
        st.subheader(f"📍 {selected_place} の特選実績")
        
        # 計算ロジック
        max_size = p_df['length_num'].max()
        max_tide = p_df['tide_cm'].max()
        top_phase = p_df['潮位フェーズ'].mode()[0] if not p_df['潮位フェーズ'].empty else "-"
        
        # 最多ヒット潮位域
        p_df['tide_range'] = (p_df['tide_cm'] // 20 * 20).astype(int)
        top_tide_val = p_df['tide_range'].mode()[0] if not p_df['tide_range'].empty else 0

        # 「下げ○分」の算出（直前の満潮時刻からの経過時間を計算）
        # ※データに「直前の満潮_時刻」がある場合
        p_df['datetime'] = pd.to_datetime(p_df['datetime'], errors='coerce')
        p_df['last_high_tide'] = pd.to_datetime(p_df['直前の満潮_時刻'], errors='coerce')
        p_df['mins_since_high'] = (p_df['datetime'] - p_df['last_high_tide']).dt.total_seconds() / 60
        
        # 下げフェーズのみを抽出して平均を出す
        ebb_df = p_df[p_df['潮位フェーズ'].str.contains('下げ', na=False)]
        avg_ebb_mins = int(ebb_df['mins_since_high'].mean()) if not ebb_df.empty else 0

        c1, c2 = st.columns(2)
        with c1:
            st.metric("歴代最大サイズ", f"{max_size} cm")
            st.metric("最多ヒット潮時", f"{top_phase}")
        with c2:
            st.metric("最大ヒット潮位", f"{max_tide} cm")
            st.metric(f"最多ヒット時合", f"下げ {avg_ebb_mins} 分")
        
        st.caption(f"※最多ヒット潮位域: {top_tide_val} ～ {top_tide_val+20} cm")

        st.markdown("---")
        config = {'scrollZoom': False, 'displayModeBar': False}

        # --- 4. その場所の個別グラフ一覧 ---
        col_a, col_b = st.columns(2)

        with col_a:
            # 風向別実績
            st.write("🌬️ 有利な風向き")
            w_stats = p_df['風向_8'].value_counts().reset_index()
            w_stats.columns = ['風向', '件数']
            fig_w = px.bar(w_stats, x='風向', y='件数', color='件数', color_continuous_scale='Blues')
            apply_mobile_style(fig_w)
            st.plotly_chart(fig_w, use_container_width=True, config=config)

        with col_b:
            # 潮名別実績
            st.write("🌊 有利な潮名")
            t_stats = p_df.groupby('潮名').size().reset_index(name='件数')
            fig_t = px.bar(t_stats, x='潮名', y='件数', color='件数', color_continuous_scale='Viridis')
            apply_mobile_style(fig_t)
            st.plotly_chart(fig_t, use_container_width=True, config=config)

        # ヒットルアー TOP10
        st.write("🎣 この場所のヒットルアー TOP10")
        l_stats = p_df['ルアー'].value_counts().reset_index().head(10)
        l_stats.columns = ['ルアー', '個数']
        fig_l = px.bar(l_stats, x='個数', y='ルアー', orientation='h', color_discrete_sequence=['#00ffd0'])
        fig_l.update_layout(yaxis={'categoryorder':'total ascending'})
        apply_mobile_style(fig_l, height=400)
        st.plotly_chart(fig_l, use_container_width=True, config=config)

def apply_mobile_style(fig, height=300):
    fig.update_layout(
        margin=dict(l=5, r=5, t=30, b=10),
        dragmode=False,
        xaxis=dict(fixedrange=True),
        yaxis=dict(fixedrange=True),
        hovermode="closest",
        height=height
    )
