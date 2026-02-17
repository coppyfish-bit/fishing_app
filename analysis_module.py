import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def show_analysis_page(df):
    st.subheader("📊 時合精密解析（24時満潮・フェーズ同期）")

    if df.empty:
        st.info("データがありません。")
        return

    selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()))
    df_p = df[df["場所"] == selected_place].copy()
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')

    # --- 1. 定数定義 ---
    # 24時（深夜0時）を頂点にする設定
    CYCLE = 12
    PEAK_DAY = 12.0    # 昼の満潮：12時
    PEAK_MIDNIGHT = 24.0 # 夜の満潮：24時
    PEAK_MORNING = 36.0  # 翌朝の満潮：36時（翌12時）

    # --- 2. 座標計算ロジック ---
    def get_sync_coords(row):
        phase = str(row['潮位フェーズ'])
        try:
            step = int(''.join(filter(str.isdigit, phase)))
        except:
            step = 5
        
        # 写真の時刻を 12h〜36h の範囲にシフト
        h = row['datetime'].hour + row['datetime'].minute / 60
        shifted_h = h if h >= 12 else h + 24
        
        # 時刻を参照して、どの満潮(Peak)に近い波に乗せるか判定
        # 12-18hなら12時の波、18-30hなら24時の波、30-36hなら36時の波
        if shifted_h < 18:
            base_peak = PEAK_DAY
        elif shifted_h < 30:
            base_peak = PEAK_MIDNIGHT
        else:
            base_peak = PEAK_MORNING

        # 潮位フェーズ(1-9分)を、満潮(peak)を起点に左右に配置
        # 上げ潮は満潮の左側（上り）、下げ潮は満潮の右側（下り）
        if "上げ" in phase:
            sync_x = base_peak - ((10 - step) * 0.6)
            y = -100 + (step * 20)
        elif "下げ" in phase:
            sync_x = base_peak + (step * 0.6)
            y = 100 - (step * 20)
        else:
            sync_x = base_peak
            y = 0
            
        return pd.Series([sync_x, y])

    # 計算実行
    df_p[['x_sync', 'y_sync']] = df_p.apply(get_sync_coords, axis=1)

    # --- 3. グラフ描画 ---
    fig = go.Figure()

    # 背景：24時を満潮の頂点にする正弦波
    x_line = np.linspace(12, 36, 1000)
    # 24時で頂点にするため、(x - 24)を使用
    y_line = 100 * np.cos(2 * np.pi * (x_line - 24) / 12)
    
    fig.add_trace(go.Scatter(
        x=x_line, y=y_line, mode='lines', 
        line=dict(color='rgba(100, 200, 255, 0.3)', width=2),
        hoverinfo='skip'
    ))

    # 釣果プロット
    for p_type in ['上げ', '下げ']:
        mask = df_p['潮位フェーズ'].str.contains(p_type)
        curr_df = df_p[mask]
        
        fig.add_trace(go.Scatter(
            x=curr_df['x_sync'], y=curr_df['y_sync'],
            mode='markers+text',
            name=f'{p_type}潮',
            marker=dict(
                size=16, 
                color='#00ffd0' if p_type == '上げ' else '#ff4b4b',
                symbol='triangle-up' if p_type == '上げ' else 'triangle-down',
                line=dict(width=1, color='white')
            ),
            text=curr_df.apply(lambda r: f"{r['魚種']}{r['全長_cm']}cm", axis=1),
            textposition="top center",
            customdata=curr_df['潮位フェーズ'],
            hovertemplate="<b>%{customdata}</b><br>判定位置: %{x:.2f}h<extra></extra>"
        ))

    # レイアウト
    fig.update_layout(
        xaxis=dict(
            title="時刻判定 (24:00 満潮ベース)",
            tickvals=[12, 18, 24, 30, 36], 
            ticktext=["12:00", "18:00", "0:00(満潮)", "6:00", "12:00"], 
            range=[12, 36]
        ),
        yaxis=dict(
            title="潮位フェーズ",
            tickvals=[100, 0, -100], 
            ticktext=["満潮", "中間", "干潮"], 
            range=[-150, 180]
        ),
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=600,
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)
