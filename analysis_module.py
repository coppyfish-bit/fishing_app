import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 時合精密解析（インタラクティブ詳細表示）")

    if df.empty:
        st.info("データがありません。")
        return

    # 場所の絞り込み
    selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()))
    df_p = df[df["場所"] == selected_place].copy()
    
    # データの整理
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')
    df_p = df_p.dropna(subset=['datetime']).reset_index()

    # --- 1. 座標計算（これまでの波形同期ロジックを継承） ---
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
            peak = (24.0 if shifted_h < 24.0 else 36.0) if is_up else 24.0
            sync_x = peak - ((10 - step) * 0.6) if is_up else peak + (step * 0.6)
        return pd.Series([sync_x, y])

    df_p[['x_sync', 'y_sync']] = df_p.apply(get_sync_coords, axis=1)

    # --- 2. グラフ描画 ---
    fig = go.Figure()
    x_line = np.linspace(8, 38, 1000)
    y_line = 100 * np.cos(2 * np.pi * (x_line - 24) / 12)
    fig.add_trace(go.Scatter(x=x_line, y=y_line, mode='lines', line=dict(color='rgba(100, 200, 255, 0.2)', width=2), hoverinfo='skip'))

    # プロット（選択機能を有効化）
    scatter = go.Scatter(
        x=df_p['x_sync'], y=df_p['y_sync'],
        mode='markers+text',
        marker=dict(size=22, color=df_p['潮位フェーズ'].apply(lambda x: '#00ffd0' if '上げ' in x else '#ff4b4b'), 
                    symbol=df_p['潮位フェーズ'].apply(lambda x: 'triangle-up' if '上げ' in x else 'triangle-down'),
                    line=dict(width=2, color='white')),
        text=df_p.apply(lambda r: f"{r['魚種']}{r['全長_cm']}cm", axis=1),
        textposition="top center",
        customdata=df_p['index'], # 各点のID
        hovertemplate="<b>クリックして詳細を表示</b><extra></extra>"
    )
    fig.add_trace(scatter)

    fig.update_layout(
        xaxis=dict(tickvals=[12, 18, 24, 30, 36], ticktext=["12:00", "18:00", "0:00", "6:00", "12:00"], range=[8.5, 37.5]),
        yaxis=dict(tickvals=[100, 0, -100], ticktext=["満潮", "中間", "干潮"], range=[-150, 220]),
        template="plotly_dark", height=500, showlegend=False,
        clickmode='event+select'
    )

    # グラフを表示
    event_data = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

    # --- 3. クリックされた時の詳細パネル ---
    if event_data and "selection" in event_data and event_data["selection"]["points"]:
        clicked_id = event_data["selection"]["points"][0]["customdata"]
        item = df_p[df_p['index'] == clicked_id].iloc[0]

        st.markdown(f"### 📋 {item['魚種']} ({item['全長_cm']}cm) の釣果詳細")
        
        detail_col1, detail_col2 = st.columns([1, 1])

        with detail_col1:
            # 写真の表示（データに 'image_path' または 'image' がある想定）
            if 'image' in item and item['image']:
                st.image(item['image'], caption=f"{item['魚種']} の写真", use_container_width=True)
            else:
                st.info("📷 写真はありません")

        with detail_col2:
            st.metric("🌡️ 気温", f"{item.get('気温', '--')} °C")
            st.metric("💨 風速", f"{item.get('風速', '--')} m/s")
            
            # 潮位・時合情報のまとめ
            st.write("---")
            st.write(f"**⏰ 釣れた時刻:** {item['datetime'].strftime('%H:%M')}")
            st.write(f"**🌊 潮位状況:** {item['潮位フェーズ']}")
            if '潮位_cm' in item:
                st.write(f"**📊 潮位高さ:** {item['潮位_cm']} cm")
            if '潮名' in item:
                st.write(f"**🌙 潮回り:** {item['潮名']}")

        # メモがあれば大きく表示
        if 'memo' in item and item['memo']:
            st.warning(f"📝 **フィールドメモ:** \n\n {item['memo']}")

    else:
        st.write("💡 **グラフ上のプロット（▲▼）をクリックすると、ここに写真や詳細データが表示されます。**")
