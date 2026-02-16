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
    df_gallery['datetime'] = pd.to_datetime(df_gallery['datetime'])
    
    if selected_fish != "すべて":
        df_gallery = df_gallery[df_gallery["魚種"] == selected_fish]

    df_gallery = df_gallery.sort_values("datetime", ascending=False)

    if df_gallery.empty:
        st.warning("選択された魚種のデータはありません。")
        return

    # --- ギャラリー表示 ---
    cols = st.columns(3)
    
    for i, (idx, row) in enumerate(df_gallery.iterrows()):
        img_url = row["filename"]
        
        if img_url:
            with cols[i % 3]:
                try:
                    # データの取得
                    dt_str = row['datetime'].strftime('%Y/%m/%d %H:%M')
                    tide_phase = row.get('潮位フェーズ', '-')
                    tide_name = row.get('潮名', '-')
                    temp = row.get('気温', '-')
                    wind_d = row.get('風向', '-')
                    wind_s = row.get('風速', '-')
                    lat = row.get('lat')
                    lon = row.get('lon')

                    # Googleマップのリンク作成
                    map_url = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

                    # HTMLオーバーレイ表示（全体をaタグで囲んでタップ可能に）
                    overlay_html = f"""
                    <a href="{map_url}" target="_blank" style="text-decoration: none; color: inherit;">
                        <div style="position: relative; width: 100%; margin-bottom: 20px; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.5); transition: transform 0.2s;">
                            <img src="{img_url}" style="width: 100%; aspect-ratio: 1/1; object-fit: cover; display: block;">
                            <div style="position: absolute; bottom: 0; width: 100%; padding: 10px; background: rgba(0,0,0,0.7); color: white; font-size: 0.7rem; backdrop-filter: blur(4px); line-height: 1.4;">
                                <b style="color: #00ffd0; font-size: 0.85rem;">{row['魚種']} {row['全長_cm']}cm</b><br>
                                📅 {dt_str}<br>
                                📍 {row['場所']} <span style="font-size: 0.6rem; color: #aaa;">(タップで地図)</span><br>
                                🌊 {tide_name} / {tide_phase}<br>
                                🌡️ {temp}℃ / 🚩 {wind_d} {wind_s}m/s
                            </div>
                        </div>
                    </a>"""
                    st.markdown(overlay_html, unsafe_allow_html=True)
                except Exception as e:
                    st.image(img_url, caption=f"{row['魚種']}")
