import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def show_analysis_page(df):
    st.subheader("📊 時合精密解析（24時満潮・昼夜振り分け）")

    if df.empty:
        st.info("データがありません。")
        return

    selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()))
    df_p = df[df["場所"] == selected_place].copy()
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')

    # --- 1. 定数定義 ---
    CYCLE = 12
    PEAK_L = 12.0  # 左側の山の頂点（お昼12時）
    PEAK_C = 24.0  # 中央の山の頂点（深夜0時）
    PEAK_R = 36.0  # 右側の山の頂点（翌お昼12時）

    # --- 2. 座標計算ロジック ---
    def get_sync_coords(row):
        phase = str(row['潮位フェーズ'])
        try:
            step = int(''.join(filter(str.isdigit, phase)))
        except:
            step = 5
        
        # 時刻を12h〜36hのスケールに変換
        h = row['datetime'].hour + row['datetime'].minute / 60
        shifted_h = h if h >= 12 else h + 24
        
        # 【重要】時刻による山の振り分け
        # 18:00〜30:00(翌6:00)の間なら、中央の24時満潮の波に乗せる
        if 18.0 <= shifted_h < 30.0:
            base_peak = PEAK_C
        elif shifted_h < 18.0:
            base_peak = PEAK_L
        else:
            base_peak = PEAK_R

        # 潮位フェーズ(1-9分)からXとYを算出
        # 12時間周期なので、干潮から満潮（または逆）までは3時間。
        # 5分（中間）を基準に前後3時間を9分割して配置
        offset_time = (5 - step) * (3 / 5) 

        if "上げ" in phase:
            sync_x = base_peak - abs(offset_time) if offset_time >= 0 else base_peak - abs(offset_time)
            # より直感的に：上げは満潮の左側
            sync_x = base_peak - ((10 - step) * 0.6)
            y = -100 + (step * 20)
        elif "下げ" in phase:
            # 下げは満潮の右側
            sync_x = base_peak + (step * 0.6)
            y = 100 - (step * 20)
        else:
            sync_x = base_peak
            y = 0
            
        return pd.Series([sync_x, y])

    # 座標計算を実行
    df_p[['x_sync', 'y_sync']] = df_p.apply(get_sync_coords, axis=1)

    # --- 3. グラフ描画 ---
    fig = go.Figure()

    # 背景：24時を満潮の頂点とする波 (12:00 - 36:00)
    x_line = np.linspace(12, 36, 1000)
    y_line = 100 * np.cos(2 * np.pi * (x_line - 24) / 12)
    
    fig.add_trace(go.Scatter(
        x=x_line, y=y_line, mode='lines', 
        line=dict(color='rgba(100, 200, 255, 0.4)', width=3),
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
                line=dict(width=1.5, color='white')
            ),
            text=curr_df.apply(lambda r: f"{r['魚種']}{r['全長_cm']}cm", axis=1),
            textposition="top center",
            customdata=curr_df['潮位フェーズ'],
            hovertemplate="<b>%{customdata}</b><br>判定位置: %{x:.2f}h<extra></extra>"
        ))

    # レイアウト設定
    fig.update_layout(
        xaxis=dict(
            title="釣行時刻判定 (12:00 - 0:00 - 12:00)",
            tickvals=[12, 18, 21, 24, 27, 30, 36], 
            ticktext=["12:00", "18:00", "21:00", "0:00(満潮)", "3:00", "6:00", "12:00"], 
            range=[12, 36],
            gridcolor='rgba(255,255,255,0.05)'
        ),
        yaxis=dict(
            title="潮位位置",
            tickvals=[100, 0, -100], 
            ticktext=["満潮", "中間", "干潮"], 
            range=[-150, 180],
            gridcolor='rgba(255,255,255,0.05)'
        ),
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=650,
        showlegend=False
    )

    # 補助線
    fig.add_hline(y=0, line_width=1, line_color="rgba(255,255,255,0.2)") # 中間線

    st.plotly_chart(fig, use_container_width=True)
