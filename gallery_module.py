import streamlit as st
import pandas as pd

def show_gallery_page(df):
    st.subheader("🖼️ 全釣果ギャラリー")
    st.caption("写真をタップするとGoogleマップを開きます")
    
    if df is None or df.empty:
        st.info("表示するデータがまだありません。")
        return

    df_gallery = df.copy()

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
    
    # 降順（新しい順）に並べ替え
    df_gallery = df_gallery.sort_values(
        by=['datetime_parsed', 'datetime_tmp'], 
        ascending=[False, False], 
        na_position='last'
    )

    # --- 2. カラム名チェックとデータの絞り込み ---
    # 'filename' 列がない場合のエラー回避
    target_col = 'filename'
    if target_col not in df_gallery.columns:
        st.error(f"スプレッドシートに '{target_col}' 列が見つかりません。")
        return

    # 有効な画像があるデータのみ抽出
    valid_rows = df_gallery[
        df_gallery[target_col].notna() & 
        (df_gallery[target_col].astype(str).str.lower() != "nan") &
        (df_gallery[target_col].astype(str) != "")
    ]

    if valid_rows.empty:
        st.warning("表示できる写真がありません。")
        return

    # --- 3. グリッド表示 (スマホの順番崩れ対策) ---
    # スマホで「1→2→3」と縦に並ぶように、1つのコンテナに順次配置します
    
    # PC表示用のカラム作成
    cols = st.columns(3)
    
    for i, (idx, row) in enumerate(valid_rows.iterrows()):
        # ここが重要：i % 3 で列を順番に入れ替えることで
        # PCでは横並び、スマホでは上から順に「1, 2, 3...」と表示されます
        with cols[i % 3]:
            img_url = row.get(target_col)
            lat = row.get('lat')
            lon = row.get('lon')
            
            # Google Maps URLの作成
            if pd.notnull(lat) and lat != 0:
                map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
            else:
                map_url = "#"

            # 日時表示の整形
            dt_val = row.get('datetime_parsed')
            display_dt = dt_val.strftime('%Y-%m-%d %H:%M') if pd.notnull(dt_val) else str(row.get('datetime', '-'))[:16]
            
            # 各種情報の取得
            fish_info = f"{row.get('魚種', '-')} {row.get('全長_cm', '-')}cm"
            place_name = row.get('場所', '-')
            tide_info = f"{row.get('潮名', '-')} ({row.get('潮位フェーズ', '-')})"
            env_info = f"🌡️ {row.get('気温', '-')}℃ / 💨 {row.get('風速', '-')}m"

            # HTMLによるカード表示
            card_html = f"""
            <a href="{map_url}" target="_blank" style="text-decoration: none; color: inherit;">
                <div style="position: relative; width: 100%; margin-bottom: 15px; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.2); background: #1e1e1e;">
                    <img src="{img_url}" style="width: 100%; aspect-ratio: 1/1; object-fit: cover; display: block;">
                    <div style="position: absolute; bottom: 0; width: 100%; padding: 6px; background: linear-gradient(transparent, rgba(0,0,0,0.9)); color: white; font-size: 0.7rem; line-height: 1.3;">
                        <b style="color: #00ffd0; font-size: 0.8rem;">{fish_info}</b><br>
                        📍 {place_name}<br>
                        📅 {display_dt}<br>
                        🌊 {tide_info}<br>
                        {env_info}
                    </div>
                </div>
            </a>
            """
            st.markdown(card_html, unsafe_allow_html=True)
