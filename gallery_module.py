import streamlit as st
import pandas as pd

def show_gallery_page(df):
    st.subheader("🖼️ 全釣果ギャラリー")
    
    if df is None or df.empty:
        st.info("表示するデータがまだありません。")
        return

    df_gallery = df.copy()

    # --- 日付の読み込み処理 (NaTを徹底排除) ---
    # datetime列を一度文字列に変換し、空の値(NaN)だけハイフンに置き換える
    df_gallery['datetime'] = df_gallery['datetime'].fillna('-').astype(str)

    # 最新の投稿（下の行）を上にする
    df_gallery = df_gallery.iloc[::-1]

    cols = st.columns(3)
    display_count = 0
    
    for i, (idx, row) in enumerate(df_gallery.iterrows()):
        img_url = row.get("filename")
        if not img_url or pd.isna(img_url) or img_url == "nan":
            continue
        
        with cols[display_count % 3]:
            # 日付文字列を取得（秒があれば削り、なければそのまま出す）
            raw_dt = str(row.get('datetime', '-'))
            # 2026-02-17 14:50:00 のような場合に秒(:00)をカットする処理
            display_dt = raw_dt[:16] if len(raw_dt) > 16 else raw_dt

            # 気象・潮汐情報
            temp = f"{row.get('気温', '-')}℃"
            wind = f"{row.get('風向', '')}{row.get('風速', '-')}m"
            tide_name = row.get('潮名', '-')
            tide_phase = row.get('潮位フェーズ', '-')
            fish_info = f"{row.get('魚種', '-')} {row.get('全長_cm', '-')}cm"

            overlay_html = f"""
            <div style="position: relative; width: 100%; margin-bottom: 20px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
                <img src="{img_url}" style="width: 100%; aspect-ratio: 1/1; object-fit: cover; display: block;">
                <div style="position: absolute; bottom: 0; width: 100%; padding: 8px; background: linear-gradient(transparent, rgba(0,0,0,0.9)); color: white; font-size: 0.75rem;">
                    <b style="color: #00ffd0; font-size: 0.9rem;">{fish_info}</b><br>
                    📅 {display_dt}<br>
                    🌡️ {temp} / 💨 {wind}<br>
                    🌊 {tide_name} ({tide_phase})
                </div>
            </div>
            """
            st.markdown(overlay_html, unsafe_allow_html=True)
            display_count += 1
