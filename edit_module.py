import streamlit as st
import pandas as pd

def show_edit_page(conn, url):
    st.subheader("🔄 登録情報の修正・削除")
    
    # 1. データの読み込み
    df = conn.read(spreadsheet=url, ttl=0)
    
    if df.empty:
        st.info("データがありません。")
        return

    # 全体の並びを新しい順（降順）にする
    df = df.iloc[::-1].copy()

    # --- A. 直近5件の表示（最初から開いた状態） ---
    st.markdown("### 📸 修正")
    df_recent = df.head(5)
    
    for idx in df_recent.index:
        label = f"✨ 最新: {df.at[idx, 'datetime']} | {df.at[idx, '場所']} | {df.at[idx, '魚種']}"
        # expanded=True にすることで、最初から入力欄と写真が見えるようになります
        with st.expander(label, expanded=True):
            render_edit_form(df, idx, conn, url)

    st.markdown("---")

    # --- B. 5件より前のデータをリストから選択 ---
    st.markdown("### 🔍 過去のデータを検索・修正")
    if len(df) > 5:
        df_old = df.iloc[5:].copy()
        df_old['search_label'] = df_old['datetime'].astype(str) + " | " + df_old['場所'].astype(str) + " | " + df_old['魚種'].astype(str)
        
        selected_label = st.selectbox("修正したい過去のデータを選択してください", df_old['search_label'], index=None, placeholder="項目を選択...")
        
        if selected_label:
            target_idx = df_old[df_old['search_label'] == selected_label].index[0]
            with st.container(border=True):
                st.info(f"選択中のデータ: {selected_label}")
                render_edit_form(df, target_idx, conn, url)
    else:
        st.caption("5件より前のデータはありません。")

# --- 共通の修正フォーム関数 ---
def render_edit_form(df, idx, conn, url):
    # 写真の表示
    if 'filename' in df.columns and df.at[idx, 'filename']:
        st.image(df.at[idx, 'filename'], width=400)
    
    with st.form(key=f"form_{idx}"):
        st.write("📝 **基本情報**")
        col1, col2 = st.columns(2)
        new_fish = col1.text_input("魚種", value=df.at[idx, '魚種'], key=f"f_{idx}")
        new_len = col2.number_input("全長(cm)", value=float(df.at[idx, '全長_cm']), step=0.1, key=f"l_{idx}")
        new_place = col1.text_input("場所", value=df.at[idx, '場所'], key=f"p_{idx}")
        
        st.write("🌤️ **環境データ**")
        c1, c2, c3 = st.columns(3)
        new_temp = c1.number_input("気温(℃)", value=float(df.at[idx, '気温']), key=f"t_{idx}")
        new_wind = c2.number_input("風速(m)", value=float(df.at[idx, '風速']), key=f"w_{idx}")
        new_tide = c3.number_input("潮位(cm)", value=int(df.at[idx, '潮位_cm']), key=f"td_{idx}")
        
        new_memo = st.text_area("備考", value=df.at[idx, '備考'] if pd.notna(df.at[idx, '備考']) else "", key=f"m_{idx}")

        c_sub, c_del = st.columns(2)
        if c_sub.form_submit_button("✅ 更新", use_container_width=True):
            df.at[idx, '魚種'] = new_fish
            df.at[idx, '全長_cm'] = new_len
            df.at[idx, '場所'] = new_place
            df.at[idx, '気温'] = new_temp
            df.at[idx, '風速'] = new_wind
            df.at[idx, '潮位_cm'] = new_tide
            df.at[idx, '備考'] = new_memo
            # 保存時に一時的な列を削除
            save_df = df.drop(columns=['search_label']) if 'search_label' in df.columns else df
            conn.update(spreadsheet=url, data=save_df.iloc[::-1]) # スプレッドシートの元の順序（昇順）に戻して保存
            st.success("更新完了！")
            st.rerun()

        if c_del.form_submit_button("🗑️ 削除", type="primary", use_container_width=True):
            df = df.drop(idx)
            save_df = df.drop(columns=['search_label']) if 'search_label' in df.columns else df
            conn.update(spreadsheet=url, data=save_df.iloc[::-1])
            st.warning("削除しました。")
            st.rerun()

