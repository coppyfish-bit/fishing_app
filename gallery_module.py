import streamlit as st
import pandas as pd

def show_gallery_page(df):
    st.subheader("🖼️ 全釣果ギャラリー")
    
    if df is None or df.empty:
        st.info("表示するデータがまだありません。")
        return

    df_gallery = df.copy()

    # --- 重要：日付の読み込みを柔軟にする (NaT対策) ---
    # formatを指定せず自動判別に任せ、エラー行があっても全体を止めない
    df_gallery['datetime'] = pd.to_datetime(df_gallery['datetime'], errors='coerce')

    # スプレッドシートの下の行（最新）を上にする
    df_gallery = df_gallery.iloc[::-1]

    cols = st.columns(3)
    display_count = 0
    
    for i, (idx, row) in enumerate(df_gallery.iterrows()):
        img_url = row.get("filename")
        if not img_url or pd.isna(img_url):
            continue
        
        with cols[display_count % 3]:
            # --- 日付・時刻の表示処理 (NaT対策) ---
            dt_val = row['datetime']
            if pd.notnull(dt_val):
                dt_str = dt_val.strftime('%y/%m/%d %H:%M')
            else:
                # NaTの場合は、元の値（文字列）をそのまま使う
                dt_str = str(row.get('datetime', '-'))

            # --- 気象・潮汐情報の取得 ---
            temp = f"{row.get('気温', '-')}℃"
            wind = f"{row.get('風向', '')}{row.get('風速', '-')}m"
            tide_name = row.get('潮名', '-')
            tide_phase = row.get('潮位フェーズ', '-')

            fish_info = f"{row.get('魚種', '-')} {row.get('全長_cm', '-')}cm"

            # HTMLでのカード表示（気象・潮汐情報を追加）
            overlay_html = f"""
            <div style="position: relative; width: 100%; margin-bottom: 20px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
                <img src="{img_url}" style="width: 100%; aspect-ratio: 1/1; object-fit: cover; display: block;">
                <div style="position: absolute; bottom: 0; width: 100%; padding: 8px; background: linear-gradient(transparent, rgba(0,0,0,0.9)); color: white; font-size: 0.75rem;">
                    <b style="color: #00ffd0; font-size: 0.9rem;">{fish_info}</b><br>
                    📅 {dt_str}<br>
                    🌡️ {temp} / 💨 {wind}<br>
                    🌊 {tide_name} ({tide_phase})
                </div>
            </div>
            """
            st.markdown(overlay_html, unsafe_allow_html=True)
            display_count += 1
