import streamlit as st
import pandas as pd
from datetime import datetime

def show_edit_page(conn, url):
    st.subheader("🔄 登録情報の修正・削除")
    
    # 1. データの読み込み
    df = conn.read(spreadsheet=url, ttl=300)
    
    if df.empty:
        st.info("データがありません。")
        return

    # 全体の並びを新しい順（降順）にする
    df = df.iloc[::-1].copy()

    # --- A. 直近5件の表示 ---
    st.markdown("### 📸 修正")
    df_recent = df.head(5)
    
    for idx in df_recent.index:
        label = f"✨ 最新: {df.at[idx, 'datetime']} | {df.at[idx, '場所']} | {df.at[idx, '魚種']}"
        with st.expander(label, expanded=True):
            render_edit_form(df, idx, conn, url)

    st.markdown("---")

    # --- B. 5件より前のデータを検索・修正 ---
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
    
    # --- 🔄 気象情報の再取得ボタン ---
    st.write("💡 **データが正しくない場合はこちら**")
    if st.button(f"🔄 気象・潮汐データを再取得する", key=f"recalc_{idx}", use_container_width=True):
        try:
            with st.spinner("最新データを取得中..."):
                # 循環参照を防ぐため、ボタンが押された時だけappをインポートする
                import app
                
                dt_obj = datetime.strptime(df.at[idx, 'datetime'], '%Y/%m/%d %H:%M')
                lat, lon = float(df.at[idx, 'lat']), float(df.at[idx, 'lon'])
                
                # app.pyの関数を使用
                temp, wind_s, wind_d, rain = app.get_weather_data_openmeteo(lat, lon, dt_obj)
                station = app.find_nearest_tide_station(lat, lon)
                tide_res = app.get_tide_details(station['code'], dt_obj)
                
                # 反映
                df.at[idx, '気温'] = temp
                df.at[idx, '風速'] = wind_s
                if tide_res:
                    df.at[idx, '潮位_cm'] = tide_res['cm']
                
                st.toast("✅ 最新データを取得しました！ 下の「更新」で保存してください。")
        except Exception as e:
            st.error(f"再取得エラー: {e}")

    # --- 修正フォーム ---
    with st.form(key=f"form_{idx}"):
        st.write("📝 **基本情報**")
        col1, col2 = st.columns(2)
        new_fish = col1.text_input("魚種", value=df.at[idx, '魚種'], key=f"f_{idx}")
        new_len = col2.number_input("全長(cm)", value=float(df.at[idx, '全長_cm']), step=0.1, key=f"l_{idx}")
        new_place = col1.text_input("場所", value=df.at[idx, '場所'], key=f"p_{idx}")
        
        st.write("🌤️ **環境データ**")
        c1, c2, c3, c4 = st.columns(4)
        new_temp = c1.number_input("気温(℃)", value=float(df.at[idx, '気温']), key=f"t_{idx}")
        new_wind = c2.number_input("風速(m)", value=float(df.at[idx, '風速']), key=f"w_{idx}")
        new_tide = c3.number_input("潮位(cm)", value=int(df.at[idx, '潮位_cm']), key=f"td_{idx}")
        
        # 潮位フェーズの入力欄を追加
        current_phase = df.at[idx, '潮位フェーズ'] if '潮位フェーズ' in df.columns and pd.notna(df.at[idx, '潮位フェーズ']) else ""
        new_phase = c4.text_input("潮位フェーズ", value=current_phase, key=f"ph_{idx}", placeholder="例: 上げ3分")
        
        new_memo = st.text_area("備考", value=df.at[idx, '備考'] if pd.notna(df.at[idx, '備考']) else "", key=f"m_{idx}")

        c_sub, c_del = st.columns(2)
        if c_sub.form_submit_button("✅ 更新", use_container_width=True):
            df.at[idx, '魚種'] = new_fish
            df.at[idx, '全長_cm'] = new_len
            df.at[idx, '場所'] = new_place
            df.at[idx, '気温'] = new_temp
            df.at[idx, '風速'] = new_wind
            df.at[idx, '潮位_cm'] = new_tide
            df.at[idx, '潮位フェーズ'] = new_phase # 追加
            df.at[idx, '備考'] = new_memo
            
            # 保存時に一時的な列を削除
            save_df = df.drop(columns=['search_label']) if 'search_label' in df.columns else df
            conn.update(spreadsheet=url, data=save_df.iloc[::-1]) # スプレッドシートの元の順序（昇順）に戻して保存
            
            st.cache_data.clear() # キャッシュを消して即時反映
            st.success("更新完了！")
            st.rerun()

        if c_del.form_submit_button("🗑️ 削除", type="primary", use_container_width=True):
            df = df.drop(idx)
            save_df = df.drop(columns=['search_label']) if 'search_label' in df.columns else df
            conn.update(spreadsheet=url, data=save_df.iloc[::-1])
            
            st.cache_data.clear()
            st.warning("削除しました。")
            st.rerun()
