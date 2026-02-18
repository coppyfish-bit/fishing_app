import streamlit as st
import pandas as pd

def show_gallery_page(df):
    st.subheader("🖼️ 全釣果ギャラリー")
    
    if df is None or df.empty:
        st.info("表示するデータがまだありません。")
        return

    df_gallery = df.copy()

    # --- 重要：日付の読み込みを柔軟にする ---
    # formatを指定せず、Pandasに自動判別させることで「秒あり/なし」が混在してもOKにします
    df_gallery['datetime'] = pd.to_datetime(df_gallery['datetime'], errors='coerce')

    # datetimeが空の行（変換失敗）があるとソートでエラーになる可能性があるため
    # 保存されていない分も確実に拾うために、一度並び替えをせずに最新行を上に持ってくる工夫をします
    df_gallery = df_gallery.iloc[::-1] # 単純に「スプレッドシートの下の行」を上にする

    # --- ギャラリー表示 ---
    cols = st.columns(3)
    display_count = 0
    
    for i, (idx, row) in enumerate(df_gallery.iterrows()):
        img_url = row.get("filename")
        if not img_url or pd.isna(img_url):
            continue
        
        with cols[display_count % 3]:
            try:
                # 日付の表示形式を統一
                dt_val = row['datetime']
                dt_str = dt_val.strftime('%y/%m/%d %H:%M') if pd.notnull(dt_val) else str(row.get('datetime', '-'))
                
                fish_name = row.get('魚種', '-')
                size = row.get('全長_cm', '-')

                overlay_html = f"""
                <div style="position: relative; width: 100%; margin-bottom: 20px; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.3);">
                    <img src="{img_url}" style="width: 100%; aspect-ratio: 1/1; object-fit: cover; display: block;">
                    <div style="position: absolute; bottom: 0; width: 100%; padding: 8px; background: linear-gradient(transparent, rgba(0,0,0,0.9)); color: white; font-size: 0.8rem;">
                        <b style="color: #00ffd0;">{fish_name} {size}cm</b><br>
                        {dt_str}
                    </div>
                </div>
                """
                st.markdown(overlay_html, unsafe_allow_html=True)
                display_count += 1
                
            except Exception as e:
                st.image(str(img_url))
                display_count += 1
