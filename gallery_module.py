import streamlit as st
import pandas as pd
from datetime import datetime, date

def show_gallery_page(df):
    # --- 1. スタイル設定（ポップアップ用のCSSを追加） ---
    st.markdown("""
        <style>
        .stExpander { border: none !important; background-color: #1e2630 !important; border-radius: 15px !important; }
        .result-count { color: #00ffd0; font-size: 0.9rem; font-weight: bold; letter-spacing: 0.1rem; text-transform: uppercase; }
        
        /* カードデザイン */
        .fish-card {
            position: relative;
            width: 100%;
            margin-bottom: 25px;
            border-radius: 20px;
            overflow: hidden;
            background: #0e1117;
            box-shadow: 0 10px 25px rgba(0,0,0,0.6);
            cursor: pointer;
            transition: transform 0.3s ease;
        }
        .fish-card:hover { transform: translateY(-8px); }
        .fish-img {
            width: 100%;
            aspect-ratio: 1/1;
            object-fit: cover;
            display: block;
            mask-image: linear-gradient(to bottom, black 65%, transparent 100%);
            -webkit-mask-image: linear-gradient(to bottom, black 65%, transparent 100%);
        }
        .overlay-content {
            position: absolute; bottom: 0; width: 100%; padding: 18px;
            background: linear-gradient(to top, rgba(0,0,0,1) 0%, rgba(0,0,0,0.8) 60%, transparent 100%);
            color: #ffffff;
        }
        .fish-title { color: #00ffd0; font-size: 1.25rem; font-weight: 900; margin-bottom: 6px; }
        .tide-badge {
            display: inline-block; background: rgba(0, 255, 208, 0.15); color: #00ffd0;
            padding: 4px 12px; border-radius: 8px; font-size: 0.8rem; font-weight: bold;
            border: 1px solid rgba(0, 255, 208, 0.3);
        }

        /* 詳細ポップアップ（Expanderをボタン風に見せる） */
        .details-btn {
            background: #00ffd0; color: #000; padding: 10px; border-radius: 10px;
            text-align: center; font-weight: bold; margin-top: 10px; display: block;
            text-decoration: none;
        }
        .memo-box {
            background: rgba(255,255,255,0.05); border-left: 3px solid #00ffd0;
            padding: 10px; margin-top: 10px; font-size: 0.9rem; color: #eee;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🖼️ PHOTO GALLERY")
    
    # (前略：データ処理・フィルタリング部分は前回と同じ)
    df_gallery = df.copy()
    def clean_datetime_str(x):
        if pd.isna(x): return x
        return str(x).replace("/", "-").strip()
    df_gallery['datetime_tmp'] = df_gallery['datetime'].apply(clean_datetime_str)
    df_gallery['datetime_parsed'] = pd.to_datetime(df_gallery['datetime_tmp'], errors='coerce')

    # 検索パネル
    with st.expander("🔍 FILTERING RECORDS", expanded=False):
        col_f, col_p = st.columns(2)
        fish_list = ["すべて"] + sorted(df_gallery['魚種'].unique().tolist())
        selected_fish = col_f.selectbox("🐟 SPECIES", fish_list)
        place_list = ["すべて"] + sorted(df_gallery['場所'].unique().tolist())
        selected_place = col_p.selectbox("📍 FIELD", place_list)
        date_range = st.date_input("📅 DATE RANGE", value=(df_gallery['datetime_parsed'].min().date(), date.today()))

    if selected_fish != "すべて": df_gallery = df_gallery[df_gallery['魚種'] == selected_fish]
    if selected_place != "すべて": df_gallery = df_gallery[df_gallery['場所'] == selected_place]
    
    df_gallery = df_gallery.sort_values(by=['datetime_parsed', 'datetime_tmp'], ascending=[False, False])
    valid_rows = df_gallery[df_gallery['filename'].notna()]

    st.markdown(f'<p class="result-count">Showing {len(valid_rows)} captures</p>', unsafe_allow_html=True)

    # --- 2. グリッド表示とポップアップの仕掛け ---
    for i in range(0, len(valid_rows), 3):
        chunk = valid_rows.iloc[i : i + 3]
        cols = st.columns(3) 
        for j, (_, row) in enumerate(chunk.iterrows()):
            with cols[j]:
                img_url = row.get("filename")
                lat, lon = row.get('lat'), row.get('lon')
                map_url = f"https://www.google.com/maps?q={lat},{lon}" if pd.notnull(lat) else "#"
                
                fish_info = f"{row.get('魚種', '-')} / {row.get('全長_cm', '-')}cm"
                memo_text = row.get('備考', 'メモなし')
                
                # --- [仕掛け] st.popover を使って詳細表示 ---
                with st.popover(f"🔍 {fish_info}", use_container_width=True):
                    # 大きな画像を表示
                    st.image(img_url, use_container_width=True)
                    
                    # 詳細ステータス
                    st.markdown(f"### {fish_info}")
                    st.markdown(f"**📍 場所:** {row.get('場所', '-')}")
                    st.markdown(f"**📅 日時:** {row.get('datetime', '-')}")
                    
                    col1, col2 = st.columns(2)
                    col1.metric("気温", f"{row.get('気温', '-')}℃")
                    col1.metric("風速", f"{row.get('風速', '-')}m ({row.get('風向', '')})")
                    col2.metric("潮位", f"{row.get('潮位_cm', '-')}cm")
                    col2.metric("降水", f"{row.get('降水量', '0')}mm")
                    
                    st.markdown(f"**🌊 潮汐:** {row.get('潮名', '-')} ({row.get('潮位フェーズ', '-')})")
                    
                    # 備考メモ
                    st.info(f"📝 **MEMO:**\n\n{memo_text}")
                    
                    # 地図ボタン
                    st.link_button("🌐 Googleマップで場所を確認", map_url, use_container_width=True)

                # --- ギャラリーの見た目（カード） ---
                st.markdown(f"""
                    <div class="fish-card">
                        <img src="{img_url}" class="fish-img">
                        <div class="overlay-content">
                            <div class="fish-title">{fish_info}</div>
                            <div class="info-row">📍 {row.get('場所', '-')}</div>
                            <div class="tide-badge">🌊 {row.get('潮名', '-')}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
