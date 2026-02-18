import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 シームレス・時合精密解析")

    if df.empty:
        st.info("データがありません。")
        return

    # --- 1. フィルタリング設定 ---
    col_f1, col_f2 = st.columns([1, 2])
    
    with col_f1:
        # 1. まず場所を選択（ここで selected_place が定義される）
        places = sorted(df["場所"].unique())
        selected_place = st.selectbox("📍 場所を選択", places, key="ana_place")
    
    # 2. 選択された場所のデータを抽出
    df_p_base = df[df["場所"] == selected_place].copy()

    with col_f2:
        all_species = sorted(df_p_base["魚種"].unique())
        top_species = df_p_base["魚種"].value_counts().idxmax() if not df_p_base.empty else None
        default_selection = [top_species] if top_species else []
        selected_species = st.multiselect("🐟 魚種を選択", all_species, default=default_selection, key="ana_species")

    # --- デバッグ表示（エラー回避のため定義の後に配置） ---
    # st.caption(f"DEBUG: 全 {len(df)} 件中、この場所のデータは {len(df_p_base)} 件です。")

   # --- データの前処理 (柔軟な日付解析モード) ---
    df_p = df_p_base.copy()
    
    # 柔軟に日付を読み込む（dayfirst=False, yearfirst=True など自動推論）
    # errors='coerce' は維持しつつ、読み込み前に文字列のクリーンアップを行う
    df_p['datetime'] = df_p['datetime'].astype(str).str.strip() # 前後の空白を削除
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')
    
    # 【追加】それでもエラーになる場合、一度だけ「日付のみ」で再試行する救済処置
    if df_p['datetime'].isna().any():
        idx = df_p['datetime'].isna()
        # エラーになった行だけ別の解析を試みる（日付として認識できる部分だけ抽出）
        df_p.loc[idx, 'datetime'] = pd.to_datetime(df_p_base.loc[idx, 'datetime'], errors='coerce', fuzzy=True)

    before_drop = len(df_p)
    df_p = df_p.dropna(subset=['datetime'])
    after_drop = len(df_p)
    
    if before_drop != after_drop:
        st.warning(f"⚠️ 日付の形式が正しくないデータが {before_drop - after_drop} 件あります。")

    # --- 2. 座標計算ロジック ---
    def get_sync_coords(row):
        phase_str = str(row['潮位フェーズ']).strip()
        nums = re.findall(r'\d+', phase_str.translate(str.maketrans('０１２３４５６７８９', '0123456789')))
        step = int(nums[0]) if nums else 5
        step = max(0, min(10, step))
        is_up = "下げ" not in phase_str
        
        # 波形位置計算
        if not is_up:
            x_val = step * 0.6
        else:
            x_val = 6 + (step * 0.6)

        h = row['datetime'].hour
        offset = 0 if 4 <= h <= 19 else 12.5 
        final_x = x_val + offset
        final_y = 100 * np.cos(x_val * np.pi / 6)
        
        return pd.Series([final_x, final_y])

    if not df_p.empty:
        df_p[['x_sync', 'y_sync']] = df_p.apply(get_sync_coords, axis=1)

    # --- 3. グラフ描画 ---
    fig = go.Figure()
    
    x_line = np.linspace(0, 25, 1000)
    y_line = [100 * np.cos(x * np.pi / 6) if x <= 12.5 else 100 * np.cos((x - 12.5) * np.pi / 6) for x in x_line]
    
    fig.add_trace(go.Scatter(
        x=x_line, y=y_line, 
        mode='lines', 
        line=dict(color='#00d4ff', width=3, shape='spline'),
        fill='tozeroy', 
        fillcolor='rgba(0, 212, 255, 0.2)',
        hoverinfo='skip'
    ))

    fig.add_vline(x=12.25, line_width=1, line_dash="dot", line_color="rgba(255,255,255,0.3)")

    if selected_species:
        # 選択された魚種のみを抽出
        display_df = df_p[df_p['魚種'].isin(selected_species)]
        
        if not display_df.empty:
            is_up_list = display_df['潮位フェーズ'].apply(lambda x: "下げ" not in str(x))
            symbols = is_up_list.apply(lambda x: 'triangle-up' if x else 'triangle-down')
            colors = is_up_list.apply(lambda x: '#00ffd0' if x else '#ff4b4b')
            
            fig.add_trace(go.Scatter(
                x=display_df['x_sync'], y=display_df['y_sync'],
                mode='markers',
                name="釣果ポイント",
                marker=dict(size=18, symbol=symbols, color=colors, line=dict(width=1.5, color='white')),
                text=display_df['datetime'].dt.strftime('%m/%d %H:%M'),
                hovertemplate="<b>%{text}</b><extra></extra>"
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
        template="plotly_dark", height=550, margin=dict(l=10, r=10, t=20, b=60)
    )

    st.plotly_chart(fig, use_container_width=True)

