import streamlit as st
import pandas as pd

def show_gallery_page(df):
    st.subheader("🖼️ 全釣果ギャラリー（写真をタップして地図表示）")
    
    if df is None or df.empty:
        st.info("表示するデータがまだありません。")
        return

    df_gallery = df.copy()

    # --- 【最強ソート処理】 ---
    def clean_datetime_str(x):
        if pd.isna(x): return x
        return str(x).replace("/", "-").strip()

    df_gallery['datetime_tmp'] = df_gallery['datetime'].apply(clean_datetime_str)
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

    # --- 【スマホ対応のグリッド表示】 ---
    # st.columnsの中に直接書くのではなく、1行(Row)ごとにデータを配置します
    # スマホ等の狭い画面では、1列または2列に自動で調整されるように設定
    
    # PCは3列、スマホを考慮して1列ずつ順番に並べるロジック
    # display_countを使って、3列の箱に順番に入れていく
    grid_cols = st.columns(3)
    
    # フィルタリング後の有効なデータのみ抽出
    valid_rows = df_gallery[df_gallery['filename'].notna() & (df_gallery['filename'].astype(str).lower() != "nan")]

    for i, (idx, row) in enumerate(valid_rows.iterrows()):
        # 順番通りに並べるための魔法：
        # スマホでの「縦積み」を防ぐため、1つずつ列を選択して配置する
        with grid_cols[i % 3]:
            img_url = row.get("filename")
            lat = row.get('lat')
            lon = row.get('lon')
            map_url = f"https://www.google.com/maps?q={lat},{lon}" if pd.notnull(lat) and lat != 0 else "#"

            # 表示用日時のフォーマット
            dt_val = row.get('datetime_parsed')
            display_dt = dt_val.strftime('%Y-%m-%d %H:%M') if pd.notnull(dt_val) else str(row.get('datetime', '-'))[:16]
            
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
