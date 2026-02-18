import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 時合精密解析 (タイドグラフ)")

    if df.empty:
        st.info("データがありません。")
        return

    # --- 1. フィルタリング設定 ---
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()), key="ana_place")
    
    with col_f2:
        all_species = sorted(df[df["場所"] == selected_place]["魚種"].unique())
        initial_targets = ["スズキ", "ヒラスズキ"]
        default_selection = [s for s in initial_targets if s in all_species]
        if not default_selection and all_species:
            default_selection = [all_species[0]]
        selected_species = st.multiselect("🐟 表示する魚種を選択", all_species, default=default_selection, key="ana_species")

    # データの前処理
    df_p = df[df["場所"] == selected_place].copy()
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')
    df_p = df_p.dropna(subset=['datetime'])

    # --- 2. 座標計算ロジック (曲線同期版) ---
    def get_sync_coords(row):
        phase_str = str(row['潮位フェーズ']).strip()
        # 数字を抽出（全角・半角・位置不問）
        nums = re.findall(r'\d+', phase_str.translate(str.maketrans('０１２３４５６７８９', '0123456789')))
        
        # ステップ（分）を抽出。取れない場合は中間の5にする
        step = int(nums[0]) if nums else 5
        
        # 0〜10の範囲にクランプ（安全策）
        step = max(0, min(10, step))
        
        # 時刻を数値化 (0.0 ～ 24.0)
        h = row['datetime'].hour + row['datetime'].minute / 60
        
        # 【重要】y軸（潮位）を「潮位フェーズ」から直接計算
        # 上げ0分 = -100, 上げ10分 = 100 / 下げ0分 = 100, 下げ10分 = -100
        is_up = "上げ" in phase_str
        if is_up:
            y = -100 + (step * 20)
        else:
            y = 100 - (step * 20)
        
        # プロットを曲線に合わせるための疑似x軸計算
        # 0:00〜24:00の実際の時刻をベースにしつつ、
        # グラフの見た目（波）に合わせるため少し補正
        x = h if h >= 4 else h + 24
        
        return pd.Series([x, y])

    if not df_p.empty:
        df_p[['x_sync', 'y_sync']] = df_p.apply(get_sync_coords, axis=1)

    # --- 3. グラフ描画 ---
    fig = go.Figure()
    
    # 背景のガイド曲線 (サインカーブ)
    x_line = np.linspace(0, 28, 1000)
    y_line = 100 * np.sin(2 * np.pi * (x_line - 7) / 12.4) # 位相を調整
    
    fig.add_trace(go.Scatter(
        x=x_line, y=y_line, 
        mode='lines', 
        line=dict(color='rgba(100, 200, 255, 0.15)', width=1, dash='dot'), 
        hoverinfo='skip',
        name='潮位目安'
    ))

    if selected_species:
        for species in selected_species:
            spec_df = df_p[df_p['魚種'] == species]
            if spec_df.empty: continue
            
            # 潮位フェーズに基づいたマーカー設定
            is_up_list = spec_df['潮位フェーズ'].str.contains('上げ')
            symbols = is_up_list.apply(lambda x: 'triangle-up' if x else 'triangle-down')
            colors = is_up_list.apply(lambda x: '#00d4ff' if x else '#ff4b4b')
            
            fig.add_trace(go.Scatter(
                x=spec_df['x_sync'], y=spec_df['y_sync'],
                mode='markers',
                name=species,
                marker=dict(
                    size=16, 
                    symbol=symbols, 
                    color=colors, 
                    line=dict(width=1, color='white'),
                    opacity=0.8
                ),
                text=spec_df['datetime'].dt.strftime('%H:%M') + " / " + spec_df['潮位フェーズ'],
                hovertemplate="<b>%{name}</b><br>%{text}<extra></extra>"
            ))

    fig.update_layout(
        xaxis=dict(
            title="時刻",
            tickvals=[0, 6, 12, 18, 24, 28], 
            ticktext=["0:00", "6:00", "12:00", "18:00", "0:00", "4:00"], 
            range=[0, 28],
            gridcolor='rgba(255,255,255,0.1)'
        ),
        yaxis=dict(
            tickvals=[100, 0, -100], 
            ticktext=["満潮", "中間", "干潮"], 
            range=[-120, 120],
            gridcolor='rgba(255,255,255,0.1)'
        ),
        template="plotly_dark", 
        height=500,
        margin=dict(l=20, r=20, t=40, b=20)
    )

    st.plotly_chart(fig, use_container_width=True)
