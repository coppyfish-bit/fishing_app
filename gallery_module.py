import streamlit as st
import pandas as pd

def show_gallery_page(df):
    st.subheader("🖼️ 全釣果ギャラリー（写真をタップすると地図を表示）")
    
    if df is None or df.empty:
        st.info("表示するデータがまだありません。")
        return

    df_gallery = df.copy()

    # --- 【最強ソート処理】 ---
    # 1. 念のため全角数字や記号を半角に、スラッシュをハイフンに統一
    def clean_datetime_str(x):
        if pd.isna(x): return x
        return str(x).replace("/", "-").strip()

    df_gallery['datetime_tmp'] = df_gallery['datetime'].apply(clean_datetime_str)

    # 2. 複数のフォーマットを自動推論して変換 (dayfirst=False で日本形式に固定)
    # これにより「秒あり/なし」「/区切り/-区切り」が混在しても日付として認識されます
    df_gallery['datetime_parsed'] = pd.to_datetime(
        df_gallery['datetime_tmp'], 
        errors='coerce', 
        dayfirst=False
    )
    
    # 3. 万が一、変換失敗(NaT)したデータがあれば、元の文字列でソートを補完する
    # 新しいデータが「2026-02-17」なら、文字列比較でも「2026-02-10」より前（降順なら上）に来るはずです
    df_gallery = df_gallery.sort_values(
        by=['datetime_parsed', 'datetime_tmp'], 
        ascending=[False, False], 
        na_position='last'
    )
    # -----------------------

    cols = st.columns(3)
    display_count = 0
    
    for i, (idx, row) in enumerate(df_gallery.iterrows()):
        img_url = row.get("filename")
        if not img_url or pd.isna(img_url) or str(img_url).lower() == "nan":
            continue
        
        lat = row.get('lat')
        lon = row.get('lon')
        map_url = f"https://www.google.com/maps?q={lat},{lon}" if pd.notnull(lat) and lat != 0 else "#"

        with cols[display_count % 3]:
            # 表示用日時のフォーマットを「分」までで統一
            dt_val = row.get('datetime_parsed')
            if pd.notnull(dt_val):
                display_dt = dt_val.strftime('%Y-%m-%d %H:%M')
            else:
                # 解析失敗時は元の文字を出す
                display_dt = str(row.get('datetime', '-'))[:16]
            
            temp = f"{row.get('気温', '-')}℃"
            wind = f"{row.get('風向', '')}{row.get('風速', '-')}m"
            tide_name = row.get('潮名', '-')
            tide_phase = row.get('潮位フェーズ', '-')
            place_name = row.get('場所', '-')
            fish_info = f"{row.get('魚種', '-')} {row.get('全長_cm', '-')}cm"

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
