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

    # 1. データの整理（元のdfから必要な列を確実に保持する）
    selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()))
    
    # 選択した場所のデータを抽出
    df_p = df[df["場所"] == selected_place].copy()
    
    # 日時変換
    df_p['datetime'] = pd.to_datetime(df_p['datetime'], errors='coerce')
    df_p = df_p.dropna(subset=['datetime'])
    
    # 【重要】クリック判定用にユニークIDを付与（元のIndexを保持）
    df_p['unique_id'] = df_p.index 
    df_p = df_p.reset_index(drop=True)

    # --- 座標計算（シームレスロジック） ---
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
        marker=dict(size=22, 
                    color=df_p['潮位フェーズ'].apply(lambda x: '#00ffd0' if '上げ' in x else '#ff4b4b'), 
                    symbol=df_p['潮位フェーズ'].apply(lambda x: 'triangle-up' if '上げ' in x else 'triangle-down'),
                    line=dict(width=2, color='white')),
        text=df_p.apply(lambda r: f"{r['魚種']}{r['全長_cm']}cm", axis=1),
        textposition="top center",
        customdata=df_p['unique_id'], # ここで元のIndexを渡す
        hovertemplate="<b>クリックして詳細を表示</b><extra></extra>"
    ))

    fig.update_layout(
        xaxis=dict(tickvals=[12, 18, 24, 30, 36], ticktext=["12:00", "18:00", "0:00", "6:00", "12:00"], range=[8.5, 37.5]),
        yaxis=dict(tickvals=[100, 0, -100], ticktext=["満潮", "中間", "干潮"], range=[-150, 220]),
        template="plotly_dark", height=500, showlegend=False,
        clickmode='event+select'
    )

    event_data = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

    # --- 3. 詳細パネル ---
    if event_data and "selection" in event_data and event_data["selection"]["points"]:
        # 選択されたunique_idを取得
        target_id = event_data["selection"]["points"][0]["customdata"]
        
        # オリジナルの df から直接データを取得（df_pではなく大元のdfを使うのが確実）
        item = df.loc[target_id]

        st.markdown("---")
        
        col1, col2 = st.columns([1.5, 1])

        with col1:
            # 【画像表示ロジックの最強化】
            # dfに存在するすべての列名から「画像っぽい」ものを自動抽出
            img_column = next((c for c in df.columns if c in ['画像', '写真', 'image', 'photo', 'picture']), None)
            
            if img_column and pd.notna(item[img_column]):
                try:
                    st.image(item[img_column], caption=f"釣果写真: {item['魚種']}", use_container_width=True)
                except Exception as e:
                    st.error(f"⚠️ 画像データの形式が正しくありません: {e}")
            else:
                st.warning(f"📷 写真列「{img_column}」にデータがありません。")
                # 念のため、全列名を確認用に表示
                # st.write("データ列一覧:", list(df.columns))

        with col2:
            st.subheader(f"🐟 {item['魚種']} {item['全長_cm']}cm")
            st.metric("🌡️ 気温", f"{item.get('気温', '--')}°C")
            st.metric("💨 風速", f"{item.get('風速', '--')}m/s")
            st.write(f"**⏰ 時刻:** {pd.to_datetime(item['datetime']).strftime('%H:%M')}")
            st.write(f"**🌊 潮位:** {item['潮位フェーズ']}")
            if 'memo' in item and item['memo']:
                st.info(f"📝 **メモ:**\n{item['memo']}")
    else:
        st.info("💡 グラフ上のプロットをクリックすると、ここに写真が表示されます。")
