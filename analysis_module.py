import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 時合精密解析（24hシームレス・プロット）")

    if df.empty:
        st.info("データがありません。")
        return

    selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()))
    df_p = df[df["場所"] == selected_place].copy()
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')

    # --- 1. 定数と座標計算関数 ---
    def get_sync_coords(row):
        phase_str = str(row['潮位フェーズ'])
        nums = re.findall(r'\d+', phase_str.translate(str.maketrans('０１２３４５６７８９', '0123456789')))
        step = int(nums[0]) if nums else 5
        
        h = row['datetime'].hour + row['datetime'].minute / 60
        shifted_h = h if h >= 12 else h + 24

        if "上げ" in phase_str:
            y = -100 + (step * 20)
            is_up = True
        else:
            y = 100 - (step * 20)
            is_up = False

        # --- 20時を境にターゲットにする満潮(Peak)を切り替え ---
        if shifted_h < 20.0:
            peak = 15.0  # 昼の山
        elif shifted_h < 30.0:
            peak = 24.0  # 夜の山（24時）
        else:
            peak = 36.0  # 翌朝の山（翌12時）

        # ピークを基準に、フェーズに合わせてX位置を強制吸着
        if is_up:
            sync_x = peak - ((10 - step) * 0.6)
        else:
            sync_x = peak + (step * 0.6)

        return pd.Series([sync_x, y])

    df_p[['x_sync', 'y_sync']] = df_p.apply(get_sync_coords, axis=1)

    # --- 2. グラフ描画 ---
    fig = go.Figure()

    # 背景の波：20時で昼の波と夜の波を無理やり繋ぐ
    x_full = np.linspace(11, 37, 1000)
    y_full = []
    for x in x_full:
        if x < 20:
            # 昼の波 (頂点15時)
            y_full.append(100 * np.cos(2 * np.pi * (x - 15) / 12))
        else:
            # 夜の波 (頂点24時)
            y_full.append(100 * np.cos(2 * np.pi * (x - 24) / 12))
    
    fig.add_trace(go.Scatter(x=x_full, y=y_full, mode='lines', 
                             line=dict(color='rgba(100, 200, 255, 0.4)', width=3),
                             hoverinfo='skip'))

    # 釣果プロット
    for p_type, color, symbol, name in [('上げ', '#00ffd0', 'triangle-up', '上げ潮'), 
                                        ('下げ', '#ff4b4b', 'triangle-down', '下げ潮')]:
        mask = df_p['潮位フェーズ'].str.contains(p_type)
        curr_df = df_p[mask]
        
        if not curr_df.empty:
            fig.add_trace(go.Scatter(
                x=curr_df['x_sync'], y=curr_df['y_sync'],
                mode='markers+text',
                name=name,
                marker=dict(size=18, color=color, symbol=symbol, line=dict(width=1, color='white')),
                text=curr_df.apply(lambda r: f"{r['魚種']}{r['全長_cm']}cm", axis=1),
                textposition="top center",
                customdata=curr_df['潮位フェーズ'],
                hovertemplate="<b>%{customdata}</b><br>判定位置: %{x:.2f}h<extra></extra>"
            ))

    # レイアウト
    fig.update_layout(
        xaxis=dict(
            tickvals=[12, 15, 18, 20, 21, 24, 27, 30, 33, 36], 
            ticktext=["12:00", "15(満)", "18:00", "20:00", "21:00", "0:00(満)", "3:00", "6:00", "9:00", "12:00"], 
            range=[11, 37],
            gridcolor='rgba(255,255,255,0.05)'
        ),
        yaxis=dict(
            tickvals=[100, 0, -100], 
            ticktext=["満潮", "中間", "干潮"], 
            range=[-150, 200],
            gridcolor='rgba(255,255,255,0.05)'
        ),
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=650,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
