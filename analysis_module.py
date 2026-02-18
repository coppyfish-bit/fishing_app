import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 タイドサイクル別・時合解析")

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

    # --- 2. 座標計算ロジック (タイドサイクル集約版) ---
    def get_sync_coords(row):
        phase_str = str(row['潮位フェーズ']).strip()
        nums = re.findall(r'\d+', phase_str.translate(str.maketrans('０１２３４５６７８９', '0123456789')))
        step = int(nums[0]) if nums else 5
        step = max(0, min(10, step))
        
        h = row['datetime'].hour
        is_up = "上げ" in phase_str

        # Y軸: 潮位フェーズから高さを決定
        y = -100 + (step * 20) if is_up else 100 - (step * 20)

        # X軸: 指定された時間帯でエリアを分ける
        # サイクル内での位置(0〜12)を計算
        # 下げ5分(x=0) → 干潮(x=3) → 上げ5分(x=6) → 満潮(x=9) → 下げ5分(x=12)
        if not is_up:
            # 下げフェーズ: 満潮(0)から干潮(6)へ
            pos = step * 0.6 if step >= 0 else 0
        else:
            # 上げフェーズ: 干潮(6)から満潮(12)へ
            pos = 6 + (step * 0.6)

        # 4時〜19時は左側(base=0)、それ以外は右側(base=15)にプロット
        base_x = 0 if 4 <= h <= 19 else 15
        x = base_x + pos
        
        return pd.Series([x, y])

    if not df_p.empty:
        df_p[['x_sync', 'y_sync']] = df_p.apply(get_sync_coords, axis=1)

    # --- 3. グラフ描画 ---
    fig = go.Figure()
    
    # 背景の波形 (2つのサイクルを描画)
    x_line = np.linspace(0, 27, 1000)
    # 周期12のサインカーブ。x=0, 12, 15, 27 が「下げ5分(中間)」になるよう調整
    y_line = 100 * np.sin(2 * np.pi * (x_line - 9) / 12)
    
    fig.add_trace(go.Scatter(
        x=x_line, y=y_line, 
        mode='lines', 
        line=dict(color='rgba(100, 200, 255, 0.2)', width=1), 
        hoverinfo='skip'
    ))

    if selected_species:
        for species in selected_species:
            spec_df = df_p[df_p['魚種'] == species]
            if spec_df.empty: continue
            
            is_up_list = spec_df['潮位フェーズ'].str.contains('上げ')
            symbols = is_up_list.apply(lambda x: 'triangle-up' if x else 'triangle-down')
            colors = is_up_list.apply(lambda x: '#00d4ff' if x else '#ff4b4b')
            
            fig.add_trace(go.Scatter(
                x=spec_df['x_sync'], y=spec_df['y_sync'],
                mode='markers',
                name=species,
                marker=dict(size=16, symbol=symbols, color=colors, line=dict(width=1, color='white')),
                text=spec_df['datetime'].dt.strftime('%H:%M') + " (" + spec_df['潮位フェーズ'] + ")",
                hovertemplate="<b>%{name}</b><br>%{text}<extra></extra>"
            ))

    # レイアウト設定
    fig.update_layout(
        xaxis=dict(
            title="タイドサイクル (左:4-19時 / 右:夜間)",
            tickvals=[0, 3, 6, 9, 12, 15, 18, 21, 24, 27],
            ticktext=["下げ5分", "干潮", "上げ5分", "満潮", "下げ5分", "下げ5分", "干潮", "上げ5分", "満潮", "下げ5分"],
            range=[-1, 28],
            gridcolor='rgba(255,255,255,0.05)'
        ),
        yaxis=dict(
            tickvals=[100, 0, -100], 
            ticktext=["満潮", "中間", "干潮"], 
            range=[-130, 130]
        ),
        template="plotly_dark", height=500
    )

    st.plotly_chart(fig, use_container_width=True)
