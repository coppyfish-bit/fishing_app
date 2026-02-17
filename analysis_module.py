import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 時合精密解析（フォト詳細表示）")

    if df.empty:
        st.info("データがありません。")
        return

    # 1. データの整理
    selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()))
    df_p = df[df["場所"] == selected_place].copy()
    
    # 日時変換
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')
    df_p = df_p.dropna(subset=['datetime'])
    
    # 【重要】クリック判定用に現在のインデックスを新しい列として固定
    df_p['plot_id'] = range(len(df_p))
    df_p = df_p.reset_index(drop=True)

    # --- 座標計算（既存のシームレスロジック） ---
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

    fig.add_trace(go.Scatter(
        x=df_p['x_sync'], y=df_p['y_sync'],
        mode='markers+text',
        marker=dict(size=22, color=df_p['潮位フェーズ'].apply(lambda x: '#00ffd0' if '上げ' in x else '#ff4b4b'), 
                    symbol=df_p['潮位フェーズ'].apply(lambda x: 'triangle-up' if '上げ' in x else 'triangle-down'),
                    line=dict(width=2, color='white')),
        text=df_p.apply(lambda r: f"{r['魚種']}{r['全長_cm']}cm", axis=1),
        textposition="top center",
        # customdata に plot_id を渡す
        customdata=df_p['plot_id'],
        hovertemplate="<b>クリックして詳細を表示</b><extra></extra>"
    ))

    fig.update_layout(
        xaxis=dict(tickvals=[12, 18, 24, 30, 36], ticktext=["12:00", "18:00", "0:00", "6:00", "12:00"], range=[8.5, 37.5]),
        yaxis=dict(tickvals=[100, 0, -100], ticktext=["満潮", "中間", "干潮"], range=[-150, 220]),
        template="plotly_dark", height=500, showlegend=False,
        clickmode='event+select'
    )

    # グラフを表示（on_selectで再実行）
    event_data = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

    # --- 3. クリック詳細表示（写真表示の強化） ---
    if event_data and "selection" in event_data and event_data["selection"]["points"]:
        # 選択されたIDを取得
        selected_id = event_data["selection"]["points"][0]["customdata"]
        item = df_p[df_p['plot_id'] == selected_id].iloc[0]

        st.markdown("---")
        st.subheader(f"🖼️ {item['魚種']} の詳細データ")

        col1, col2 = st.columns([1.5, 1])

        with col1:
            # 【写真表示の徹底修正】
            # データ保存時の候補となる列名をすべてチェックします
            photo_keys = ['画像', 'image', '写真', 'photo']
            img_data = None
            for key in photo_keys:
                if key in item and item[key] is not None:
                    img_data = item[key]
                    break
            
            if img_data:
                try:
                    # bytes形式でもURL(パス)でも対応可能
                    st.image(img_data, caption=f"釣果時刻: {item['datetime'].strftime('%H:%M')}", use_container_width=True)
                except Exception as e:
                    st.error(f"画像の読み込みに失敗しました。データ形式を確認してください。({e})")
            else:
                st.info("📷 この釣果に写真は登録されていません。")
                # デバッグ用：現在どの列があるかを表示（必要なければ消してください）
                # st.write("利用可能な列名:", list(item.index))

        with col2:
            st.metric("🌡️ 気温", f"{item.get('気温', '--')}°C")
            st.metric("💨 風速", f"{item.get('風速', '--')}m/s")
            st.write(f"**🌊 潮位:** {item['潮位フェーズ']}")
            if '潮名' in item: st.write(f"**🌙 潮回り:** {item['潮名']}")
            if 'memo' in item and item['memo']:
                st.info(f"📝 **メモ:**\n{item['memo']}")

    else:
        st.info("💡 グラフ上の▲や▼をクリックすると、ここに写真が表示されます。")
