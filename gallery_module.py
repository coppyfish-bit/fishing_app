import streamlit as st
import pandas as pd
from datetime import datetime, date

def show_gallery_page(df):
    # --- 1. 全体のスタイル設定（CSS） ---
    st.markdown("""
        <style>
        /* 検索パネルの見た目をカスタム */
        .stExpander {
            border: none !important;
            background-color: #1e2630 !important;
            border-radius: 15px !important;
            margin-bottom: 20px !important;
        }
        /* 検索結果のカウント表示 */
        .result-count {
            color: #00ffd0;
            font-size: 0.9rem;
            font-weight: bold;
            letter-spacing: 0.1rem;
            margin-bottom: 15px;
            text-transform: uppercase;
        }
        /* カード全体のデザイン */
        .fish-card {
            position: relative;
            width: 100%;
            margin-bottom: 25px;
            border-radius: 20px;
            overflow: hidden;
            background: #0e1117;
            box-shadow: 0 10px 20px rgba(0,0,0,0.5);
            transition: transform 0.3s ease;
        }
        .fish-card:hover {
            transform: translateY(-5px);
        }
        /* 画像のスタイリング */
        .fish-img {
            width: 100%;
            aspect-ratio: 1/1;
            object-fit: cover;
            display: block;
            mask-image: linear-gradient(to bottom, black 70%, transparent 100%);
            -webkit-mask-image: linear-gradient(to bottom, black 70%, transparent 100%);
        }
        /* テキストエリアのスタイリング */
        .overlay-content {
            position: absolute;
            bottom: 0;
            width: 100%;
            padding: 15px;
            background: linear-gradient(to top, rgba(0,0,0,0.95) 0%, rgba(0,0,0,0.7) 70%, transparent 100%);
            color: #e0e0e0;
        }
        .fish-title {
            color: #00ffd0;
            font-size: 1.2rem;
            font-weight: 800;
            margin-bottom: 4px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.5);
        }
        .info-row {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.85rem;
            margin-bottom: 3px;
            opacity: 0.9;
        }
        .tide-badge {
            display: inline-block;
            background: rgba(0, 255, 208, 0.15);
            color: #00ffd0;
            padding: 2px 8px;
            border-radius: 5px;
            font-size: 0.75rem;
            font-weight: bold;
            margin-top: 5px;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🖼️ PHOTO GALLERY")
    
    if df is None or df.empty:
        st.info("表示するデータがまだありません。")
        return

    df_gallery = df.copy()

    # --- 2. 前処理（ソート用日時の作成） ---
    def clean_datetime_str(x):
        if pd.isna(x): return x
        return str(x).replace("/", "-").strip()

    df_gallery['datetime_tmp'] = df_gallery['datetime'].apply(clean_datetime_str)
    df_gallery['datetime_parsed'] = pd.to_datetime(df_gallery['datetime_tmp'], errors='coerce', dayfirst=False)

    # --- 3. 検索パネル (メイン画面内) ---
    with st.expander("🔍 FILTERING RECORDS", expanded=False):
        col_f, col_p = st.columns(2)
        fish_list = ["すべて"] + sorted(df_gallery['魚種'].unique().tolist())
        selected_fish = col_f.selectbox("🐟 SPECIES", fish_list)
        place_list = ["すべて"] + sorted(df_gallery['場所'].unique().tolist())
        selected_place = col_p.selectbox("📍 FIELD", place_list)

        min_date = df_gallery['datetime_parsed'].min().date() if not df_gallery['datetime_parsed'].isna().all() else date(2024, 1, 1)
        date_range = st.date_input("📅 DATE RANGE", value=(min_date, date.today()), min_value=min_date, max_value=date.today())

    # フィルタリング実行
    if selected_fish != "すべて":
        df_gallery = df_gallery[df_gallery['魚種'] == selected_fish]
    if selected_place != "すべて":
        df_gallery = df_gallery[df_gallery['場所'] == selected_place]
    if isinstance(date_range, tuple) and len(date_range) == 2:
        df_gallery = df_gallery[(df_gallery['datetime_parsed'].dt.date >= date_range[0]) & (df_gallery['datetime_parsed'].dt.date <= date_range[1])]

    df_gallery = df_gallery.sort_values(by=['datetime_parsed', 'datetime_tmp'], ascending=[False, False])
    valid_rows = df_gallery[df_gallery['filename'].notna() & (df_gallery['filename'].astype(str).str.lower() != "nan")]

    if valid_rows.empty:
        st.warning("No records found.")
        return

    st.markdown(f'<p class="result-count">Found {len(valid_rows)} records</p>', unsafe_allow_html=True)

    # --- 4. グリッド表示 ---
    for i in range(0, len(valid_rows), 3):
        chunk = valid_rows.iloc[i : i + 3]
        cols = st.columns(3) 
        for j, (_, row) in enumerate(chunk.iterrows()):
            with cols[j]:
                img_url = row.get("filename")
                lat, lon = row.get('lat'), row.get('lon')
                map_url = f"https://www.google.com/maps?q={lat},{lon}" if pd.notnull(lat) and lat != 0 else "#"
                dt_val = row.get('datetime_parsed')
                display_dt = dt_val.strftime('%Y.%m.%d %H:%M') if pd.notnull(dt_val) else str(row.get('datetime', '-'))[:16]
                
                fish_info = f"{row.get('魚種', '-')} / {row.get('全長_cm', '-')}cm"
                tide_cm = f"{row.get('潮位_cm', '-')}cm"

                # 高級感のあるオーバーレイHTML
                card_html = f"""
                <a href="{map_url}" target="_blank" style="text-decoration: none;">
                    <div class="fish-card">
                        <img src="{img_url}" class="fish-img">
                        <div class="overlay-content">
                            <div class="fish-title">{fish_info}</div>
                            <div class="info-row">📍 {row.get('場所', '-')}</div>
                            <div class="info-row">📅 {display_dt}</div>
                            <div class="info-row">🌡️ {row.get('気温', '-')}℃ / ☔ {row.get('降水量', '0')}mm / 💨 {row.get('風速', '-')}m</div>
                            <div class="tide-badge">🌊 {row.get('潮名', '-')} ({row.get('潮位フェーズ', '-')}) {tide_cm}</div>
                        </div>
                    </div>
                </a>
                """
                st.markdown(card_html, unsafe_allow_html=True)
