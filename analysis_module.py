import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def show_analysis_page(df):
    st.subheader("📊 時合精密解析（フェーズ同期プロット）")

    if df.empty:
        st.info("データがありません。")
        return

    selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()))
    df_p = df[df["場所"] == selected_place].copy()
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')

    # --- 1. 定数定義 ---
    # 12:00を起点(12.0)として、12時間周期の波を2サイクル描く
    # 満潮(頂点)が 15:00, 27:00(3:00) に来るように設定
    CYCLE = 12
    OFFSET = 15 

    # --- 2. 潮位フェーズから「波の上の位置」を計算 ---
    def calculate_phase_coords(row):
        try:
            step = int(''.join(filter(str.isdigit, str(row['潮位フェーズ']))))
        except:
            step = 5
        
        # Y座標 (干潮 -100 〜 満潮 100)
        if "上げ" in str(row['潮位フェーズ']):
            y = -100 + (step * 20)
            # 上げ潮（上り坂）の位相を計算
            # 正弦波において y = sin(theta) がこの値になる角度を探す
            theta = np.arcsin(y / 100) 
            is_up_slope = True
        else: # 下げ
            y = 100 - (step * 20)
            theta = np.arcsin(y / 100)
            is_up_slope = False

        # 本来の釣行時刻が12:00〜24:00の間か、0:00〜12:00の間かを判定
        h = row['datetime'].hour + row['datetime'].minute / 60
        shifted_h = h if h >= 12 else h + 24
        
        # 波のサイクル（12時間）のどこにいるか
        cycle_idx = 0 if shifted_h < 24 else 1
        
        # 位相角度からX座標を逆算
        # sin波の1周期(2π)の中で、上げは -π/2〜π/2、下げは π/2〜3π/2
        if is_up_slope:
            base_x = (theta * CYCLE) / (2 * np.pi) + OFFSET
        else:
            # 下げは山の反対側なので位相を調整
            base_x = ((np.pi - theta) * CYCLE) / (2 * np.pi) + OFFSET
            
        return pd.Series([base_x + (cycle_idx * CYCLE), y])

    # XとYをフェーズに完全同期させる
    df_p[['x_sync', 'y_sync']] = df_p.apply(calculate_phase_coords, axis=1)

    # --- 3. グラフ描画 ---
    fig = go.Figure()

    # 背景：タイド曲線
    x_line = np.linspace(12, 36, 1000)
    y_line = 100 * np.sin(2 * np.pi * (x_line - OFFSET) / CYCLE)
    fig.add_trace(go.Scatter(x=x_line, y=y_line, mode='lines', 
                             line=dict(color='rgba(100, 200, 255, 0.3)', width=2),
                             hoverinfo='skip'))

    # 釣果プロット
    for phase_type in ['上げ潮', '下げ潮']:
        mask = df_p['潮位フェーズ'].str.contains(phase_type[:2])
        curr_df = df_p[mask]
        
        fig.add_trace(go.Scatter(
            x=curr_df['x_sync'], y=curr_df['y_sync'],
            mode='markers+text',
            name=phase_type,
            marker=dict(
                size=15, 
                color='#00ffd0' if '上げ' in phase_type else '#ff4b4b',
                symbol='triangle-up' if '上げ' in phase_type else 'triangle-down',
                line=dict(width=1, color='white')
            ),
            text=curr_df.apply(lambda r: f"{r['魚種']}{r['全長_cm']}cm", axis=1),
            textposition="top center",
            customdata=curr_df['潮位フェーズ'],
            hovertemplate="<b>%{customdata}</b><br>本来の時刻: %{text}<extra></extra>"
        ))

    # レイアウト
    fig.update_layout(
        xaxis=dict(tickvals=[12, 18, 24, 30, 36], 
                   ticktext=["12:00", "18:00", "0:00", "6:00", "12:00"], range=[12, 36]),
        yaxis=dict(tickvals=[100, 0, -100], ticktext=["満潮", "中間", "干潮"], range=[-140, 160]),
        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        height=550, showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)
