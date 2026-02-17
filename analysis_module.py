import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def show_analysis_page(df):
    st.subheader("📊 夜間・深夜中心の時合解析")

    if df.empty:
        st.info("解析するデータがまだありません。")
        return

    place_list = sorted(df["場所"].unique().tolist())
    selected_place = st.selectbox("📍 解析する場所を選択", place_list)
    
    df_place = df[df["場所"] == selected_place].copy()
    df_place['datetime'] = pd.to_datetime(df_place['datetime'])

    # --- 1. 時間軸のシフト (12時開始 〜 翌12時終了) ---
    # 0〜12時を24〜36時として扱い、グラフの中央を24時にする
    def shift_hour(dt):
        h = dt.hour + dt.minute / 60
        return h if h >= 12 else h + 24

    df_place['hour_shifted'] = df_place['datetime'].apply(shift_hour)

    # --- 2. 仮想タイドグラフの作成 (12時〜36時) ---
    x_tide = np.linspace(12, 36, 500)
    # 周期12.4時間。24時（深夜）付近で変化が見えるよう調整
    y_tide = 80 * np.sin(2 * np.pi * (x_tide - 18) / 12.4) 

    fig = go.Figure()

    # 背景の潮位曲線
    fig.add_trace(go.Scatter(
        x=x_tide, y=y_tide,
        mode='lines',
        line=dict(color='rgba(100, 200, 255, 0.3)', width=2),
        name='潮位イメージ'
    ))

    # --- 3. 釣果プロットの計算 ---
    def get_y_pos(phase):
        step = int(''.join(filter(str.isdigit, phase))) if any(c.isdigit() for c in phase) else 5
        if "上げ" in phase: return -80 + (step * 16)
        if "下げ" in phase: return 80 - (step * 16)
        return 0

    df_place['y_pos'] = df_place['潮位フェーズ'].apply(get_y_pos)

    # プロット
    fig.add_trace(go.Scatter(
        x=df_place['hour_shifted'],
        y=df_place['y_pos'],
        mode='markers+text',
        marker=dict(size=14, color='#00ffd0', symbol='diamond', line=dict(width=1, color='white')),
        text=df_place['魚種'] + df_place['全長_cm'].astype(str) + "cm",
        textposition="top center",
        name='釣果'
    ))

    # --- 4. X軸のラベルを読みやすく書き換える ---
    tick_vals = [12, 15, 18, 21, 24, 27, 30, 33, 36]
    tick_text = ["12:00", "15:00", "18:00", "21:00", "深夜0:00", "3:00", "6:00", "9:00", "12:00"]

    fig.update_layout(
        xaxis=dict(
            title="時刻 (深夜0時を中央に表示)",
            tickvals=tick_vals,
            ticktext=tick_text,
            range=[12, 36],
            gridcolor='rgba(255,255,255,0.1)'
        ),
        yaxis=dict(showticklabels=False, range=[-110, 110]),
        height=450,
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    # 24時（深夜0時）に目立つ縦線を引く
    fig.add_vline(x=24, line_width=2, line_dash="dash", line_color="orange")

    st.plotly_chart(fig, use_container_width=True)
