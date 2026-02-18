import streamlit as st
import pandas as pd

def show_gallery_page(df):
    st.subheader("🖼️ 全釣果ギャラリー（最新順）")
    
    if df is None or df.empty:
        st.info("表示するデータがまだありません。")
        return

    # データのコピーを作成
    df_gallery = df.copy()
    
    # datetime列を日付型に変換して最新順に並び替え
    df_gallery['datetime'] = pd.to_datetime(df_gallery['datetime'], errors='coerce')
    df_gallery = df_gallery.sort_values("datetime", ascending=False)

    # --- ギャラリー表示 ---
    cols = st.columns(3)
    
    for i, (idx, row) in enumerate(df_gallery.iterrows()):
        img_url = row.get("filename")
        if not img_url or pd.isna(img_url):
            continue
        
        with cols[i % 3]:
            try:
                # 表示用データの準備
                dt_str = row['datetime'].strftime('%y/%m/%d %H:%M') if pd.notnull(row['datetime']) else "-"
                fish_name = row.get('魚種', '-')
                size = row.get('全長_cm', '-')
                place = row.get('場所', '-')
                tide_name = row.get('潮名', '-')
                tide_phase = row.get('潮位フェーズ', '-')

                # 画像と情報を表示
                overlay_html = f"""
                <div style="position: relative; width: 100%; margin-bottom: 20px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
                    <img src="{img_url}" style="width: 100%; aspect-ratio: 1/1; object-fit: cover; display: block;">
                    <div style="position: absolute; bottom: 0; width: 100%; padding: 8px; background: linear-gradient(transparent, rgba(0,0,0,0.9)); color: white; font-size: 0.8rem;">
                        <b style="color: #00ffd0;">{fish_name} {size}cm</b><br>
                        {dt_str}<br>
                        {place} / {tide_name}
                    </div>
                </div>
                """
                st.markdown(overlay_html, unsafe_allow_html=True)
                
            except Exception as e:
                st.image(str(img_url), caption=f"{row.get('魚種','-')}")
