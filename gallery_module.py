import streamlit as st
import pandas as pd

def show_gallery_page(df):
    st.subheader("🖼️ 全釣果ギャラリー")
    
    if df is None or df.empty:
        st.info("表示するデータがまだありません。")
        return

    df_gallery = df.copy()

    # --- 1. ソート処理 ---
    def clean_datetime_str(x):
        if pd.isna(x): return x
        return str(x).replace("/", "-").strip()

    df_gallery['datetime_tmp'] = df_gallery['datetime'].apply(clean_datetime_str)
    df_gallery['datetime_parsed'] = pd.to_datetime(
        df_gallery['datetime_tmp'], 
        errors='coerce', 
        dayfirst=False
    )
    
    # 降順（新しい順）
    df_gallery = df_gallery.sort_values(
        by=['datetime_parsed', 'datetime_tmp'], 
        ascending=[False, False], 
        na_position='last'
    )

    # 有効な画像データの抽出
    valid_rows = df_gallery[df_gallery['filename'].notna() & (df_gallery['filename'].astype(str).lower() != "nan")]

    # --- 2. 1行（3つ）ずつ処理してスマホの順序を強制 ---
    # データを3つずつの塊（チャンク）に分けます
    chunks = [valid_rows.iloc[i:i+3] for i in range(0, len(valid_rows), 3)]

    for chunk in chunks:
        cols = st.columns(3)
        for i, (_, row) in enumerate(chunk.iterrows()):
            with cols[i]:
                img_url = row.get('filename')
                lat, lon = row.get('lat'), row.get('lon')
                map_url = f"https://www.google.com/maps?q={lat},{lon}" if pd.notnull(lat) and lat != 0 else "#"
                
                dt_val = row.get('datetime_parsed')
                display_dt = dt_val.strftime('%Y-%m-%d %H:%M') if pd.notnull(dt_val) else str(row.get('datetime', '-'))[:16]
                
                fish_info = f"{row.get('魚種', '-')} {row.get('全長_cm', '-')}cm"
                place_name = row.get('場所', '-')
                tide_info = f"{row.get('潮名', '-')} ({row.get('潮位フェーズ', '-')})"
                env_info = f"🌡️ {row.get('気温', '-')}℃ / 💨 {row.get('風速', '-')}m"

                # 個別のカードHTML
                card_html = f"""
                <a href="{map_url}" target="_blank" style="text-decoration: none; color: inherit;">
                    <div style="position: relative; width: 100%; margin-bottom: 20px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.3); background: #1e1e1e;">
                        <img src="{img_url}" style="width: 100%; aspect-ratio: 1/1; object-fit: cover; display: block;">
                        <div style="position: absolute; bottom: 0; width: 100%; padding: 8px; background: linear-gradient(transparent, rgba(0,0,0,0.95)); color: white; font-size: 0.72rem; line-height: 1.4;">
                            <b style="color: #00ffd0; font-size: 0.85rem;">{fish_info}</b><br>
                            📍 {place_name}<br>
                            📅 {display_dt}<br>
                            🌊 {tide_info}<br>
                            {env_info}
                        </div>
                    </div>
                </a>
                """
                st.markdown(card_html, unsafe_allow_html=True)
