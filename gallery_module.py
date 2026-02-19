import streamlit as st
import pandas as pd

def show_gallery_page(df):
    st.subheader("🖼️ 全釣果ギャラリー（写真をタップすると地図を表示）")
    
    if df is None or df.empty:
        st.info("表示するデータがまだありません。")
        return

    df_gallery = df.copy()

    # --- 1. 日時に基づく正確なソート ---
    # 秒あり(2026-02-10 22:53:00)と秒なし(2026-02-17 16:08)が混在しても
    # 正しく「日時」として認識させてから、降順（新しい順）に並べ替えます。
    df_gallery['datetime_parsed'] = pd.to_datetime(df_gallery['datetime'], errors='coerce')
    df_gallery = df_gallery.sort_values(by='datetime_parsed', ascending=False, na_position='last')

    cols = st.columns(3)
    display_count = 0
    
    for i, (idx, row) in enumerate(df_gallery.iterrows()):
        img_url = row.get("filename")
        # 画像URLがない、または無効な場合はスキップ
        if not img_url or pd.isna(img_url) or str(img_url).lower() == "nan":
            continue
        
        # 緯度・経度を取得
        lat = row.get('lat')
        lon = row.get('lon')
        
        # マップのURLを作成 (緯度経度がある場合のみ)
        if pd.notnull(lat) and pd.notnull(lon) and lat != 0:
            map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
        else:
            map_url = "#"

        with cols[display_count % 3]:
            # --- 表示用データの整理 ---
            # 日時：一度datetime型にしてから「分」までの形式に統一
            dt_val = row.get('datetime', '-')
            try:
                parsed_dt = pd.to_datetime(dt_val)
                display_dt = parsed_dt.strftime('%Y-%m-%d %H:%M')
            except:
                display_dt = str(dt_val)[:16]
            
            # 各種情報を変数に格納
            temp = f"{row.get('気温', '-')}℃"
            wind = f"{row.get('風向', '')}{row.get('風速', '-')}m"
            tide_name = row.get('潮名', '-')
            tide_phase = row.get('潮位フェーズ', '-')
            place_name = row.get('場所', '-')
            fish_info = f"{row.get('魚種', '-')} {row.get('全長_cm', '-')}cm"

            # HTMLでのカード表示 (全体をaタグで囲ってリンク化)
            overlay_html = f"""
            <a href="{map_url}" target="_blank" style="text-decoration: none; color: inherit;">
                <div style="position: relative; width: 100%; margin-bottom: 20px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
                    <img src="{img_url}" style="width: 100%; aspect-ratio: 1/1; object-fit: cover; display: block;">
                    <div style="position: absolute; bottom: 0; width: 100%; padding: 8px; background: linear-gradient(transparent, rgba(0,0,0,0.9)); color: white; font-size: 0.72rem; line-height: 1.4;">
                        <b style="color: #00ffd0; font-size: 0.85rem;">{fish_info}</b><br>
                        📍 {place_name}<br>
                        📅 {display_dt}<br>
                        🌡️ {temp} / 💨 {wind}<br>
                        🌊 {tide_name} ({tide_phase})
                    </div>
                </div>
            </a>
            """
            st.markdown(overlay_html, unsafe_allow_html=True)
            display_count += 1
