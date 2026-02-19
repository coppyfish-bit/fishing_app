import streamlit as st
import pandas as pd

def show_gallery_page(df):
    st.subheader("🖼️ 全釣果ギャラリー（写真をタップすると地図を表示）")
    
    if df is None or df.empty:
        st.info("表示するデータがまだありません。")
        return

    df_gallery = df.copy()

    # --- 【修正】日時に基づく正確な並び替え ---
    # 1. datetime列を日付型に変換（変換できないものはNaTになる）
    df_gallery['datetime_parsed'] = pd.to_datetime(df_gallery['datetime'], errors='coerce')
    
    # 2. 日付が新しい順（降順）にソート。日付がないデータは最後に回す
    df_gallery = df_gallery.sort_values(by='datetime_parsed', ascending=False)
    # ---------------------------------------

    # 日付の読み込み処理 (表示用の文字列整理)
    df_gallery['datetime'] = df_gallery['datetime'].fillna('-').astype(str)

    cols = st.columns(3)
    display_count = 0
    
    for i, (idx, row) in enumerate(df_gallery.iterrows()):
        img_url = row.get("filename")
        if not img_url or pd.isna(img_url) or img_url == "nan":
            continue
        
        # 緯度・経度を取得
        lat = row.get('lat')
        lon = row.get('lon')
        
        # マップのURLを作成 (緯度経度がある場合のみ)
        if pd.notnull(lat) and pd.notnull(lon) and lat != 0:
            # 💡 googleusercontent.com ではなく標準的な Google Maps URL に修正
            map_url = f"https://www.google.com/maps?q={lat},{lon}"
        else:
            map_url = "#"

        with cols[display_count % 3]:
            # 表示用データの整理
            raw_dt = str(row.get('datetime', '-'))
            display_dt = raw_dt[:16] if len(raw_dt) > 16 else raw_dt
            
            temp = f"{row.get('気温', '-')}℃"
            wind = f"{row.get('風向', '')}{row.get('風速', '-')}m"
            tide_name = row.get('潮名', '-')
            tide_phase = row.get('潮位フェーズ', '-')
            place_name = row.get('場所', '-')
            fish_info = f"{row.get('魚種', '-')} {row.get('全長_cm', '-')}cm"

            # HTMLでのカード表示
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
