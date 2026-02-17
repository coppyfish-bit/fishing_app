import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def show_analysis_page(df):
    st.subheader("📊 時合精密解析（24時満潮・フェーズ完全同期）")

    if df.empty:
        st.info("データがありません。")
        return

    selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()))
    df_p = df[df["場所"] == selected_place].copy()
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')

    # --- 1. 定数定義 ---
    CYCLE = 12
    CENTER_PEAK = 24.0  # 深夜0時を頂点とする

    # --- 2. 座標計算ロジック（時刻でエリアを決め、フェーズで座標を固定） ---
    def get_sync_coords(row):
        phase_str = str(row['潮位フェーズ'])
        # 数字を抽出（全角・半角両対応）
        import re
        nums = re.findall(r'\d+', phase_str.translate(str.maketrans('０１２３４５６７８９', '0123456789')))
        step = int(nums[0]) if nums else 5
        
        # 時刻を12h〜36hスケールに変換
        h = row['datetime'].hour + row['datetime'].minute / 60
        shifted_h = h if h >= 12 else h + 24

        # 【エリア判定】どの山（Peak）に乗せるかだけを時刻で決める
        # 18:00〜30:00(翌6:00)の間なら、中央の24時満潮の山
        if 18.0 <= shifted_h < 30.0:
            target_peak = 24.0
        elif shifted_h < 18.0:
            target_peak = 12.0
        else:
            target_peak = 36.0

        # 【座標決定】上げ・下げのフェーズ情報から、target_peakに対する相対位置を決める
        # 潮位フェーズ1〜9分を、満潮(Peak)から前後3時間の範囲に均等配置
        # 上げ潮(上り坂)はPeakの左側、下げ潮(下り坂)はPeakの右側
        if "上げ" in phase_str:
            # 上げ1分 = Peakの3時間前 / 上げ9分 = Peakの0.6時間前
            # 頂点に近いほどstepが大きい(上げ7分 > 上げ3分)
            x_offset = - (10 - step) * 0.6 
            y = -100 + (step * 20)
        elif "下げ" in phase_str:
            # 下げ1分 = Peakの0.6時間後 / 下げ9分 = Peakの3時間後
            # 頂点に近いほどstepが小さい(下げ3分 < 下げ7分)
            x_offset = step * 0.6
            y = 100 - (step * 20)
        else:
            x_offset = 0
            y = 0

        return pd.Series([target_peak + x_offset, y])

    # 座標計算を実行
    df_p[['x_sync', 'y_sync']] = df_p.apply(get_sync_coords, axis=1)

    # --- 3. グラフ描画 ---
    fig = go.Figure()

    # 背景：24時を満潮の頂点とする一定のサインカーブ
    x_line = np.linspace(12, 36, 1000)
    y_line = 100 * np.cos(2 * np.pi * (x_line - 24) / 12)
    fig.add_trace(go.Scatter(x=x_line, y=y_line, mode='lines', 
                             line=dict(color='rgba(100, 200, 255, 0.4)', width=3),
                             hoverinfo='skip'))

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
                marker=dict(size=18, color=color, symbol=symbol, line=dict(width=1.5, color='white')),
                text=curr_df.apply(lambda r: f"{r['魚種']}{r['全長_cm']}cm", axis=1),
                textposition="top center",
                customdata=curr_df['潮位フェーズ'],
                hovertemplate="<b>%{customdata}</b><br>時刻判定エリア: %{x:.2f}h<extra></extra>"
            ))

    # レイアウト
    fig.update_layout(
        xaxis=dict(
            tickvals=[12, 18, 21, 24, 27, 30, 36], 
            ticktext=["12:00", "18:00", "21:00", "0:00(満潮)", "3:00", "6:00", "12:00"], 
            range=[12, 36]
        ),
        yaxis=dict(
            tickvals=[100, 0, -100], 
            ticktext=["満潮", "中間", "干潮"], 
            range=[-150, 200]
        ),
        template="plotly_dark",
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=650,
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)
