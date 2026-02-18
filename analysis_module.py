import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 全データ強制表示・時合解析")

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
        selected_species = st.multiselect("🐟 魚種を選択", all_species, default=default_selection, key="ana_species")

    # データの前処理
    df_p = df[df["場所"] == selected_place].copy()
    # 日付が壊れていても、無理やり文字列から日付を作る
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')
    df_p = df_p.dropna(subset=['datetime'])

    # --- 2. 座標計算ロジック (救済モード) ---
    def get_sync_coords(row):
        phase_str = str(row['潮位フェーズ']).strip()
        
        # 【救済1】数字の抽出（全角半角問わず）
        nums = re.findall(r'\d+', phase_str.translate(str.maketrans('０１２３４５６７８９', '0123456789')))
        
        # 【救済2】数字がなければ5分、あればその数字を採用
        step = int(nums[0]) if nums else 5
        step = max(0, min(10, step))
        
        # 潮位フェーズによる判定（上げ・下げが含まれない場合のデフォルトは上げ）
        is_up = "下げ" not in phase_str # "上げ"が含まれるか、何もなければ上げ扱い
        
        # Y軸: 潮位フェーズから高さを決定
        y = -100 + (step * 20) if is_up else 100 - (step * 20)

        # X軸: 時間帯によるエリア分け
        h = row['datetime'].hour
        # 下げ満潮付近(0) ～ 干潮(6) ～ 上げ満潮(12) への変換
        if not is_up:
            pos = step * 0.6
        else:
            pos = 6 + (step * 0.6)

        # 4時〜19時(昼)は x=0〜12、それ以外(夜)は x=15〜27
        base_x = 0 if 4 <= h <= 19 else 15
        x = base_x + pos
        
        return pd.Series([x, y])

    if not df_p.empty:
        df_p[['x_sync', 'y_sync']] = df_p.apply(get_sync_coords, axis=1)

    # --- 3. グラフ描画 ---
    fig = go.Figure()
    
    # 潮位背景（面グラフ）
    x_line = np.linspace(0, 27, 1000)
    y_line = 100 * np.sin(2 * np.pi * (x_line - 9) / 12)
    
    fig.add_trace(go.Scatter(
        x=x_line, y=y_line, 
        mode='lines', 
        line=dict(color='#00d4ff', width=3),
        fill='tozeroy', 
        fillcolor='rgba(0, 212, 255, 0.2)',
        hoverinfo='skip',
        name='潮位目安'
    ))

    # 中央の境界線
    fig.add_vline(x=13.5, line_width=2, line_dash="dash", line_color="rgba(255,255,255,0.3)")

    if selected_species:
        for species in selected_species:
            spec_df = df_p[df_p['魚種'] == species]
            if spec_df.empty: continue
            
            # 「下げ」という文字が入っていないものはすべて「上げ」の三角形にする救済
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
            tickvals=[0, 3, 6, 9, 12, 15, 18, 21, 24, 27],
            ticktext=["下げ始", "干潮", "上げ始", "満潮", "下げ終", "下げ始", "干潮", "上げ始", "満潮", "下げ終"],
            range=[-0.5, 27.5],
            gridcolor='rgba(255,255,255,0.05)'
        ),
        yaxis=dict(
            tickvals=[100, 0, -100], 
            ticktext=["満潮", "中間", "干潮"], 
            range=[-120, 150],
            gridcolor='rgba(255,255,255,0.1)'
        ),
        template="plotly_dark",
        height=550,
        margin=dict(l=10, r=10, t=50, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)
