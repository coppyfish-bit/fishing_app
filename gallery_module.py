import streamlit as st
import pandas as pd

def show_gallery_page(df):
    st.subheader("🖼️ 精密データオーバーレイ")
    
    if df.empty:
        st.info("表示するデータがまだありません。")
        return

    # --- 魚種リストの動的生成（ここを修正） ---
    # df["魚種"] から最新のリストを取得し、欠損値を除去してソートします
    available_species = df["魚種"].dropna().unique().tolist()
    fish_list = ["すべて"] + sorted([str(s) for s in available_species])
    
    # ユーザーが選択した魚種をセッションで保持（リロード対策）
    selected_fish = st.selectbox("🐟 魚種で絞り込み", fish_list, key="gallery_fish_filter")

    df_gallery = df.copy()
    # datetimeの変換を確実に行う
    df_gallery['datetime'] = pd.to_datetime(df_gallery['datetime'], errors='coerce')
    
    # フィルタリング
    if selected_fish != "すべて":
        df_gallery = df_gallery[df_gallery["魚種"] == selected_fish]

    # 最新順に並び替え
    df_gallery = df_gallery.sort_values("datetime", ascending=False)

    if df_gallery.empty:
        st.warning(f"「{selected_fish}」のデータは見つかりませんでした。")
        return

    # --- ギャラリー表示 ---
    cols = st.columns(3)
    
    for i, (idx, row) in enumerate(df_gallery.iterrows()):
        img_url = row.get("filename")
        if not img_url or pd.isna(img_url): continue
        
        # Google Drive URLの変換処理
        display_url = str(img_url)
        if "drive.google.com" in display_url:
            try:
                if "/d/" in display_url:
                    file_id = display_url.split('/d/')[1].split('/')[0]
                else:
                    file_id = display_url.split('id=')[1].split('&')[0]
                display_url = f"https://drive.google.com/uc?id={file_id}"
            except:
                pass

        with cols[i % 3]:
            try:
                dt_str = row['datetime'].strftime('%y/%m/%d %H:%M') if pd.notnull(row['datetime']) else "-"
                fish_name = row.get('魚種', '-')
                size = row.get('全長_cm', '-')
                place = row.get('場所', '-')
                tide_name = row.get('潮名', '-')
                tide_phase = row.get('潮位フェーズ', '-')
                temp = row.get('気温', '-')
                wind_d = row.get('風向', '-')
                wind_s = row.get('風速', '-')
                lat = row.get('lat', 0)
                lon = row.get('lon', 0)

                map_url = f"https://www.google.com/maps?q={lat},{lon}"

                overlay_html = f"""
                <a href="{map_url}" target="_blank" style="text-decoration: none; color: inherit;">
                    <div style="position: relative; width: 100%; margin-bottom: 20px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.3);">
                        <img src="{display_url}" style="width: 100%; aspect-ratio: 1/1; object-fit: cover; display: block;">
                        <div style="position: absolute; bottom: 0; width: 100%; padding: 12px 10px; background: linear-gradient(transparent, rgba(0,0,0,0.5) 20%, rgba(0,0,0,0.95)); color: white; line-height: 1.5;">
                            <b style="color: #00ffd0; font-size: 1.1rem; display: block; margin-bottom: 2px;">{fish_name} {size}cm</b>
                            <span style="font-size: 0.85rem;">
                                🕒 {dt_str}<br>
                                📍 {place}<br>
                                🌊 {tide_name} ({tide_phase})<br>
                                🚩 {temp}℃ / {wind_d} {wind_s}m/s
                            </span>
                        </div>
                    </div>
                </a>"""
                st.markdown(overlay_html, unsafe_allow_html=True)
                
            except Exception as e:
                st.image(display_url, caption=f"{row.get('魚種','-')}")
