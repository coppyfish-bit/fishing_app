import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 時合精密解析（全時間帯・完全同期プロット）")

    if df.empty:
        st.info("データがありません。")
        return

    selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()))
    df_p = df[df["場所"] == selected_place].copy()
    
    # 日時変換
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')
    df_p = df_p.dropna(subset=['datetime'])

    # --- 1. 座標計算ロジック ---
    def get_sync_coords(row):
        phase_str = str(row['潮位フェーズ'])
        # 数字抽出（全角・半角対応）
        nums = re.findall(r'\d+', phase_str.translate(str.maketrans('０１２３４５６７８９', '0123456789')))
        step = int(nums[0]) if nums else 5
        
        # 時刻を12h〜36hスケールに変換
        h = row['datetime'].hour + row['datetime'].minute / 60
        shifted_h = h if h >= 12 else h + 24

        is_up = "上げ" in phase_str
        y = (-100 + (step * 20)) if is_up else (100 - (step * 20))

        # --- 【ターゲット・ピークの決定とX軸の計算】 ---
        # 1. 20時より前：昼のサイクル（12時の山）
        if shifted_h < 20.0:
            peak = 12.0
            if is_up:
                # 12時以前に消えないよう、上げ潮は「12時の山」から「0時の山(左端外)」の間に配置
                # 上げ1分〜9分を 9.0h 〜 12.0h の間にプロット
                sync_x = peak - ((10 - step) * 0.3) 
            else:
                sync_x = peak + (step * 0.6)
        
        # 2. 20時以降：夜のサイクル（24時以降の山）
        else:
            if is_up:
                # 20時〜24時の上げは24時の山へ、24時以降の上げは36時の山へ
                peak = 24.0 if shifted_h < 24.0 else 36.0
                sync_x = peak - ((10 - step) * 0.6)
            else:
                peak = 24.0
                sync_x = peak + (step * 0.6)

        return pd.Series([sync_x, y])

    # 座標計算を実行
    df_p[['x_sync', 'y_sync']] = df_p.apply(get_sync_coords, axis=1)

    # --- 2. グラフ描画 ---
    fig = go.Figure()

    # 背景：滑らかな正弦波（表示範囲を 9時〜37時に拡大して、昼の上げ潮を見えるようにする）
    x_line = np.linspace(8, 38, 1000)
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
                            line=dict(width=1.5, color='white')),
                text=curr_df.apply(lambda r: f"{r['魚種']}{r['全長_cm']}cm", axis=1),
                textposition="top center",
                customdata=curr_df['潮位フェーズ'],
                hovertemplate="<b>%{customdata}</b><br>判定位置: %{x:.1f}h<extra></extra>"
            ))

    # レイアウト
    fig.update_layout(
        xaxis=dict(
            tickvals=[9, 12, 15, 18, 20, 21, 24, 27, 30, 33, 36], 
            ticktext=["(9:00)", "12:00(満)", "15:00", "18:00(干)", "20:00", "21:00", "0:00(満)", "3:00", "6:00(干)", "9:00", "12:00(満)"], 
            range=[8.5, 37.5], # 昼の上げ潮が見えるように左側を拡張
            gridcolor='rgba(255,255,255,0.05)'
        ),
        yaxis=dict(tickvals=[100, 0, -100], ticktext=["満潮", "中間", "干潮"], range=[-150, 200]),
        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        height=650, showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
