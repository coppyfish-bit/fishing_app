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
    # 深夜24:00を頂点（山）とする設定
    CYCLE = 12
    CENTER_PEAK = 24.0

    # --- 2. 座標計算ロジック（上げ・下げを区別して波に吸着） ---
    def get_sync_coords(row):
        phase = str(row['潮位フェーズ'])
        try:
            step = int(''.join(filter(str.isdigit, phase)))
        except:
            step = 5
        
        # 釣行時刻を 12h〜36h スケールに変換
        h = row['datetime'].hour + row['datetime'].minute / 60
        shifted_h = h if h >= 12 else h + 24

        # Y軸の高さ計算（-100〜100）
        if "上げ" in phase:
            y = -100 + (step * 20)
            # 上げ潮は山の「左側」に配置。頂点（24時）から最大3時間前まで。
            # sin波の性質を利用してXを逆算： y = 100 * cos( (x-24)*2π/12 )
            # 簡略化してフェーズで横位置を決定
            sync_x = CENTER_PEAK - ((10 - step) * 0.6)
        elif "下げ" in phase:
            y = 100 - (step * 20)
            # 下げ潮は山の「右側」に配置。頂点（24時）から最大3時間後まで。
            sync_x = CENTER_PEAK + (step * 0.6)
        else:
            y = 0
            sync_x = shifted_h # 判定不能時は時刻に従う

        # 18時より前、または30時(朝6時)以降のデータは別の山へシフト
        if shifted_h < 18.0:
            sync_x -= 12.0
        elif shifted_h >= 30.0:
            sync_x += 12.0
            
        return pd.Series([sync_x, y])

    # 座標計算を一括適用
    df_p[['x_sync', 'y_sync']] = df_p.apply(get_sync_coords, axis=1)

    # --- 3. グラフ描画 ---
    fig = go.Figure()

    # 背景：24時を満潮の頂点とする曲線
    x_line = np.linspace(12, 36, 1000)
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
                marker=dict(size=16, color=color, symbol=symbol, line=dict(width=1, color='white')),
                text=curr_df.apply(lambda r: f"{r['魚種']}{r['全長_cm']}cm", axis=1),
                textposition="top center",
                customdata=curr_df['潮位フェーズ'],
                hovertemplate="<b>%{customdata}</b><br>判定位置: %{x:.2f}h<extra></extra>"
            ))

    # レイアウト設定
    fig.update_layout(
        xaxis=dict(
            tickvals=[12, 18, 21, 24, 27, 30, 36], 
            ticktext=["12:00", "18:00", "21:00", "0:00(満潮)", "3:00", "6:00", "12:00"], 
            range=[12, 36]
        ),
        yaxis=dict(
            tickvals=[100, 0, -100], 
            ticktext=["満潮", "中間", "干潮"], 
            range=[-150, 180]
        ),
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=650,
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)
