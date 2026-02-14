import streamlit as st
import pandas as pd

def show_gallery_page(df):
    st.subheader("🖼️ 精密データオーバーレイ")
    
    if df.empty:
        st.info("表示するデータがまだありません。")
        return

    # --- フィルター機能 ---
    # 魚種のリストを取得（重複なし）
    fish_list = ["すべて"] + sorted(df["魚種"].unique().tolist())
    selected_fish = st.selectbox("🐟 魚種で絞り込み", fish_list)

    # データのコピーと日付型への変換
    df_gallery = df.copy()
    df_gallery['datetime'] = pd.to_datetime(df_gallery['datetime'])
    
    # フィルター適用
    if selected_fish != "すべて":
        df_gallery = df_gallery[df_gallery["魚種"] == selected_fish]

    # 最新順にソート
    df_gallery = df_gallery.sort_values("datetime", ascending=False)

    if df_gallery.empty:
        st.warning("選択された魚種のデータはありません。")
        return

    # --- ギャラリー表示 ---
    cols = st.columns(3)
    
    for i, (idx, row) in enumerate(df_gallery.iterrows()):
        img_url = row["filename"]  # CloudinaryのURL
        
        if img_url:
            with cols[i % 3]:
                try:
                    # 潮汐ディテールの計算
                    dt = row['datetime']
                    prev_h = pd.to_datetime(row['直前の満潮_時刻']) if pd.notna(row['直前の満潮_時刻']) else None
                    
                    if prev_h:
                        diff_mins = int((dt - prev_h).total_seconds() / 60)
                        tide_detail = row.get('潮位フェーズ', f"{diff_mins}分経過")
                    else:
                        tide_detail = row.get('潮位フェーズ', "-")

                    # HTMLオーバーレイ表示
                    overlay_html = f"""
                    <div style="position: relative; width: 100%; margin-bottom: 20px; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.5);">
                        <img src="{img_url}" style="width: 100%; aspect-ratio: 1/1; object-fit: cover; display: block;">
                        <div style="position: absolute; bottom: 0; width: 100%; padding: 8px; background: rgba(0,0,0,0.6); color: white; font-size: 0.7rem; backdrop-filter: blur(2px); line-height: 1.2;">
                            <b style="color: #00ffd0; font-size: 0.8rem;">{row['魚種']} {row['全長_cm']}cm</b><br>
                            📍 {row['場所']}<br>
                            🕒 {tide_detail} / 🌡️ {row.get('気温','-')}℃
                        </div>
                    </div>"""
                    st.markdown(overlay_html, unsafe_allow_html=True)
                except Exception as e:
                    st.image(img_url, caption=f"{row['魚種']}")
