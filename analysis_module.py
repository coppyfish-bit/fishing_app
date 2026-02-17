import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 時合精密解析（昼・夜・深夜全対応版）")

    if df.empty:
        st.info("データがありません。")
        return

    selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()))
    df_p = df[df["場所"] == selected_place].copy()
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')

    # --- 1. 座標計算ロジック ---
    def get_sync_coords(row):
        phase_str = str(row['潮位フェーズ'])
        # 数字を抽出
        nums = re.findall(r'\d+', phase_str.translate(str.maketrans('０１２３４５６７８９', '0123456789')))
        step = int(nums[0]) if nums else 5
        
        # 時刻を12h〜36hスケールに変換
        h = row['datetime'].hour + row['datetime'].minute / 60
        shifted_h = h if h >= 12 else h + 24

        # 上げ・下げの高さ(Y)
        if "上げ" in phase_str:
            y = -100 + (step * 20)
            is_up = True
        else:
            y = 100 - (step * 20)
            is_up = False

        # --- 【波の振り分けロジック】 ---
        # 1. 20時より前 (昼の波) -> 頂点を15時に設定して表示を安定させる
        if shifted_h < 20.0:
            peak = 15.0 
            if is_up:
                sync_x = peak - ((10 - step) * 0.6) # 15時の左側(上り)
            else:
                sync_x = peak + (step * 0.6)        # 15時の右側(下り)
        
        # 2. 20時以降 (夜の波) -> 頂点は24時
        else:
            peak = 24.0
            if is_up:
                # 24時より前なら中央の波の上り坂、24時を過ぎていれば右端の上り坂
                if shifted_h < 24.0:
                    sync_x = 24.0 - ((10 - step) * 0.6)
                else:
                    sync_x = 36.0 - ((10 - step) * 0.6)
            else:
                sync_x = 24.0 + (step * 0.6)

        return pd.Series([sync_x, y])

    # 座標計算を実行
    df_p[['x_sync', 'y_sync']] = df_p.apply(get_sync_coords, axis=1)

    # --- 2. グラフ描画 ---
    fig = go.Figure()

    # 背景：15時と27時(深夜3時)を頂点にする波形 (昼夜のバランスを調整)
    x_line = np.linspace(10, 38, 1000)
    y_line = 100 * np.cos(2 * np.pi * (x_line - 15) / 12)
    
    fig.add_trace(go.Scatter(
        x=x_line, y=y_line, mode='lines', 
        line=dict(color='rgba(100, 200, 255, 0.3)', width=2),
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
                marker=dict(size=18, color=color, symbol=symbol, line=dict(width=1, color='white')),
                text=curr_df.apply(lambda r: f"{r['魚種']}{r['全長_cm']}cm", axis=1),
                textposition="top center",
                customdata=curr_df['潮位フェーズ'],
                hovertemplate="<b>%{customdata}</b><br>判定時刻: %{x:.2f}h<extra></extra>"
            ))

    # レイアウト
    fig.update_layout(
        xaxis=dict(
            tickvals=[12, 15, 18, 21, 24, 27, 30, 33, 36], 
            ticktext=["12:00", "15:00(満)", "18:00", "21:00", "0:00(満)", "3:00", "6:00", "9:00", "12:00"], 
            range=[11, 37]
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
    # 20時の境界線を薄く表示（デバッグ・確認用）
    fig.add_vline(x=20, line_width=1, line_dash="dot", line_color="gray")

    st.plotly_chart(fig, use_container_width=True)
