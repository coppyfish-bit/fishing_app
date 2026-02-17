import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 時合精密解析（スプレッドシート画像対応版）")

    if df.empty:
        st.info("データがありません。")
        return

    selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()))
    df_p = df[df["場所"] == selected_place].copy()
    
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')
    df_p = df_p.dropna(subset=['datetime'])
    
    # クリック判定用のID作成
    df_p['fish_id'] = df_p['datetime'].dt.strftime('%Y%m%d%H%M%S') + "_" + df_p['魚種']

    # --- 座標計算（これまでのロジック） ---
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

    # --- グラフ描画 ---
    fig = go.Figure()
    x_line = np.linspace(8, 38, 1000)
    y_line = 100 * np.cos(2 * np.pi * (x_line - 24) / 12)
    fig.add_trace(go.Scatter(x=x_line, y=y_line, mode='lines', line=dict(color='rgba(100, 200, 255, 0.2)', width=2), hoverinfo='skip'))

    fig.add_trace(go.Scatter(
        x=df_p['x_sync'], y=df_p['y_sync'],
        mode='markers+text',
        marker=dict(size=22, 
                    color=df_p['潮位フェーズ'].apply(lambda x: '#00ffd0' if '上げ' in x else '#ff4b4b'), 
                    symbol=df_p['潮位フェーズ'].apply(lambda x: 'triangle-up' if '上げ' in x else 'triangle-down'),
                    line=dict(width=2, color='white')),
        text=df_p.apply(lambda r: f"{r['魚種']}{r['全長_cm']}cm", axis=1),
        textposition="top center",
        customdata=df_p['fish_id'], 
        hovertemplate="<b>クリックして詳細を表示</b><extra></extra>"
    ))

    fig.update_layout(
        xaxis=dict(tickvals=[12, 18, 24, 30, 36], ticktext=["12:00", "18:00", "0:00", "6:00", "12:00"], range=[8.5, 37.5]),
        yaxis=dict(tickvals=[100, 0, -100], ticktext=["満潮", "中間", "干潮"], range=[-150, 220]),
        template="plotly_dark", height=500, showlegend=False, clickmode='event+select'
    )

    event_data = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

    # --- 3. 詳細パネル（URL画像対応） ---
    if event_data and "selection" in event_data and event_data["selection"]["points"]:
        selected_fish_id = event_data["selection"]["points"][0]["customdata"]
        item = df_p[df_p['fish_id'] == selected_fish_id].iloc[0]

        st.markdown("---")
        col1, col2 = st.columns([1.5, 1])

        with col1:
            # スプレッドシートの画像URLを取得
            # 実際の列名に合わせてください（'画像URL', '画像', 'URL' など）
            img_keys = ['画像', 'image', '画像URL', 'URL', '写真']
            img_url = None
            for k in img_keys:
                if k in item and pd.notna(item[k]):
                    img_url = str(item[k])
                    break
            
            if img_url and img_url.startswith('http'):
                try:
                    # Google DriveのプレビューURLを直接表示可能なURLに変換する簡易ロジック
                    if "drive.google.com" in img_url and "view" in img_url:
                        # URLを /d/XXX/view から /uc?id=XXX に書き換え
                        file_id = img_url.split('/d/')[1].split('/')[0]
                        img_url = f"https://drive.google.com/uc?id={file_id}"
                    
                    st.image(img_url, use_container_width=True)
                except Exception as e:
                    st.error(f"⚠️ 画像の読み込みに失敗しました。URLを確認してください。")
            else:
                st.warning("📷 画像URLが見つかりません。")
                # st.write("URL列の値:", img_url) # デバッグ用

        with col2:
            st.subheader(f"🐟 {item['魚種']} {item['全長_cm']}cm")
            st.write(f"**⏰ 時刻:** {item['datetime'].strftime('%H:%M')}")
            st.metric("🌡️ 気温", f"{item.get('気温', '--')}°C")
            st.metric("💨 風速", f"{item.get('風速', '--')}m/s")
            if 'memo' in item and pd.notna(item['memo']):
                st.info(f"📝 **メモ:**\n{item['memo']}")
    else:
        st.info("💡 グラフ上のプロットをクリックすると、写真が表示されます。")
