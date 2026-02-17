import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def show_analysis_page(df):
    st.subheader("📊 時合解析：タイド曲線オーバーレイ")

    if df.empty:
        st.info("データがありません。")
        return

    selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()))
    df_p = df[df["場所"] == selected_place].copy()
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')

    # 1. 時間軸のシフト (12時〜翌12時)
    def shift_h(dt):
        h = dt.hour + dt.minute / 60
        return h if h >= 12 else h + 24
    df_p['x_time'] = df_p['datetime'].apply(shift_h)

    # 2. 正弦波の定義 (周期12時間、振幅100)
    # y = 100 * sin(2π * (x - offset) / 周期)
    # 満潮を18時と6時に設定するオフセット
    def get_wave_y(x):
        return 100 * np.sin(2 * np.pi * (x - 15) / 12)

    # 3. 正弦波の「近く」にポイントを打つための計算
    # 釣行時刻(x)における「波の高さ」をベースに、フェーズで微調整
    def get_phase_y(row):
        try:
            step = int(''.join(filter(str.isdigit, str(row['潮位フェーズ']))))
        except:
            step = 5
        
        # フェーズに基づいた理想的な高さ (満潮100 〜 干潮-100)
        if "上げ" in str(row['潮位フェーズ']):
            return -100 + (step * 20)
        elif "下げ" in str(row['潮位フェーズ']):
            return 100 - (step * 20)
        return get_wave_y(row['x_time'])

    df_p['y_pos'] = df_p.apply(get_phase_y, axis=1)

    # 4. グラフ作成
    fig = go.Figure()

    # 背景：タイド曲線
    x_line = np.linspace(12, 36, 500)
    y_line = get_wave_y(x_line)
    fig.add_trace(go.Scatter(x=x_line, y=y_line, mode='lines', 
                             line=dict(color='rgba(100, 200, 255, 0.4)', width=3),
                             name='タイド曲線', hoverinfo='skip'))

    # 釣果ポイント
    fig.add_trace(go.Scatter(
        x=df_p['x_time'], y=df_p['y_pos'],
        mode='markers+text',
        marker=dict(size=14, color='#00ffd0', symbol='diamond', 
                    line=dict(width=1, color='white'), opacity=1),
        text=df_p.apply(lambda r: f"{r['魚種']}<br>{r['全長_cm']}cm", axis=1),
        textposition="top center",
        customdata=df_p['潮位フェーズ'],
        hovertemplate="<b>%{customdata}</b><br>時刻: %{x:.2f}h<extra></extra>"
    ))

    # レイアウト
    fig.update_layout(
        xaxis=dict(tickvals=[12, 18, 24, 30, 36], 
                   ticktext=["12:00", "18:00", "深夜 0:00", "6:00", "12:00"], range=[12, 36]),
        yaxis=dict(tickvals=[100, 0, -100], ticktext=["満潮", "中間", "干潮"], range=[-140, 160]),
        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        height=500, showlegend=False
    )
    
    # 深夜0時ライン
    fig.add_vline(x=24, line_width=2, line_color="orange", line_dash="dash")

    st.plotly_chart(fig, use_container_width=True)
