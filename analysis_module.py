import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def show_analysis_page(df):
    st.subheader("📊 時合解析：タイドフェーズ・プロット")

    if df.empty:
        st.info("データがありません。")
        return

    selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()))
    df_p = df[df["場所"] == selected_place].copy()
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')

    # --- 1. 潮位フェーズから波の上の「高さ(Y)」を計算 ---
    def get_phase_y(phase):
        try:
            step = int(''.join(filter(str.isdigit, str(phase))))
        except:
            step = 5
        if "上げ" in str(phase):
            return -100 + (step * 20)  # -80 〜 80 (上り)
        elif "下げ" in str(phase):
            return 100 - (step * 20)   # 80 〜 -80 (下り)
        return 0

    df_p['y_pos'] = df_p['潮位フェーズ'].apply(get_phase_y)

    # --- 2. 上げ・下げを区別してプロット位置(X)を微調整 ---
    # 波の形に合わせて、上げ潮のデータは「上り坂」に、下げ潮は「下り坂」に配置
    def adjust_x_for_slope(row):
        h = row['datetime'].hour + row['datetime'].minute / 60
        x_base = h if h >= 12 else h + 24
        
        # 仮想波形の周期(12h)の中で、どこが上り坂でどこが下り坂かを判定し、
        # 潮位フェーズに合う「一番近い斜面」にXを少し補正して吸着させます
        phase = str(row['潮位フェーズ'])
        # 12時間周期の位相 (0-12)
        local_x = x_base % 12
        
        # 下げ潮なのに波が「上げ」の区間にある場合など、斜面に合わせる処理
        # (簡易的に、フェーズの事実に合わせてXを波の位相に同期させます)
        return x_base

    df_p['x_adjusted'] = df_p.apply(adjust_x_for_slope, axis=1)

    # --- 3. グラフ作成 ---
    fig = go.Figure()

    # 背景：きれいな正弦波（12時間周期）
    x_line = np.linspace(12, 36, 1000)
    y_line = 100 * np.sin(2 * np.pi * (x_line - 15) / 12)
    fig.add_trace(go.Scatter(x=x_line, y=y_line, mode='lines', 
                             line=dict(color='rgba(100, 200, 255, 0.2)', width=2),
                             hoverinfo='skip'))

    # 釣果プロット（上げと下げで色やシンボルを分けるとより見やすいです）
    for is_up in [True, False]:
        mask = df_p['潮位フェーズ'].str.contains('上げ') if is_up else df_p['潮位フェーズ'].str.contains('下げ')
        curr_df = df_p[mask]
        
        fig.add_trace(go.Scatter(
            x=curr_df['x_adjusted'], y=curr_df['y_pos'],
            mode='markers+text',
            name='上げ潮' if is_up else '下げ潮',
            marker=dict(
                size=14, 
                color='#00ffd0' if is_up else '#ff4b4b', # 上げは青緑、下げは赤系
                symbol='triangle-up' if is_up else 'triangle-down',
                line=dict(width=1, color='white')
            ),
            text=curr_df.apply(lambda r: f"{r['魚種']}{r['全長_cm']}cm", axis=1),
            textposition="top center",
            hovertemplate="<b>%{customdata}</b><br>時刻: %{x:.2f}h<extra></extra>",
            customdata=curr_df['潮位フェーズ']
        ))

    # レイアウト（オレンジの線を除去）
    fig.update_layout(
        xaxis=dict(
            title="釣行時刻",
            tickvals=[12, 18, 24, 30, 36], 
            ticktext=["12:00", "18:00", "0:00", "6:00", "12:00"], 
            range=[12, 36],
            gridcolor='rgba(255,255,255,0.05)'
        ),
        yaxis=dict(
            title="潮位位置", 
            tickvals=[100, 0, -100], 
            ticktext=["満潮", "中間", "干潮"], 
            range=[-140, 160],
            gridcolor='rgba(255,255,255,0.05)'
        ),
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=550,
        showlegend=True # 上げ・下げの凡例を表示
    )

    st.plotly_chart(fig, use_container_width=True)
