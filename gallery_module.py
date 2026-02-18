import streamlit as st
import pandas as pd

def show_gallery_page(df):
    # インデックスを振り直して、途中に欠番があっても最後までループさせる
    df = df.reset_index(drop=True)
    st.subheader("📊 ギャラリー診断モード")
    
    if df is None or df.empty:
        st.error("❌ データが空っぽです（読み込み失敗）")
        return

    # 1. データの件数を表示
    st.write(f"読み込んだ総データ数: {len(df)} 件")
    
    # 2. データの末尾5件をテーブルで表示（ここを確認！）
    st.write("▼ 最新の5件（スプレッドシートの後半部分）")
    st.dataframe(df.tail(5))

    # 3. 実際の表示ループ
    st.divider()
    cols = st.columns(3)
    
    # datetimeで並び替え
    df_sorted = df.copy()
    df_sorted['datetime'] = pd.to_datetime(df_sorted['datetime'], errors='coerce')
    df_sorted = df_sorted.sort_values("datetime", ascending=False)

    display_count = 0
    for idx in range(len(df)):
        row = df.iloc[idx]
        img_url = row.get("filename")
        
        # URLが空っぽならスキップ理由を表示
        if not img_url or pd.isna(img_url):
            # st.write(f"行 {idx}: filenameが空のためスキップ") # デバッグ用
            continue
        
        with cols[display_count % 3]:
            st.image(str(img_url), caption=f"{row.get('魚種','-')} ({row.get('datetime','-')})")
            display_count += 1

    if display_count == 0:
        st.warning("⚠️ filename（画像URL）が入っているデータが1件もありませんでした。")

