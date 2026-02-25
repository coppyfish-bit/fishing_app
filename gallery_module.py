import streamlit as st
import pandas as pd
from datetime import datetime, date

def show_gallery_page(df):
    st.subheader("🖼️ 全釣果ギャラリー")
    
    if df is None or df.empty:
        st.info("表示するデータがまだありません。")
        return

    df_gallery = df.copy()

    # --- 1. 前処理（ソート用日時の作成） ---
    def clean_datetime_str(x):
        if pd.isna(x): return x
        return str(x).replace("/", "-").strip()

    df_gallery['datetime_tmp'] = df_gallery['datetime'].apply(clean_datetime_str)
    df_gallery['datetime_parsed'] = pd.to_datetime(
        df_gallery['datetime_tmp'], 
        errors='coerce', 
        dayfirst=False
    )

    # --- 2. サイドバー・フィルター機能 ---
    st.sidebar.markdown("### 🔍 釣果を絞り込む")

    # 魚種で絞り込み
    fish_list = ["すべて"] + sorted(df_gallery['魚種'].unique().tolist())
    selected_fish = st.sidebar.selectbox("魚種を選択", fish_list)

    # 場所で絞り込み
    place_list = ["すべて"] + sorted(df_gallery['場所'].unique().tolist())
    selected_place = st.sidebar.selectbox("場所を選択", place_list)

    # 期間で絞り込み
    min_date = df_gallery['datetime_parsed'].min().date() if not df_gallery['datetime_parsed'].isna().all() else date(2024, 1, 1)
    max_date = date.today()
    
    date_range = st.sidebar.date_input(
        "期間を選択",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # --- 3. フィルタリングの実行 ---
    # 魚種
    if selected_fish != "すべて":
        df_gallery = df_gallery[df_gallery['魚種'] == selected_fish]
    
    # 場所
    if selected_place != "すべて":
        df_gallery = df_gallery[df_gallery['場所'] == selected_place]
    
    # 期間（date_rangeが開始と終了のペアである場合）
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        df_gallery = df_gallery[
            (df_gallery['datetime_parsed'].dt.date >= start_date) & 
            (df_gallery['datetime_parsed'].dt.date <= end_date)
        ]

    # 最新順に並べ替え
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

    if valid_rows.empty:
        st.warning("条件に一致する釣果がありません。")
        return

    st.write(f"検索結果: {len(valid_rows)} 件")

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
                display_dt = dt_val.strftime('%Y-%m-%d %H:%M') if pd.notnull(dt_val) else str(row.get('datetime', '-'))[:16]
                
                fish_info = f"{row.get('魚種', '-')} {row.get('全長_cm', '-')}cm"
                place_name = row.get('場所', '-')
                temp = f"{row.get('気温', '-')}℃"
                wind = f"{row.get('風向', '')}{row.get('風速', '-')}m"
                rain = f"{row.get('降水量', '0')}mm"
                
                tide_name = row.get('潮名', '-')
                tide_phase = row.get('潮位フェーズ', '-')
                tide_cm = f"{row.get('潮位_cm', '-')}cm"

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
