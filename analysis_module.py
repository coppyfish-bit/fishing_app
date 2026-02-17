import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 時合精密解析（詳細リンク機能付き）")

    if df.empty:
        st.info("データがありません。")
        return

    selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()))
    df_p = df[df["場所"] == selected_place].copy()
    
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')
    df_p = df_p.dropna(subset=['datetime']).reset_index() # indexを保持

    # --- 1. 座標計算ロジック（昼夜・20時境界対応済） ---
    def get_sync_coords(row):
        phase_str = str(row['潮位フェーズ'])
        nums = re.findall(r'\d+', phase_str.translate(str.maketrans('０１２３４５６７８９', '0123456789')))
        step = int(nums[0]) if nums else 5
        h = row['datetime'].hour + row['datetime'].minute / 60
        shifted_h = h if h >= 12 else h + 24

        is_up = "上げ" in phase_str
        y = (-100 + (step * 20)) if is_up else (100 - (step * 20))

        if shifted_h < 20.0:
            peak = 12.0
            sync_x = peak - ((10 - step) * 0.3) if is_up else peak + (step * 0.6)
        else:
            if is_up:
                peak = 24.0 if shifted_h < 24.0 else 36.0
                sync_x = peak - ((10 - step) * 0.6)
            else:
                peak = 24.0
                sync_x = peak + (step * 0.6)
        return pd.Series([sync_x, y])

    df_p[['x_sync', 'y_sync']] = df_p.apply(get_sync_coords, axis=1)

    # --- 2. グラフ描画 ---
    fig = go.Figure()
    x_line = np.linspace(8, 38, 1000)
    y_line = 100 * np.cos(2 * np.pi * (x_line - 24) / 12)
    fig.add_trace(go.Scatter(x=x_line, y=y_line, mode='lines', line=dict(color='rgba(100, 200, 255, 0.2)', width=2), hoverinfo='skip'))

    # プロット（一括で描画することで選択判定を容易にする）
    scatter = go.Scatter(
        x=df_p['x_sync'], y=df_p['y_sync'],
        mode='markers+text',
        marker=dict(size=20, color=df_p['潮位フェーズ'].apply(lambda x: '#00ffd0' if '上げ' in x else '#ff4b4b'), 
                    symbol=df_p['潮位フェーズ'].apply(lambda x: 'triangle-up' if '上げ' in x else 'triangle-down'),
                    line=dict(width=2, color='white')),
        text=df_p.apply(lambda r: f"{r['魚種']}{r['全長_cm']}cm", axis=1),
        textposition="top center",
        # customdataに元のindexを仕込んでおく
        customdata=df_p['index'],
        hovertemplate="クリックして詳細を表示<br>時刻: %{text}<extra></extra>"
    )
    fig.add_trace(scatter)

    fig.update_layout(
        xaxis=dict(tickvals=[12, 18, 20, 24, 30, 36], ticktext=["12:00(満)", "18:00(干)", "20:00(境)", "0:00(満)", "6:00(干)", "12:00(満)"], range=[8.5, 37.5]),
        yaxis=dict(tickvals=[100, 0, -100], ticktext=["満潮", "中間", "干潮"], range=[-150, 200]),
        template="plotly_dark", height=600, showlegend=False,
        clickmode='event+select' # クリックを有効化
    )

    # グラフを表示し、クリックイベントを取得
    # ※streamlit-plotly-eventsを使用するか、標準のplotly_chartで判定
    selected_points = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

    # --- 3. クリックされた時の詳細表示 ---
    # 選択された点がある場合
    if selected_points and "selection" in selected_points and selected_points["selection"]["points"]:
        # 選択された最初の点のcustomdata(index)を取得
        clicked_index = selected_points["selection"]["points"][0]["customdata"]
        target_data = df_p[df_p['index'] == clicked_index].iloc[0]

        st.markdown("---")
        st.subheader(f"🐟 【詳細】{target_data['魚種']} {target_data['全長_cm']}cm")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.write(f"**日時:** {target_data['datetime'].strftime('%Y/%m/%d %H:%M')}")
            st.write(f"**潮位フェーズ:** {target_data['潮位フェーズ']}")
            st.write(f"**場所:** {target_data['場所']}")
        with col2:
            # メモなどがあれば表示
            if 'memo' in target_data:
                st.info(f"📝 メモ: {target_data['memo']}")
        
        if st.button("この釣果をさらに詳しく見る（個別ページへ）"):
            # ここでセッション状態を書き換えて、メインの表示を切り替えるなどの処理
            st.session_state.selected_fish_id = clicked_index
            st.info("個別詳細ページへの遷移ロジックをここに記述します。")
