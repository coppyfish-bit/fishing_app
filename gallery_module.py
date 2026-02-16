import streamlit as st
import pandas as pd

def show_gallery_page(df):
    st.subheader("🖼️ 精密データオーバーレイ")
    
    if df.empty:
        st.info("表示するデータがまだありません。")
        return

    # --- フィルター機能 ---
    fish_list = ["すべて"] + sorted(df["魚種"].unique().tolist())
    selected_fish = st.selectbox("🐟 魚種で絞り込み", fish_list)

    df_gallery = df.copy()
    # datetime型に変換（エラーはNaTにする）
    df_gallery['datetime'] = pd.to_datetime(df_gallery['datetime'], errors='coerce')
    
    if selected_fish != "すべて":
        df_gallery = df_gallery[df_gallery["魚種"] == selected_fish]

    # 最新順に並び替え
    df_gallery = df_gallery.sort_values("datetime", ascending=False)

    # --- ギャラリー表示 ---
    cols = st.columns(3)
    
    for i, (idx, row) in enumerate(df_gallery.iterrows()):
        img_url = row.get("filename")
        if not img_url or pd.isna(img_url): continue
        
        with cols[i % 3]:
            try:
                # 教えていただいたカラム名に完全一致させて取得
                dt_str = row['datetime'].strftime('%y/%m/%d %H:%M') if pd.notnull(row['datetime']) else "-"
                fish_name = row.get('魚種', '-')
                size = row.get('全長_cm', '-')
                place = row.get('場所', '-')
                
                # 潮汐情報
                tide_name = row.get('潮名', '-')
                tide_phase = row.get('潮位フェーズ', '-')
                
                # 気象情報
                temp = row.get('気温', '-')
                wind_d = row.get('風向', '-')
                wind_s = row.get('風速', '-')
                
                # 位置情報
                lat = row.get('lat', 0)
                lon = row.get('lon', 0)

                # Googleマップのリンク（緯度,経度の順）
                map_url = f"https://www.google.com/maps?q={lat},{lon}"

                # HTMLオーバーレイ表示
                overlay_html = f"""
                <a href="{map_url}" target="_blank" style="text-decoration: none; color: inherit;">
                    <div style="position: relative; width: 100%; margin-bottom: 20px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.3); transition: transform 0.2s;">
                        <img src="{img_url}" style="width: 100%; aspect-ratio: 1/1; object-fit: cover; display: block;">
                        <div style="position: absolute; bottom: 0; width: 100%; padding: 10px; background: linear-gradient(transparent, rgba(0,0,0,0.9)); color: white; font-size: 0.75rem; line-height: 1.4;">
                            <b style="color: #00ffd0; font-size: 0.9rem;">{fish_name} {size}cm</b><br>
                            🕒 {dt_str}<br>
                            📍 {place}<br>
                            🌊 {tide_name} ({tide_phase})<br>
                            🚩 {temp}℃ / {wind_d} {wind_s}m/s
                        </div>
                    </div>
                </a>"""
                st.markdown(overlay_html, unsafe_allow_html=True)
                
            except Exception as e:
                # 万が一のエラー時は標準の画像表示
                st.image(img_url, caption=f"{row.get('魚種','-')}")
