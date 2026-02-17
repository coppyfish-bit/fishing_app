import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def show_analysis_page(df):
    st.subheader("📊 時合精密解析（曲線吸着プロット）")

    if df.empty:
        st.info("データがありません。")
        return

    selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()))
    df_p = df[df["場所"] == selected_place].copy()
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')

    # --- 1. 定数定義 ---
    # 周期12時間。15時と27時(深夜3時)を「満潮(山の頂点)」に設定
    CYCLE = 12
    PEAK_1 = 15.0 # 第1サイクルの満潮時刻
    PEAK_2 = 27.0 # 第2サイクルの満潮時刻

    # --- 2. 潮位フェーズから波の上の座標(X, Y)を計算 ---
    def get_sync_coords(row):
        phase = str(row['潮位フェーズ'])
        try:
            # 「上げ7分」などの数字を取得
            step = int(''.join(filter(str.isdigit, phase)))
        except:
            step = 5
        
        # 釣行時刻から、第1サイクル(12-24h)か第2サイクル(24-36h)かを決定
        h = row['datetime'].hour + row['datetime'].minute / 60
        shifted_h = h if h >= 12 else h + 24
        base_peak = PEAK_1 if shifted_h < 24 else PEAK_2

        # 正弦波の山(満潮)を基準(0)として、何時間前後するかを計算
        # 12時間周期なので、干潮から満潮までは3時間、満潮から干潮までも3時間
        # フェーズ1〜9を、満潮から前後3時間の範囲にマッピング
        time_offset = (5 - step) * (3 / 5) # 5分を中心に前後させる

        if "上げ" in phase:
            # 上げ潮は「満潮の前」
            sync_x = base_peak - time_offset if time_offset > 0 else base_peak - abs(time_offset)
            # 上げ潮は常に満潮時刻より前(左側)に配置
            sync_x = base_peak - ( (10 - step) * 0.6 )
            y = -100 + (step * 20)
        else:
            # 下げ潮は「満潮の後(右側)」に配置
            sync_x = base_peak + ( step * 0.6 )
            y = 100 - (step * 20)
            
        return pd.Series([sync_x, y])

    # 全データを曲線上の位置に強制移動
    df_p[['x_sync', 'y_sync']] = df_p.apply(get_sync_coords, axis=1)

    # --- 3. グラフ描画 ---
    fig = go.Figure()

    # 背景：タイド曲線（15時と27時を頂点にする）
    x_line = np.linspace(12, 36, 1000)
    y_line = 100 * np.cos(2 * np.pi * (x_line - 15) / 12) # cosを使うと15時が頂点になる
    fig.add_trace(go.Scatter(x=x_line, y=y_line, mode='lines', 
                             line=dict(color='rgba(100, 200, 255, 0.3)', width=2),
                             hoverinfo='skip'))

    # 釣果プロット
    for p_type in ['上げ', '下げ']:
        curr_df = df_p[df_p['潮位フェーズ'].str.contains(p_type)]
        
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
            hovertemplate="<b>%{customdata}</b><br>本来の時刻: %{text}<extra></extra>"
        ))

    # レイアウト
    fig.update_layout(
        xaxis=dict(tickvals=[12, 18, 24, 30, 36], 
                   ticktext=["12:00", "18:00", "0:00", "6:00", "12:00"], range=[12, 36]),
        yaxis=dict(tickvals=[100, 0, -100], ticktext=["満潮", "中間", "干潮"], range=[-150, 180]),
        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        height=600, showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)
