import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 時合精密解析（滑らかな波形・フェーズ同期）")

    if df.empty:
        st.info("データがありません。")
        return

    selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()))
    df_p = df[df["場所"] == selected_place].copy()
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')

    # --- 1. 定数定義（24時を頂点とする12時間周期の1本の波） ---
    CYCLE = 12
    # この波形では 12時、24時、36時 が自動的に満潮（山）になります
    
    def get_sync_coords(row):
        phase_str = str(row['潮位フェーズ'])
        nums = re.findall(r'\d+', phase_str.translate(str.maketrans('０１２３４５６７８９', '0123456789')))
        step = int(nums[0]) if nums else 5
        
        h = row['datetime'].hour + row['datetime'].minute / 60
        shifted_h = h if h >= 12 else h + 24

        # 上げ・下げ判定
        is_up = "上げ" in phase_str
        y = (-100 + (step * 20)) if is_up else (100 - (step * 20))

        # 【ターゲットにする山の決定】
        # 18時までなら12時の山、18時〜30時(朝6時)なら24時の山、それ以降は36時の山
        if shifted_h < 18.0:
            peak = 12.0
        elif shifted_h < 30.0:
            peak = 24.0
        else:
            peak = 36.0

        # フェーズによるX位置の補正（山の左か右か）
        if is_up:
            sync_x = peak - ((10 - step) * 0.6)
        else:
            sync_x = peak + (step * 0.6)

        return pd.Series([sync_x, y])

    df_p[['x_sync', 'y_sync']] = df_p.apply(get_sync_coords, axis=1)

    # --- 2. グラフ描画 ---
    fig = go.Figure()

    # 背景：完全に滑らかな1本の正弦波（12時間周期、24時が頂点）
    x_line = np.linspace(11, 37, 1000)
    y_line = 100 * np.cos(2 * np.pi * (x_line - 24) / 12)
    
    fig.add_trace(go.Scatter(
        x=x_line, y=y_line, mode='lines', 
        line=dict(color='rgba(100, 200, 255, 0.4)', width=3),
        hoverinfo='skip'
    ))

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
                marker=dict(size=18, color=color, symbol=symbol, 
                            line=dict(width=1.5, color='white'), opacity=0.9),
                text=curr_df.apply(lambda r: f"{r['魚種']}{r['全長_cm']}cm", axis=1),
                textposition="top center",
                customdata=curr_df['潮位フェーズ'],
                hovertemplate="<b>%{customdata}</b><br>時刻: %{x:.2f}h<extra></extra>"
            ))

    # レイアウト
    fig.update_layout(
        xaxis=dict(
            tickvals=[12, 18, 21, 24, 27, 30, 36], 
            ticktext=["12:00(満)", "18:00(干)", "21:00", "0:00(満)", "3:00", "6:00(干)", "12:00(満)"], 
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
