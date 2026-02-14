import streamlit as st
import pandas as pd

def show_edit_page(conn, url):
    st.subheader("🔄 登録情報の修正・削除")
    
    # 1. スプレッドシートから最新データを読み込み
    # ttl=0 にすることで、常に最新のデータを取得します
    df = conn.read(spreadsheet=url, ttl=0)
    
    if df.empty:
        st.info("データがありません。")
        return

    # 選択用のリスト作成（日時 | 場所 | 魚種）
    df['display_name'] = df['datetime'].astype(str) + " | " + df['場所'].astype(str) + " | " + df['魚種'].astype(str)
    target_row = st.selectbox("修正したいデータを選択してください", df['display_name'])
    
    # 選択された行のインデックスを取得
    idx = df[df['display_name'] == target_row].index[0]
    
    st.markdown("---")

    # 修正用フォーム
    with st.form("advanced_edit_form"):
        st.write("### 📝 基本情報")
        col1, col2 = st.columns(2)
        new_fish = col1.text_input("魚種", value=df.at[idx, '魚種'])
        new_length = col2.number_input("全長 (cm)", value=float(df.at[idx, '全長_cm']), step=0.1)
        
        new_place = col1.text_input("場所", value=df.at[idx, '場所'])
        # 釣り人のリストは現状に合わせて調整してください
        angler_list = ["長元", "川口", "山川"]
        current_angler = df.at[idx, '釣り人']
        new_angler = col2.selectbox("釣り人", angler_list, 
                                     index=angler_list.index(current_angler) if current_angler in angler_list else 0)

        st.write("### 🌤️ 気象・潮汐データ")
        c1, c2, c3 = st.columns(3)
        new_temp = c1.number_input("気温 (℃)", value=float(df.at[idx, '気温']), step=0.1)
        new_wind_s = c2.number_input("風速 (m/s)", value=float(df.at[idx, '風速']), step=0.1)
        new_wind_d = c3.text_input("風向", value=df.at[idx, '風向'])
        
        new_tide_cm = c1.number_input("潮位 (cm)", value=int(df.at[idx, '潮位_cm']), step=1)
        new_tide_phase = c2.text_input("潮位フェーズ", value=df.at[idx, '潮位フェーズ'])
        new_tide_name = c3.text_input("潮名", value=df.at[idx, '潮名'])

        new_memo = st.text_area("備考", value=df.at[idx, '備考'])

        st.markdown("---")
        col_sub, col_del = st.columns([1, 1])
        update_btn = col_sub.form_submit_button("✅ スプレッドシートを更新", use_container_width=True)
        delete_btn = col_del.form_submit_button("🗑️ このレコードを削除", use_container_width=True, type="primary")

        # --- 更新処理 ---
        if update_btn:
            # DataFrameの値を書き換え
            df.at[idx, '魚種'] = new_fish
            df.at[idx, '全長_cm'] = new_length
            df.at[idx, '場所'] = new_place
            df.at[idx, '釣り人'] = new_angler
            df.at[idx, '気温'] = new_temp
            df.at[idx, '風速'] = new_wind_s
            df.at[idx, '風向'] = new_wind_d
            df.at[idx, '潮位_cm'] = new_tide_cm
            df.at[idx, '潮位フェーズ'] = new_tide_phase
            df.at[idx, '潮名'] = new_tide_name
            df.at[idx, '備考'] = new_memo

            # 不要な表示用カラムを削除して保存
            save_df = df.drop(columns=['display_name'])
            conn.update(spreadsheet=url, data=save_df)
            
            st.success("✅ スプレッドシートの情報を更新しました！")
            st.rerun()

        # --- 削除処理 ---
        if delete_btn:
            df = df.drop(idx)
            save_df = df.drop(columns=['display_name'])
            conn.update(spreadsheet=url, data=save_df)
            
            st.warning("🗑️ データを削除しました。")
            st.rerun()