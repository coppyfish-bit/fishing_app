import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 エリア別・時合解析 (曲線完全同期版)")

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
        if not df_p_base.empty:
            top_species = df_p_base["魚種"].value_counts().idxmax()
            default_selection = [top_species]
        else:
            default_selection = []
        
        selected_species = st.multiselect("🐟 魚種を選択", all_species, default=default_selection, key="ana_species")

    # データの前処理
    df_p = df_p_base.copy()
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')
    df_p = df_p.dropna(subset=['datetime'])

    # --- 2. 座標計算ロジック (曲線完全同期モード) ---
    def get_sync_coords(row):
        phase_str = str(row['潮位フェーズ']).strip()
        nums = re.findall(r'\d+', phase_str.translate(str.maketrans('０１２３４５６７８９', '0123456789')))
        step = int(nums[0]) if nums else 5
        step = max(0, min(10, step))
        is_up = "下げ" not in phase_str
        
        # Y軸: フェーズから計算 (満潮100, 干潮-100)
        y = -100 + (step * 20) if is_up else 100 - (step * 20)

        # X軸: 曲線のサインカーブ（周期12）に合わせてxを逆算する
        # 下げ: 満潮(x=3)から干潮(x=9)へ
        # 上げ: 干潮(x=9)から満潮(x=15)へ
        # ※背景曲線の y = 100 * sin(2*pi*(x-9)/12) と同期
        if not is_up:
            # 下げ0(満潮)=3, 下げ10(干潮)=9
            pos = 3 + (step * 0.6)
        else:
            # 上げ0(干潮)=9, 上げ10(満潮)=15
            pos = 9 + (step * 0.6)

        # 4時-19時は左、それ以外は右
        h = row['datetime'].hour
        base_x = -6 if 4 <= h <= 19 else 12 # 昼夜で起点を18ずらす
        x = base_x + pos
        
        return pd.Series([x, y])

    if not df_p.empty:
        df_p[['x_sync', 'y_sync']] = df_p.apply(get_sync_coords, axis=1)

    # --- 3. グラフ描画 ---
    fig = go.Figure()
    
    # 潮位背景（面グラフ）
    x_line = np.linspace(0, 27, 1000)
    # y = 100 * sin(2*pi*(x-9)/12) により、x=3,15,27が満潮(100)、x=9,21が干潮(-100)
    y_line = 100 * np.sin(2 * np.pi * (x_line - 9) / 12)
    
    fig.add_trace(go.Scatter(
        x=x_line, y=y_line, 
        mode='lines', 
        line=dict(color='#00d4ff', width=3),
        fill='tozeroy', 
        fillcolor='rgba(0, 212, 255, 0.2)',
        hoverinfo='skip'
    ))

    # 境界線
    fig.add_vline(x=13.5, line_width=2, line_dash="solid", line_color="rgba(255,255,255,0.5)")

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
            tickvals=[6, 21],
            ticktext=["☀️ 昼 エリア", "🌙 夜 エリア"],
            tickfont=dict(size=16, color="white"),
            range=[-0.5, 27.5],
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
