import streamlit as st
import pandas as pd
from datetime import datetime, date
import time

def show_gallery_page(df):
    # --- 1. スタイル設定（CSS） ---
    st.markdown("""
        <style>
        .stExpander {
            border: none !important;
            background-color: #1e2630 !important;
            border-radius: 15px !important;
            margin-bottom: 20px !important;
        }
        .result-count {
            color: #00ffd0;
            font-size: 0.9rem;
            font-weight: bold;
            letter-spacing: 0.1rem;
            margin-bottom: 15px;
            text-transform: uppercase;
        }
        .fish-card {
            position: relative;
            width: 100%;
            margin-bottom: 25px;
            border-radius: 20px;
            overflow: hidden;
            background: #0e1117;
            box-shadow: 0 10px 25px rgba(0,0,0,0.6);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        .fish-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 15px 35px rgba(0, 255, 208, 0.2);
        }
        .fish-img {
            width: 100%;
            aspect-ratio: 1/1;
            object-fit: cover;
            display: block;
            mask-image: linear-gradient(to bottom, black 65%, transparent 100%);
            -webkit-mask-image: linear-gradient(to bottom, black 65%, transparent 100%);
        }
        .overlay-content {
            position: absolute;
            bottom: 0;
            width: 100%;
            padding: 18px;
            background: linear-gradient(to top, rgba(0,0,0,1) 0%, rgba(0,0,0,0.8) 60%, transparent 100%);
            color: #ffffff;
        }
        .fish-title {
            color: #00ffd0;
            font-size: 1.25rem;
            font-weight: 900;
            margin-bottom: 6px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.8);
        }
        .info-row {
            display: flex;
            align-items: center;
            gap: 10px;
            font-size: 0.88rem;
            margin-bottom: 4px;
            color: #cccccc;
        }
        .tide-badge {
            display: inline-block;
            background: linear-gradient(90deg, rgba(0, 255, 208, 0.2), rgba(0, 200, 255, 0.2));
            color: #00ffd0;
            padding: 4px 12px;
            border-radius: 8px;
            font-size: 0.8rem;
            font-weight: bold;
            margin-top: 8px;
            border: 1px solid rgba(0, 255, 208, 0.3);
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🖼️ GALLERY")

    # --- 👿 修正ポイント：最新データ更新ボタン ---
    if st.button("🔄 最新データに更新 (キャッシュ破棄)"):
        # 全てのキャッシュをクリアし、最新のスプレッドシートを読み直す
        st.cache_data.clear()
        st.success("深淵の記憶を更新した。最新の釣果が表示されるはずだ。")
        time.sleep(1) # 成功メッセージを見せるための僅かな猶予
        st.rerun()
    
    if df is None or df.empty:
        st.info("No records found.")
        return

    df_gallery = df.copy()

    # --- 2. 前処理 ---
    def clean_datetime_str(x):
        if pd.isna(x): return x
        return str(x).replace("/", "-").strip()

    df_gallery['datetime_tmp'] = df_gallery['datetime'].apply(clean_datetime_str)
    df_gallery['datetime_parsed'] = pd.to_datetime(df_gallery['datetime_tmp'], errors='coerce')
    # 解析に失敗した行（空欄など）を念のため除外または補完
    df_gallery = df_gallery.dropna(subset=['datetime_parsed'])

# --- 3. 検索パネル ---
    with st.expander("🔍 Filter", expanded=False):
        col_f, col_p = st.columns(2)
        fish_list = ["すべて"] + sorted(df_gallery['魚種'].unique().tolist())
        selected_fish = col_f.selectbox("🐟 SPECIES", fish_list)
        place_list = ["すべて"] + sorted(df_gallery['場所'].unique().tolist())
        selected_place = col_p.selectbox("📍 FIELD", place_list)

        # 修正：今日の日付を基準に、データがなければ1年前をデフォルトにする
        absolute_min = df_gallery['datetime_parsed'].min().date() if not df_gallery.empty else date(2024, 1, 1)
        
        # date_input の初期値を (最小日, 今日の23:59まで含むイメージ) に設定
        # 登録直後のデータが「今日」の場合、これなら確実に入る
        date_range = st.date_input(
            "📅 DATE RANGE", 
            value=(absolute_min, date.today()), 
            min_value=absolute_min, 
            max_value=date.today()
        )

    # --- フィルタリング ---
    if selected_fish != "すべて":
        df_gallery = df_gallery[df_gallery['魚種'] == selected_fish]
    if selected_place != "すべて":
        df_gallery = df_gallery[df_gallery['場所'] == selected_place]
    
    # 修正：date_range がちゃんと2つ（開始と終了）選ばれている時だけ絞り込む
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date, end_date = date_range
        df_gallery = df_gallery[
            (df_gallery['datetime_parsed'].dt.date >= start_date) & 
            (df_gallery['datetime_parsed'].dt.date <= end_date)
        ]

    df_gallery = df_gallery.sort_values(by=['datetime_parsed', 'datetime_tmp'], ascending=[False, False])
    valid_rows = df_gallery[df_gallery['filename'].notna() & (df_gallery['filename'].astype(str).str.lower() != "nan")]

    if valid_rows.empty:
        st.warning("No records match your criteria.")
        return

    st.markdown(f'<p class="result-count">Showing {len(valid_rows)} captures</p>', unsafe_allow_html=True)

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
                
                # データの準備
                fish_info = f"{row.get('魚種', '-')} / {row.get('全長_cm', '-')}cm"
                # 風向と風速を合体
                wind_info = f"{row.get('風向', '')} {row.get('風速', '-')}m"
                weather_info = f"🌡️ {row.get('気温', '-')}℃ / ☔ {row.get('降水量', '0')}mm / 💨 {wind_info}"
                tide_cm = f"{row.get('潮位_cm', '-')}cm"

                # デザインHTML
                card_html = f"""
                <a href="{map_url}" target="_blank" style="text-decoration: none;">
                    <div class="fish-card">
                        <img src="{img_url}" class="fish-img">
                        <div class="overlay-content">
                            <div class="fish-title">{fish_info}</div>
                            <div class="info-row">📍 {row.get('場所', '-')}</div>
                            <div class="info-row">📅 {display_dt}</div>
                            <div class="info-row" style="font-size: 0.8rem;">{weather_info}</div>
                            <div class="tide-badge">🌊 {row.get('潮名', '-')} ({row.get('潮位フェーズ', '-')}) {tide_cm}</div>
                        </div>
                    </div>
                </a>
                """
                st.markdown(card_html, unsafe_allow_html=True)




