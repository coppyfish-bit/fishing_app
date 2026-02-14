import streamlit as st
import pandas as pd

def show_edit_page(conn, url):
    st.subheader("🔄 直近5件の登録情報修正")
    
    # 1. データの読み込み
    df = conn.read(spreadsheet=url, ttl=0)
    
    if df.empty:
        st.info("データがありません。")
        return

    # 2. データを逆順（新しい順）にして、直近5件を取得
    df_recent = df.iloc[::-1].head(5).copy()

    for idx in df_recent.index:
        # 各レコードを枠(expander)で囲んで整理
        label = f"📌 {df.at[idx, 'datetime']} | {df.at[idx, '場所']} | {df.at[idx, '魚種']}"
        with st.expander(label, expanded=False):
            
            # --- 写真のプレビュー ---
            if 'filename' in df.columns and df.at[idx, 'filename']:
                st.image(df.at[idx, 'filename'], caption="登録済みの写真", width=300)
            
            # --- 修正用フォーム（各レコードごとに独立させるためkeyを指定） ---
            with st.form(key=f"form_{idx}"):
                st.write("### 📝 修正内容")
                col1, col2 = st.columns(2)
                new_fish = col1.text_input("魚種", value=df.at[idx, '魚種'], key=f"fish_{idx}")
                new_length = col2.number_input("全長 (cm)", value=float(df.at[idx, '全長_cm']), step=0.1, key=f"len_{idx}")
                
                new_place = col1.text_input("場所", value=df.at[idx, '場所'], key=f"place_{idx}")
                new_memo = st.text_area("備考", value=df.at[idx, '備考'] if pd.notna(df.at[idx, '備考']) else "", key=f"memo_{idx}")

                st.write("🌤️ **気象・潮汐データ**")
                c1, c2, c3 = st.columns(3)
                new_temp = c1.number_input("気温(℃)", value=float(df.at[idx, '気温']), key=f"temp_{idx}")
                new_wind_s = c2.number_input("風速(m/s)", value=float(df.at[idx, '風速']), key=f"wind_{idx}")
                new_tide_cm = c3.number_input("潮位(cm)", value=int(df.at[idx, '潮位_cm']), key=f"tide_{idx}")

                col_sub, col_del = st.columns(2)
                update_btn = col_sub.form_submit_button("✅ このデータを更新", use_container_width=True)
                delete_btn = col_del.form_submit_button("🗑️ 削除する", use_container_width=True, type="primary")

                if update_btn:
                    # 値の反映
                    df.at[idx, '魚種'] = new_fish
                    df.at[idx, '全長_cm'] = new_length
                    df.at[idx, '場所'] = new_place
                    df.at[idx, '備考'] = new_memo
                    df.at[idx, '気温'] = new_temp
                    df.at[idx, '風速'] = new_wind_s
                    df.at[idx, '潮位_cm'] = new_tide_cm
                    
                    conn.update(spreadsheet=url, data=df)
                    st.success("✅ スプレッドシートを更新しました！")
                    st.rerun()

                if delete_btn:
                    df = df.drop(idx)
                    conn.update(spreadsheet=url, data=df)
                    st.warning("🗑️ データを削除しました。")
                    st.rerun()
