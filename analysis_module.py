import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 時合精密解析 (タイドグラフ)")

    if df.empty:
        st.info("データがありません。")
        return

    # --- 1. フィルタリング設定 ---
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()), key="ana_place")
    
    with col_f2:
        all_species = sorted(df[df["場所"] == selected_place]["魚種"].unique())
        initial_targets = ["スズキ", "ヒラスズキ"]
        default_selection = [s for s in initial_targets if s in all_species]
        if not default_selection and all_species:
            default_selection = [all_species[0]]
        selected_species = st.multiselect("🐟 表示する魚種を選択", all_species, default=default_selection, key="ana_species")

    # データの前処理
    df_p = df[df["場所"] == selected_place].copy()
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')
    df_p = df_p.dropna(subset=['datetime'])
    df_p['fish_id'] = df_p['datetime'].dt.strftime('%Y%m%d%H%M%S') + "_" + df_p['魚種']

    # --- 2. 座標計算ロジック ---
    def get_sync_coords(row):
        phase_str = str(row['潮位フェーズ'])
        nums = re.findall(r'\d+', phase_str.translate(str.maketrans('０１２３４５６７８９', '0123456789')))
        step = int(nums[0]) if nums else 5
        h = row['datetime'].hour + row['datetime'].minute / 60
        shifted_h = h if h >= 12 else h + 24
        is_up = "上げ" in phase_str
        y = (-100 + (step * 20)) if is_up else (100 - (step * 20))

        if shifted_h < 20.0:
            peak = 12.0
            sync_x = peak - ((10 - step) * 0.3) if is_up else peak + (step * 0.6)
        else:
            peak = 24.0 if not is_up else (24.0 if shifted_h < 24.0 else 36.0)
            sync_x = peak + (step * 0.6) if not is_up else peak - ((10 - step) * 0.6)
        return pd.Series([sync_x, y])

    if not df_p.empty:
        df_p[['x_sync', 'y_sync']] = df_p.apply(get_sync_coords, axis=1)

    # --- 3. グラフ描画 ---
    fig = go.Figure()
    x_line = np.linspace(8, 38, 1000)
    y_line = 100 * np.cos(2 * np.pi * (x_line - 24) / 12)
    fig.add_trace(go.Scatter(x=x_line, y=y_line, mode='lines', line=dict(color='rgba(100, 200, 255, 0.2)', width=2), hoverinfo='skip'))

    if selected_species:
        for species in selected_species:
            spec_df = df_p[df_p['魚種'] == species]
            if spec_df.empty: continue
            is_up_list = spec_df['潮位フェーズ'].str.contains('上げ')
            symbols = is_up_list.apply(lambda x: 'triangle-up' if x else 'triangle-down')
            colors = is_up_list.apply(lambda x: '#00d4ff' if x else '#ff4b4b')
            
            fig.add_trace(go.Scatter(
                x=spec_df['x_sync'], y=spec_df['y_sync'],
                mode='markers',
                name=species,
                marker=dict(size=18, symbol=symbols, color=colors, line=dict(width=1.5, color='white')),
                customdata=spec_df['fish_id'],
                hovertemplate=f"<b>{species}</b><br>%{{text}}<extra></extra>",
                text=spec_df['潮位フェーズ']
            ))

    fig.update_layout(
        xaxis=dict(tickvals=[12, 18, 24, 30, 36], ticktext=["12:00", "18:00", "0:00", "6:00", "12:00"], range=[8.5, 37.5]),
        yaxis=dict(tickvals=[100, 0, -100], ticktext=["満潮", "中間", "干潮"], range=[-150, 220]),
        template="plotly_dark", height=500, clickmode='event+select'
    )

    st.plotly_chart(fig, use_container_width=True)
