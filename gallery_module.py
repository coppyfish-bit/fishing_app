import streamlit as st
import pandas as pd

def show_gallery_page(df):
    st.subheader("🖼️ 全釣果ギャラリー")
    
    if df is None or df.empty:
        st.info("表示するデータがまだありません。")
        return

    df_gallery = df.copy()

    # --- カラム名の存在確認 ---
    if 'filename' not in df_gallery.columns:
        st.error("スプレッドシートに 'filename' 列が見つかりません。")
        return

    # --- 1. 日時のソート処理 ---
    def clean_datetime_str(x):
        if pd.isna(x): return x
        return str(x).replace("/", "-").strip()

    df_gallery['datetime_tmp'] = df_gallery['datetime'].apply(clean_datetime_str)
    df_gallery['datetime_parsed'] = pd.to_datetime(
        df_gallery['datetime_tmp'], 
        errors='coerce', 
        dayfirst=False
    )
    
    df_gallery = df_gallery.sort_values(
        by=['datetime_parsed', 'datetime_tmp'], 
        ascending=[False, False], 
        na_position='last'
    )

    # 有効な画像データの抽出
    valid_rows = df_gallery[
        df_gallery['filename'].notna() & 
        (df_gallery['filename'].astype(str).str.lower() != "nan") &
        (df_gallery['filename'].astype(str) != "")
    ]

    # --- 2. グリッド表示 ---
    for i in range(0, len(valid_rows), 3):
        chunk = valid_rows.iloc[i : i + 3]
        cols = st.columns(3) 
        
        for j, (_, row) in enumerate(chunk.iterrows()):
            with cols[j]:
                img_url = row.get("filename")
                lat, lon = row.get('lat'), row.get('lon')
                map_url = f"https://www.google.com/maps?q={lat},{lon}" if pd.notnull(lat) and lat != 0 else "#"

                dt_val = row.get('datetime_parsed')
                display_dt = dt_val.strftime('%Y-%m-%d %H:%M') if pd.notnull(dt_val) else str(row.get('datetime', '-'))[:16]
                
                # 表示用データの抽出
                fish_info = f"{row.get('魚種', '-')} {row.get('全長_cm', '-')}cm"
                place_name = row.get('場所', '-')
                temp = f"{row.get('気温', '-')}℃"
                wind = f"{row.get('風向', '')}{row.get('風速', '-')}m"
                rain = f"{row.get('降水量', '0')}mm" # 降水量を追加
                
                tide_name = row.get('潮名', '-')
                tide_phase = row.get('潮位フェーズ', '-')
                tide_cm = f"{row.get('潮位_cm', '-')}cm" # 潮位(cm)を追加

                # --- 文字を大きくしたオーバーレイ HTML ---
                # font-sizeを 0.72rem -> 0.85rem など全体的にアップ
                # 魚種(fish_info)を 0.85rem -> 1.05rem にアップ
                overlay_html = f"""
                <a href="{map_url}" target="_blank" style="text-decoration: none; color: inherit;">
                    <div style="position: relative; width: 100%; margin-bottom: 20px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
                        <img src="{img_url}" style="width: 100%; aspect-ratio: 1/1; object-fit: cover; display: block;">
                        <div style="position: absolute; bottom: 0; width: 100%; padding: 10px; background: linear-gradient(transparent, rgba(0,0,0,0.95)); color: white; font-size: 0.85rem; line-height: 1.5;">
                            <b style="color: #00ffd0; font-size: 1.05rem;">{fish_info}</b><br>
                            📍 {place_name}<br>
                            📅 {display_dt}<br>
                            🌡️ {temp} / 💨 {wind} / ☔ {rain}<br>
                            🌊 {tide_name} ({tide_phase}) {tide_cm}
                        </div>
                    </div>
                </a>
                """
                st.markdown(overlay_html, unsafe_allow_html=True)
