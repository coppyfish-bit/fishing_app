import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 魚種別・最多釣果フォーカス解析")

    if df.empty:
        st.info("データがありません。")
        return

    # --- 1. フィルタリング設定 ---
    col_f1, col_f2 = st.columns([1, 2])
    
    with col_f1:
        places = sorted(df["場所"].unique())
        selected_place = st.selectbox("📍 場所を選択", places, key="ana_place")
    
    # 選択された場所のデータをベースにする
    df_p_base = df[df["場所"] == selected_place].copy()

    with col_f2:
        # その場所で釣れている魚種のリスト
        all_species = sorted(df_p_base["魚種"].unique())
        
        # --- 最多釣果の魚種を特定 ---
        if not df_p_base.empty:
            # 魚種ごとの件数を数え、最大件数の名前を取得
            top_species = df_p_base["魚種"].value_counts().idxmax()
            default_selection = [top_species]
        else:
            default_selection = []
        
        # マルチセレクトにデフォルト値を適用
        selected_species = st.multiselect(
            "🐟 魚種を選択 (初期表示: 最多釣果)", 
            all_species, 
            default=default_selection, 
            key="ana_species"
        )

    # --- 2. データの前処理 (秒なし対応) ---
    df_p = df_p_base.copy()
    
    def clean_datetime_safe(val):
        if pd.isna(val): return None
        s = str(val).strip()
        s = s.translate(str.maketrans('０１２３４５６７８９：／－', '0123456789:/-'))
        s = s.replace('年', '/').replace('月', '/').replace('日', ' ').replace('時', ':').replace('分', '')
        s = re.sub(r'[^0-9:/\-\s]', '', s)
        return s if s else None

    def parse_dt(s):
        if not s: return pd.NaT
        dt = pd.to_datetime(s, errors='coerce')
        if pd.notna(dt): return dt
        for fmt in ('%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M'):
            try:
                return pd.to_datetime(s, format=fmt)
            except:
                continue
        return pd.NaT

    df_p['datetime_str'] = df_p['datetime'].apply(clean_datetime_safe)
    df_p['datetime'] = df_p['datetime_str'].apply(parse_dt)
    df_p = df_p.dropna(subset=['datetime'])

    # --- 3. 座標計算ロジック ---
    def get_sync_coords(row):
        phase_str = str(row['潮位フェーズ']).strip()
        nums = re.findall(r'\d+', phase_str.translate(str.maketrans('０１２３４５６７８９', '0123456789')))
        step = int(nums[0]) if nums else 5
        step = max(0, min(10, step))
        is_up = "下げ" not in phase_str
        
        # x=0:満潮, x=6:干潮, x=12:満潮
        x_val = step * 0.6 if not is_up else 6 + (step * 0.6)
        h = row['datetime'].hour
        offset = 0 if 4 <= h <= 19 else 12.5
        final_x = x_val + offset
        final_y = 100 * np.cos(x_val * np.pi / 6)
        return pd.Series([final_x, final_y])

    if not df_p.empty:
        df_p[['x_sync', 'y_sync']] = df_p.apply(get_sync_coords, axis=1)

    # --- 4. グラフ描画 ---
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

    if selected_species and not df_p.empty:
        display_df = df_p[df_p['魚種'].isin(selected_species)]
        
        if not display_df.empty:
            is_up_list = display_df['潮位フェーズ'].apply(lambda x: "下げ" not in str(x))
            symbols = is_up_list.apply(lambda x: 'triangle-up' if x else 'triangle-down')
            colors = is_up_list.apply(lambda x: '#00ffd0' if x else '#ff4b4b')
            
            fig.add_trace(go.Scatter(
                x=display_df['x_sync'], y=display_df['y_sync'],
                mode='markers',
                name="釣果データ",
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
