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
        st.warning("分析に必要な「スズキ」のデータがまだありません。")
        return

    # 数値変換
    df_suzuki['length_num'] = pd.to_numeric(df_suzuki['全長_cm'], errors='coerce').fillna(0)
    df_suzuki['tide_cm'] = pd.to_numeric(df_suzuki['潮位_cm'], errors='coerce').fillna(0)

    # --- 風向を16方位から8方位に変換する処理 ---
    wind_map = {
        '北': '北', '北北東': '北東', '北東': '北東', '東北東': '北東',
        '東': '東', '東南東': '南東', '南東': '南東', '南南東': '南東',
        '南': '南', '南南西': '南西', '南西': '南西', '西北西': '南西',
        '西': '西', '西北西': '北西', '北西': '北西', '北北西': '北西'
    }
    if '風向' in df_suzuki.columns:
        df_suzuki['風向_8'] = df_suzuki['風向'].map(wind_map).fillna(df_suzuki['風向'])

    st.header("🎯 スズキ専用 戦略分析")

    # --- 2. 場所ごとのピンポイント実績 (カード表示) ---
    st.subheader("📍 場所別・特選データ")
    selected_place = st.selectbox("分析する場所を選択", df_suzuki['場所'].unique())
    
    if selected_place:
        p_df = df_suzuki[df_suzuki['場所'] == selected_place]
        
        # 各種計算
        max_size = p_df['length_num'].max()
        max_tide = p_df['tide_cm'].max()
        
        # 最多ヒット潮時（潮位フェーズ）
        top_phase = p_df['潮位フェーズ'].mode()[0] if not p_df['潮位フェーズ'].empty else "-"
        
        # 最多ヒット潮位（20cm刻みのレンジで集計）
        p_df['tide_range'] = (p_df['tide_cm'] // 20 * 20).astype(int)
        top_tide_range = p_df['tide_range'].mode()[0] if not p_df['tide_range'].empty else 0

        c1, c2 = st.columns(2)
        with c1:
            st.metric("最大サイズ", f"{max_size} cm")
            st.metric("最多ヒット潮時", f"{top_phase}")
        with c2:
            st.metric("最大ヒット潮位", f"{max_tide} cm")
            st.metric("最多ヒット潮位域", f"{top_tide_range} ～ {top_tide_range+20} cm")

    st.markdown("---")
    config = {'scrollZoom': False, 'displayModeBar': False}

    # --- 3. グラフ：8方位風向実績 ---
    if '風向_8' in df_suzuki.columns:
        st.write("🌬️ 風向別実績（8方位集約）")
        wind_stats = df_suzuki['風向_8'].value_counts().reset_index()
        wind_stats.columns = ['風向', '件数']
        # 風向を時計回りに並び替え
        wind_order = ['北', '北東', '東', '南東', '南', '南西', '西', '北西']
        wind_stats['風向'] = pd.Categorical(wind_stats['風向'], categories=wind_order, ordered=True)
        wind_stats = wind_stats.sort_values('風向')
        
        fig_wind = px.bar(wind_stats, x='風向', y='件数', color='件数', color_continuous_scale='Blues')
        apply_mobile_style(fig_wind)
        st.plotly_chart(fig_wind, use_container_width=True, config=config)

    # --- 4. グラフ：場所別サイズ分布（箱ひげ図） ---
    st.write("📏 場所別の全長実績")
    fig_loc = px.box(df_suzuki, x='場所', y='length_num', color='場所', points="all")
    apply_mobile_style(fig_loc)
    st.plotly_chart(fig_loc, use_container_width=True, config=config)

    # --- 5. グラフ：潮名別実績 ---
    st.write("🌊 潮名別の実績")
    tide_stats = df_suzuki.groupby('潮名').agg(釣果数=('魚種', 'count'), 平均全長=('length_num', 'mean')).reset_index()
    fig_tide = px.bar(tide_stats, x='潮名', y='釣果数', color='平均全長', color_continuous_scale='Viridis')
    apply_mobile_style(fig_tide)
    st.plotly_chart(fig_tide, use_container_width=True, config=config)

    # --- 6. グラフ：ヒットルアー TOP10 ---
    st.write("🎣 ヒットルアー TOP10")
    lure_stats = df_suzuki['ルアー'].value_counts().reset_index().head(10)
    lure_stats.columns = ['ルアー', '個数']
    fig_lure = px.bar(lure_stats, x='個数', y='ルアー', orientation='h', color_discrete_sequence=['#00ffd0'])
    fig_lure.update_layout(yaxis={'categoryorder':'total ascending'})
    apply_mobile_style(fig_lure)
    st.plotly_chart(fig_lure, use_container_width=True, config=config)

def apply_mobile_style(fig):
    fig.update_layout(
        margin=dict(l=10, r=10, t=30, b=10),
        dragmode=False,
        xaxis=dict(fixedrange=True),
        yaxis=dict(fixedrange=True),
        hovermode="closest",
        height=350
    )
