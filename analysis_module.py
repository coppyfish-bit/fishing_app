import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 時合精密解析")

    if df.empty:
        st.info("データがありません。")
        return

    # --- 1. フィルタリング設定 ---
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()))
    
    with col_f2:
        all_species = sorted(df[df["場所"] == selected_place]["魚種"].unique())
        initial_targets = ["スズキ", "ヒラスズキ"]
        default_selection = [s for s in initial_targets if s in all_species]
        
        # スズキらがいなければ最初の1種を選択
        if not default_selection and all_species:
            default_selection = [all_species[0]]
            
        selected_species = st.multiselect("🐟 表示する魚種を選択", all_species, default=default_selection)

    # データの前処理
    df_p = df[df["場所"] == selected_place].copy()
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')
    df_p = df_p.dropna(subset=['datetime'])
    # クリック判定用のユニークID（重要：これをcustomdataに渡す）
    df_p['fish_id'] = df_p['datetime'].dt.strftime('%Y%m%d%H%M%S') + "_" + df_p['魚種']

    # --- 2. 座標計算ロジック ---
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
            peak = 24.0 if not is_up else (24.0 if shifted_h < 24.0 else 36.0)
            sync_x = peak + (step * 0.6) if not is_up else peak - ((10 - step) * 0.6)
        return pd.Series([sync_x, y])

    if not df_p.empty:
        df_p[['x_sync', 'y_sync']] = df_p.apply(get_sync_coords, axis=1)

    # --- 3. グラフ描画 ---
    fig = go.Figure()
    x_line = np.linspace(8, 38, 1000)
    y_line = 100 * np.cos(2 * np.pi * (x_line - 24) / 12)
    fig.add_trace(go.Scatter(x=x_line, y=y_line, mode='lines', line=dict(color='rgba(100, 200, 255, 0.2)', width=2), hoverinfo='skip'))

    if selected_species:
        for species in selected_species:
            spec_df = df_p[df_p['魚種'] == species]
            if spec_df.empty: continue
            
            fig.add_trace(go.Scatter(
                x=spec_df['x_sync'], y=spec_df['y_sync'],
                mode='markers',
                name=species,
                marker=dict(size=18, symbol='circle', line=dict(width=2, color='white')),
                customdata=spec_df['fish_id'], # これがクリック時に渡される
                hovertemplate=f"<b>{species}</b><br>クリックで詳細を表示<extra></extra>"
            ))

    fig.update_layout(
        xaxis=dict(tickvals=[12, 18, 24, 30, 36], ticktext=["12:00", "18:00", "0:00", "6:00", "12:00"], range=[8.5, 37.5]),
        yaxis=dict(tickvals=[100, 0, -100], ticktext=["満潮", "中間", "干潮"], range=[-150, 220]),
        template="plotly_dark", height=500, clickmode='event+select'
    )

    # グラフ表示とクリックイベント取得
    event_data = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

    # --- 4. 詳細パネル（修復ポイント） ---
    if event_data and "selection" in event_data and event_data["selection"]["points"]:
        # クリックされた点の ID を取得
        selected_id = event_data["selection"]["points"][0]["customdata"]
        # df_p から該当する行を特定
        items = df_p[df_p['fish_id'] == selected_id]
        
        if not items.empty:
            item = items.iloc[0]
            st.markdown("---")
            col1, col2 = st.columns([1.5, 1])

            with col1:
                # 画像表示 (filename列)
                img_url = item.get('filename')
                if pd.notna(img_url) and str(img_url).startswith('http'):
                    url_str = str(img_url)
                    if "drive.google.com" in url_str:
                        # DriveのID抽出ロジック
                        fid = url_str.split('/d/')[1].split('/')[0] if "/d/" in url_str else url_str.split('id=')[1].split('&')[0]
                        url_str = f"https://drive.google.com/uc?id={fid}"
                    st.image(url_str, use_container_width=True)
                else:
                    st.info("📷 写真データがありません")

            with col2:
                st.subheader(f"🐟 {item['魚種']} {item['全長_cm']}cm")
                m1, m2 = st.columns(2)
                m1.metric("🌡️ 気温", f"{item.get('気温', '--')}°C")
                m2.metric("💨 風速", f"{item.get('風速', '--')}m/s")
                m3, m4 = st.columns(2)
                m3.metric("🌊 潮位", f"{item.get('潮位_cm', '--')}cm")
                m4.metric("🧭 風向", f"{item.get('風向', '--')}")
                st.write(f"**⏰ 時刻:** {item['datetime'].strftime('%H:%M')}")
                if 'memo' in item and pd.notna(item['memo']):
                    st.info(f"📝 **メモ:**\n{item['memo']}")
    else:
        st.info("💡 グラフ上の点をクリックすると詳細が表示されます。")

