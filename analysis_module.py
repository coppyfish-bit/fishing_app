import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def show_analysis_page(df):
    st.subheader("📊 24h時合・フェーズ精密解析")

    if df.empty:
        st.info("解析するデータがまだありません。")
        return

    place_list = sorted(df["場所"].unique().tolist())
    selected_place = st.selectbox("📍 解析する場所を選択", place_list)
    
    df_place = df[df["場所"] == selected_place].copy()
    df_place['datetime'] = pd.to_datetime(df_place['datetime'], errors='coerce')

    # --- 1. 時間軸（X軸）の計算 (12:00開始 〜 深夜0:00通過 〜 翌12:00) ---
    def get_shifted_hour(dt):
        h = dt.hour + dt.minute / 60
        return h if h >= 12 else h + 24
    df_place['x_time'] = df_place['datetime'].apply(get_shifted_hour)

    # --- 2. 潮位フェーズから波の上の正確なY位置を計算 ---
    def get_y_from_phase_only(phase):
        try:
            # 「上げ3分」などの数字を取得
            step = int(''.join(filter(str.isdigit, str(phase))))
        except:
            step = 5
            
        # 満潮を100, 干潮を-100として10分割マッピング
        if "上げ" in str(phase):
            # 干潮(-100)から満潮(100)へ向かうスロープ
            return -100 + (step * 20)
        elif "下げ" in str(phase):
            # 満潮(100)から干潮(-100)へ向かうスロープ
            return 100 - (step * 20)
        return 0

    df_place['y_pos'] = df_place['潮位フェーズ'].apply(get_y_from_phase_only)

    # --- 3. グラフ描画 ---
    x_line = np.linspace(12, 36, 500)
    # 背景の波形（12時間周期の正弦波）
    y_line = 100 * np.sin(2 * np.pi * (x_line - 15) / 12)

    fig = go.Figure()

    # 背景：潮汐イメージ曲線
    fig.add_trace(go.Scatter(
        x=x_line, y=y_line,
        mode='lines',
        line=dict(color='rgba(100, 200, 255, 0.2)', width=2),
        hoverinfo='skip'
    ))

    # メイン：釣果プロット
    # 時刻(X)は位置決めのみ、高さ(Y)はフェーズで固定
    fig.add_trace(go.Scatter(
        x=df_place['x_time'],
        y=df_place['y_pos'],
        mode='markers+text',
        marker=dict(
            size=16,
            color='#00ffd0',
            symbol='diamond',
            line=dict(width=1, color='white'),
            opacity=0.9
        ),
        text=df_place.apply(lambda r: f"{r['魚種']}<br>{r['全長_cm']}cm", axis=1),
        textposition="top center",
        customdata=df_place['潮位フェーズ'],
        hovertemplate="<b>%{customdata}</b><br>釣行時刻: %{x:.2f}h<br>%{text}<extra></extra>"
    ))

    # --- 4. レイアウト調整 ---
    tick_vals = [12, 18, 24, 30, 36]
    tick_text = ["12:00", "18:00", "深夜 0:00", "6:00", "12:00"]

    fig.update_layout(
        xaxis=dict(
            title="釣行時刻",
            tickvals=tick_vals, ticktext=tick_text,
            range=[12, 36], gridcolor='rgba(255,255,255,0.05)'
        ),
        yaxis=dict(
            title="潮位フェーズ位置",
            tickvals=[100, 0, -100],
            ticktext=["満潮", "中間", "干潮"],
            range=[-130, 150], gridcolor='rgba(255,255,255,0.1)'
        ),
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=550,
        showlegend=False
    )

    # 深夜0時を強調
    fig.add_vline(x=24, line_width=2, line_color="orange", line_dash="dash")
    
    # 満潮・干潮のライン
    fig.add_hline(y=100, line_width=0.5, line_dash="dot", line_color="white")
    fig.add_hline(y=-100, line_width=0.5, line_dash="dot", line_color="white")

    st.plotly_chart(fig, use_container_width=True)
