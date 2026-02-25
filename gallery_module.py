import streamlit as st
import pandas as pd

def show_gallery_page(df):
    st.subheader("🖼️ 全釣果ギャラリー（写真をタップすると地図を表示）")
    
    if df is None or df.empty:
        st.info("表示するデータがまだありません。")
        return

    df_gallery = df.copy()

    # --- 1. 日時のソート処理 ---
    def clean_datetime_str(x):
        if pd.isna(x): return x
        return str(x).replace("/", "-").strip()

    df_gallery['datetime_tmp'] = df_gallery['datetime'].apply(clean_datetime_str)

    # 複数のフォーマットを自動推論して変換
    df_gallery['datetime_parsed'] = pd.to_datetime(
        df_gallery['datetime_tmp'], 
        errors='coerce', 
        dayfirst=False
    )
    
    # 降順（新しい順）にソート
    df_gallery = df_gallery.sort_values(
        by=['datetime_parsed', 'datetime_tmp'], 
        ascending=[False, False], 
        na_position='last'
    )

    # 有効な画像（filenameがあるもの）だけに絞り込み
    valid_rows = df_gallery[
        df_gallery['filename'].notna() & 
        (df_gallery['filename'].astype(str).lower() != "nan") &
        (df_gallery['filename'].astype(str) != "")
    ]

    # --- 2. グリッド表示 (1行ずつ columns を作成してスマホの順序を死守) ---
    # データを3つずつの塊（チャンク）に分ける
    for i in range(0, len(valid_rows), 3):
        chunk = valid_rows.iloc[i : i + 3]
        cols = st.columns(3) # 1行ごとに3列作成
        
        for j, (_, row) in enumerate(chunk.iterrows()):
            with cols[j]:
                img_url = row.get("filename")
                lat = row.get('lat')
                lon = row.get('lon')
                
                # Google Maps URL
                map_url = f"https://www.google.com/maps?q={lat},{lon}" if pd.notnull(lat) and lat != 0 else "#"

                # 表示用日時の整形
                dt_val = row.get('datetime_parsed')
                if pd.notnull(dt_val):
                    display_dt = dt_val.strftime('%Y-%m-%d %H:%M')
                else:
                    display_dt = str(row.get('datetime', '-'))[:16]
                
                # 最初にご提示いただいたデザイン変数をセット
                temp = f"{row.get('気温', '-')}℃"
                wind = f"{row.get('風向', '')}{row.get('風速', '-')}m"
                tide_name = row.get('潮名', '-')
                tide_phase = row.get('潮位フェーズ', '-')
                place_name = row.get('場所', '-')
                fish_info = f"{row.get('魚種', '-')} {row.get('全長_cm', '-')}cm"

                # --- 最初のオーバーレイ HTML ---
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
