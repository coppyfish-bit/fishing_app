import streamlit as st
import pandas as pd

def show_gallery_page(df):
    st.subheader("🖼️ 全釣果ギャラリー")
    st.caption("写真をタップするとGoogleマップを開きます")
    
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
    
    # 降順（新しい順）に並べ替え
    df_gallery = df_gallery.sort_values(
        by=['datetime_parsed', 'datetime_tmp'], 
        ascending=[False, False], 
        na_position='last'
    )

    # --- 2. 有効データの抽出 ---
    target_col = 'filename'
    if target_col not in df_gallery.columns:
        st.error(f"'{target_col}'列が見つかりません。")
        return

    valid_rows = df_gallery[
        df_gallery[target_col].notna() & 
        (df_gallery[target_col].astype(str).str.lower() != "nan")
    ]

    # --- 3. レスポンシブ・グリッド表示 (スマホ1列固定) ---
    # Streamlitのcolumnsを使わず、CSSで制御します
    st.markdown("""
        <style>
        .gallery-grid {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
            justify-content: flex-start;
        }
        .gallery-item {
            flex: 1 1 calc(33.333% - 15px); /* PCは3列 */
            box-sizing: border-box;
            min-width: 280px;
        }
        @media (max-width: 600px) {
            .gallery-item {
                flex: 1 1 100%; /* スマホは1列 */
            }
        }
        .card {
            position: relative;
            width: 100%;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 10px rgba(0,0,0,0.3);
            background: #1e1e1e;
        }
        .card img {
            width: 100%;
            aspect-ratio: 1/1;
            object-fit: cover;
            display: block;
        }
        .card-info {
            position: absolute;
            bottom: 0;
            width: 100%;
            padding: 10px;
            background: linear-gradient(transparent, rgba(0,0,0,0.95));
            color: white;
            font-size: 0.75rem;
            line-height: 1.4;
        }
        </style>
    """, unsafe_allow_html=True)

    # ギャラリー全体を囲むコンテナを開始
    gallery_html = '<div class="gallery-grid">'

    for _, row in valid_rows.iterrows():
        img_url = row.get(target_col)
        lat, lon = row.get('lat'), row.get('lon')
        map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}" if pd.notnull(lat) and lat != 0 else "#"
        
        dt_val = row.get('datetime_parsed')
        display_dt = dt_val.strftime('%Y-%m-%d %H:%M') if pd.notnull(dt_val) else str(row.get('datetime', '-'))[:16]
        
        fish_info = f"{row.get('魚種', '-')} {row.get('全長_cm', '-')}cm"
        place_name = row.get('場所', '-')
        tide_info = f"{row.get('潮名', '-')} ({row.get('潮位フェーズ', '-')})"
        env_info = f"🌡️ {row.get('気温', '-')}℃ / 💨 {row.get('風速', '-')}m"

        # 1枚ずつのカードをHTMLに追加
        gallery_html += f"""
        <div class="gallery-item">
            <a href="{map_url}" target="_blank" style="text-decoration: none; color: inherit;">
                <div class="card">
                    <img src="{img_url}">
                    <div class="card-info">
                        <b style="color: #00ffd0; font-size: 0.9rem;">{fish_info}</b><br>
                        📍 {place_name}<br>
                        📅 {display_dt}<br>
                        🌊 {tide_info}<br>
                        {env_info}
                    </div>
                </div>
            </a>
        </div>
        """

    gallery_html += '</div>' # コンテナを閉じる
    st.markdown(gallery_html, unsafe_allow_html=True)
