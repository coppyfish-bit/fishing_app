import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def show_analysis_page(df):
    st.subheader("📊 24hタイド・フェーズ解析")

    if df.empty:
        st.info("解析するデータがまだありません。")
        return

    place_list = sorted(df["場所"].unique().tolist())
    selected_place = st.selectbox("📍 解析する場所を選択", place_list)
    
    df_place = df[df["場所"] == selected_place].copy()
    df_place['datetime'] = pd.to_datetime(df_place['datetime'])

    # --- 1. 時間軸（X軸）の計算 (12:00開始 〜 翌12:00終了) ---
    def get_shifted_hour(dt):
        h = dt.hour + dt.minute / 60
        return h if h >= 12 else h + 24

    df_place['x_time'] = df_place['datetime'].apply(get_shifted_hour)

    # --- 2. 潮位フェーズから高さ（Y軸）を計算 ---
    # 頂点=100(満潮), 底=-100(干潮)
    def calculate_y_from_phase(phase):
        try:
            step = int(''.join(filter(str.isdigit, phase)))
        except:
            step = 5
            
        if "上げ" in phase:
            # 上げ1分(-80) 〜 上げ9分(80)
            return -100 + (step * 20)
        elif "下げ" in phase:
            # 下げ1分(80) 〜 下げ9分(-80)
            return 100 - (step * 20)
        return 0

    df_place['y_pos'] = df_place['潮位フェーズ'].apply(calculate_y_from_phase)

    # --- 3. グラフ描画 ---
    # 12時から翌12時までの24時間分
    x_line = np.linspace(12, 36, 500)
    
    # 24時間でちょうど2サイクル（12時間周期）のサインカーブを作成
    # 18時付近と6時付近を山（満潮）に見立てた仮想カーブ
    y_line = 100 * np.sin(2 * np.pi * (x_line - 15) / 12)

    fig = go.Figure()

    # 背景のベース波形
    fig.add_trace(go.Scatter(
        x=x_line, y=y_line,
        mode='lines',
        line=dict(color='rgba(100, 200, 255, 0.25)', width=2),
        hoverinfo='skip',
        name='潮汐リズム'
    ))

    # 釣果ポイント
    fig.add_trace(go.Scatter(
        x=df_place['x_time'],
        y=df_place['y_pos'],
        mode='markers',
        marker=dict(
            size=16,
            color='#00ffd0',
            symbol='diamond',
            line=dict(width=1, color='white'),
            opacity=0.8
        ),
        text=df_place.apply(lambda r: f"{r['魚種']} {r['全長_cm']}cm<br>{r['潮位フェーズ']}", axis=1),
        hovertemplate="%{text}<br>時刻: %{x:.2f}h<extra></extra>"
    ))

    # レイアウト
    tick_vals = [12, 18, 24, 30, 36]
    tick_text = ["12:00", "18:00", "深夜 0:00", "6:00", "12:00"]

    fig.update_layout(
        xaxis=dict(
            title="釣行時刻",
            tickvals=tick_vals, ticktext=tick_text,
            range=[12, 36], gridcolor='rgba(255,255,255,0.1)'
        ),
        yaxis=dict(
            title="潮位フェーズ (干潮 ↔ 満潮)",
            tickvals=[100, 0, -100],
            ticktext=["満潮", "中間", "干潮"],
            range=[-120, 120], gridcolor='rgba(255,255,255,0.1)'
        ),
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=500,
        showlegend=False
    )

    # 深夜0時ライン
    fig.add_vline(x=24, line_width=2, line_color="orange", line_dash="dash")

    st.plotly_chart(fig, use_container_width=True)
