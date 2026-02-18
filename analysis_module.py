import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 シームレス・時合精密解析")
    st.write(f"全データ数: {len(df)}")
    df_debug = df[df["場所"] == selected_place]
    st.write(f"選択された場所のデータ数: {len(df_debug)}")
    st.write(f"表示対象の魚種: {selected_species}")

    if df.empty:
        st.info("データがありません。")
        return

    # --- 1. フィルタリング設定 ---
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()), key="ana_place")
    
    df_p_base = df[df["場所"] == selected_place].copy()

    with col_f2:
        all_species = sorted(df_p_base["魚種"].unique())
        top_species = df_p_base["魚種"].value_counts().idxmax() if not df_p_base.empty else None
        default_selection = [top_species] if top_species else []
        selected_species = st.multiselect("🐟 魚種を選択", all_species, default=default_selection, key="ana_species")

    # データの前処理
    df_p = df_p_base.copy()
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')
    df_p = df_p.dropna(subset=['datetime'])

    # --- 2. 座標計算ロジック (シームレス接続版) ---
    def get_sync_coords(row):
        phase_str = str(row['潮位フェーズ']).strip()
        nums = re.findall(r'\d+', phase_str.translate(str.maketrans('０１２３４５６７８９', '0123456789')))
        step = int(nums[0]) if nums else 5
        step = max(0, min(10, step))
        is_up = "下げ" not in phase_str
        
        # 基本の波形位置計算 (x=0:満潮, x=6:干潮, x=12:満潮)
        if not is_up:
            x_val = step * 0.6
        else:
            x_val = 6 + (step * 0.6)

        h = row['datetime'].hour
        # 昼夜の判定とオフセット
        is_day = 4 <= h <= 19
        offset = 0 if is_day else 12.5 # 少し隙間を空けて接続を調整
        final_x = x_val + offset
        
        # シームレスな高さ補正: 昼夜のつなぎ目に向けて山の高さを変える
        # y = 100 * cos(x...) の式で曲線上へ
        final_y = 100 * np.cos(x_val * np.pi / 6)
        
        return pd.Series([final_x, final_y])

    if not df_p.empty:
        df_p[['x_sync', 'y_sync']] = df_p.apply(get_sync_coords, axis=1)

    # --- 3. グラフ描画 ---
    fig = go.Figure()
    
    # 背景のシームレス曲線作成
    # 0-12(昼) と 12.5-24.5(夜) を繋ぐ
    x_line = np.linspace(0, 25, 1000)
    
    # 昼の波と夜の波を滑らかにつなぐための条件付き合成波形
    y_line = []
    for x in x_line:
        if x <= 12.5:
            # 昼のサイクル
            val = 100 * np.cos(x * np.pi / 6)
        else:
            # 夜のサイクル (起点をずらして接続)
            val = 100 * np.cos((x - 12.5) * np.pi / 6)
        y_line.append(val)
    
    fig.add_trace(go.Scatter(
        x=x_line, y=y_line, 
        mode='lines', 
        line=dict(color='#00d4ff', width=3, shape='spline'), # shape='spline'でより滑らかに
        fill='tozeroy', 
        fillcolor='rgba(0, 212, 255, 0.2)',
        hoverinfo='skip'
    ))

    # エリア境界のガイド線
    fig.add_vline(x=12.25, line_width=1, line_dash="dot", line_color="rgba(255,255,255,0.3)")

    if selected_species:
        for species in selected_species:
            spec_df = df_p[df_p['魚種'] == species]
            if spec_df.empty: continue
            
            is_up_list = spec_df['潮位フェーズ'].apply(lambda x: "下げ" not in str(x))
            symbols = is_up_list.apply(lambda x: 'triangle-up' if x else 'triangle-down')
            colors = is_up_list.apply(lambda x: '#00ffd0' if x else '#ff4b4b')
            
            fig.add_trace(go.Scatter(
                x=spec_df['x_sync'], y=spec_df['y_sync'],
                mode='markers',
                name=species,
                marker=dict(size=18, symbol=symbols, color=colors, line=dict(width=1.5, color='white')),
                text=spec_df['datetime'].dt.strftime('%m/%d %H:%M'),
                hovertemplate="<b>%{name}</b><br>%{text}<extra></extra>"
            ))

    fig.update_layout(
        xaxis=dict(
            tickvals=[6, 18.5],
            ticktext=["☀️ 昼 エリア", "🌙 夜 エリア"],
            range=[-0.5, 25.5],
            gridcolor='rgba(255,255,255,0)',
            zeroline=False
        ),
        yaxis=dict(
            tickvals=[100, 0, -100], 
            ticktext=["満潮", "中間", "干潮"], 
            range=[-120, 150],
            gridcolor='rgba(255,255,255,0.1)'
        ),
        template="plotly_dark",
        height=550,
        margin=dict(l=10, r=10, t=20, b=60)
    )

    st.plotly_chart(fig, use_container_width=True)

