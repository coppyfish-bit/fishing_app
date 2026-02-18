import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 潮位フェーズ完全同期解析（修正版）")

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

    # --- 2. 座標計算ロジック (位相を修正) ---
    def get_sync_coords(row):
        phase_str = str(row['潮位フェーズ']).strip()
        nums = re.findall(r'\d+', phase_str.translate(str.maketrans('０１２３４５６７８９', '0123456789')))
        step = int(nums[0]) if nums else 5
        step = max(0, min(10, step))
        is_up = "下げ" not in phase_str
        
        # 背景曲線の y = 100 * sin(2*pi*(x-3)/12) に合わせる
        # この式では: x=3(満潮), x=6(下げ中間), x=9(干潮), x=12(上げ中間), x=15(満潮)
        
        if not is_up:
            # 下げフェーズ: 満潮(x=3)から干潮(x=9)へ
            x_val = 3 + (step * 0.6)
        else:
            # 上げフェーズ: 干潮(x=9)から満潮(x=15)へ
            x_val = 9 + (step * 0.6)

        # 4時-19時は左(昼)、それ以外は右(夜)へスライド
        h = row['datetime'].hour
        offset = 0 if 4 <= h <= 19 else 15
        final_x = x_val + offset
        
        # 修正されたサインカーブの式
        final_y = 100 * np.sin(2 * np.pi * (final_x - 12) / 12)
        
        return pd.Series([final_x, final_y])

    if not df_p.empty:
        df_p[['x_sync', 'y_sync']] = df_p.apply(get_sync_coords, axis=1)

    # --- 3. グラフ描画 ---
    fig = go.Figure()
    
    # 背景の面グラフ
    x_line = np.linspace(0, 30, 1000)
    # y=0で上げ開始、y=100で満潮、y=0で下げ開始、y=-100で干潮となる位相
    y_line = 100 * np.sin(2 * np.pi * (x_line - 12) / 12)
    
    fig.add_trace(go.Scatter(
        x=x_line, y=y_line, 
        mode='lines', 
        line=dict(color='#00d4ff', width=3),
        fill='tozeroy', 
        fillcolor='rgba(0, 212, 255, 0.2)',
        hoverinfo='skip'
    ))

    # 昼夜の境界線
    fig.add_vline(x=15.0, line_width=2, line_dash="solid", line_color="rgba(255,255,255,0.5)")

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
                text=spec_df['datetime'].dt.strftime('%m/%d %H:%M') + "<br>" + spec_df['潮位フェーズ'],
                hovertemplate="<b>%{name}</b><br>%{text}<extra></extra>"
            ))

    fig.update_layout(
        xaxis=dict(
            tickvals=[7.5, 22.5],
            ticktext=["☀️ 昼 エリア", "🌙 夜 エリア"],
            range=[1, 29],
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
