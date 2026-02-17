import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 時合精密解析（24時満潮・深夜上げ対応）")

    if df.empty:
        st.info("データがありません。")
        return

    selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()))
    df_p = df[df["場所"] == selected_place].copy()
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')

    # --- 1. 座標計算ロジック ---
    def get_sync_coords(row):
        phase_str = str(row['潮位フェーズ'])
        # 数字を抽出（全角・半角対応）
        nums = re.findall(r'\d+', phase_str.translate(str.maketrans('０１２３４５６７８９', '0123456789')))
        step = int(nums[0]) if nums else 5
        
        # 時刻を12h〜36hスケールに変換 (0時は24, 3時は27)
        h = row['datetime'].hour + row['datetime'].minute / 60
        shifted_h = h if h >= 12 else h + 24

        # 【上げ・下げの基本Y座標】
        if "上げ" in phase_str:
            y = -100 + (step * 20)
            is_up = True
        else: # 下げ
            y = 100 - (step * 20)
            is_up = False

        # 【X座標の決定：24時を境にした振り分け】
        # 1. 24時より前 (12:00〜24:00)
        if shifted_h < 24.0:
            if is_up:
                # 24時の山の左側（上り坂）
                sync_x = 24.0 - ((10 - step) * 0.6)
            else:
                # 12時の山の右側（下り坂） または 24時の山の右側への遷移
                # 21時などの下げなら、基本は中央の山の左側の「下げ」はないので、時刻に近い方の波へ
                sync_x = 12.0 + (step * 0.6) if shifted_h < 18 else 24.0 + (step * 0.6)
        
        # 2. 24時より後 (0:00〜12:00 / グラフの24h〜36h)
        else:
            if is_up:
                # 深夜3時の上げ5分などは、右側の谷から36時の山に向かう「右端の上り坂」
                sync_x = 36.0 - ((10 - step) * 0.6)
            else:
                # 24時の山の右側（下り坂）
                sync_x = 24.0 + (step * 0.6)

        return pd.Series([sync_x, y])

    # 座標計算を実行
    df_p[['x_sync', 'y_sync']] = df_p.apply(get_sync_coords, axis=1)

    # --- 2. グラフ描画 ---
    fig = go.Figure()

    # 背景：24時を満潮の頂点とする曲線
    x_line = np.linspace(12, 36, 1000)
    y_line = 100 * np.cos(2 * np.pi * (x_line - 24) / 12)
    fig.add_trace(go.Scatter(x=x_line, y=y_line, mode='lines', 
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
                marker=dict(size=18, color=color, symbol=symbol, line=dict(width=1.5, color='white')),
                text=curr_df.apply(lambda r: f"{r['魚種']}{r['全長_cm']}cm", axis=1),
                textposition="top center",
                customdata=curr_df['潮位フェーズ'],
                hovertemplate="<b>%{customdata}</b><br>判定位置: %{x:.2f}h<extra></extra>"
            ))

    # レイアウト
    fig.update_layout(
        xaxis=dict(
            tickvals=[12, 18, 21, 24, 27, 30, 36], 
            ticktext=["12:00", "18:00", "21:00", "0:00(満潮)", "3:00", "6:00", "12:00"], 
            range=[12, 36]
        ),
        yaxis=dict(
            tickvals=[100, 0, -100], 
            ticktext=["満潮", "中間", "干潮"], 
            range=[-150, 200]
        ),
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=650,
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)
