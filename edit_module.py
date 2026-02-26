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
    st.markdown("### 📸 最近の記録を修正")
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
    
    st.write("💡 **データが正しくない場合はこちら**")
    
    # セッション状態の初期化（再取得した値を保持するため）
    recalc_key = f"recalc_data_{idx}"
    if recalc_key not in st.session_state:
        st.session_state[recalc_key] = None

    # --- 🔄 気象情報の再取得ボタン ---
    if st.button(f"🔄 気象・潮汐データを再取得する", key=f"recalc_btn_{idx}", use_container_width=True):
        try:
            with st.spinner("地点に合わせて精密データを再計算中..."):
                import app
                
                # 日時解析
                raw_dt = str(df.at[idx, 'datetime']).replace("-", "/").strip()
                parts = raw_dt.split(":")
                clean_dt_str = f"{parts[0]}:{parts[1]}" if len(parts) > 2 else raw_dt
                
                try:
                    dt_obj = datetime.strptime(clean_dt_str, '%Y/%m/%d %H:%M')
                except ValueError:
                    dt_obj = app.safe_strptime(raw_dt)
                
                lat = float(df.at[idx, 'lat'])
                lon = float(df.at[idx, 'lon'])
                
                # app.py の関数を呼び出し
                temp, wind_s, wind_d, rain = app.get_weather_data_openmeteo(lat, lon, dt_obj)
                station = app.find_nearest_tide_station(lat, lon)
                tide_res = app.get_tide_details(station['code'], dt_obj)
                
                if temp is not None:
                    # セッション状態に取得結果を保存（これがフォームの初期値になる）
                    st.session_state[recalc_key] = {
                        "temp": temp,
                        "wind_s": wind_s,
                        "wind_d": wind_d,
                        "rain": rain,
                        "tide_cm": tide_res['cm'] if tide_res else df.at[idx, '潮位_cm'],
                        "phase": tide_res.get('phase', "不明") if tide_res else df.at[idx, '潮位フェーズ']
                    }
                    st.success(f"取得成功！値をフォームにセットしました。")
                else:
                    st.error("気象データの取得に失敗しました。")

        except Exception as e:
            st.error(f"再取得エラー: {e}")

    # --- フォームに表示する値の決定 ---
    # 再取得データがあればそれを使用、なければ既存のレコードデータを使用
    current_data = st.session_state[recalc_key]
    
    def_temp = float(current_data["temp"]) if current_data else float(df.at[idx, '気温'])
    def_wind = float(current_data["wind_s"]) if current_data else float(df.at[idx, '風速'])
    def_rain = float(current_data["rain"]) if current_data else (float(df.at[idx, '降水量']) if '降水量' in df.columns else 0.0)
    def_tide = int(current_data["tide_cm"]) if current_data else int(df.at[idx, '潮位_cm'])
    def_phase = current_data["phase"] if current_data else (df.at[idx, '潮位フェーズ'] if '潮位フェーズ' in df.columns else "")

    # --- 修正フォーム ---
    with st.form(key=f"form_{idx}"):
        st.write("📝 **基本情報**")
        col1, col2 = st.columns(2)
        new_fish = col1.text_input("魚種", value=df.at[idx, '魚種'], key=f"f_{idx}")
        new_len = col2.number_input("全長(cm)", value=float(df.at[idx, '全長_cm']), step=0.1, key=f"l_{idx}")
        new_place = col1.text_input("場所", value=df.at[idx, '場所'], key=f"p_{idx}")
        
        st.write("🌤️ **環境データ**")
        c1, c2, c3, c4, c5 = st.columns(5)
        new_temp = c1.number_input("気温(℃)", value=def_temp, key=f"t_{idx}")
        new_wind = c2.number_input("風速(m)", value=def_wind, key=f"w_{idx}")
        new_rain = c3.number_input("降水(48h)", value=def_rain, key=f"r_{idx}")
        new_tide = c4.number_input("潮位(cm)", value=def_tide, key=f"td_{idx}")
        new_phase = c5.text_input("フェーズ", value=def_phase, key=f"ph_{idx}")
        
        new_memo = st.text_area("備考", value=df.at[idx, '備考'] if pd.notna(df.at[idx, '備考']) else "", key=f"m_{idx}")

        st.markdown("---")
        st.write("⚠️ **データの削除**")
        confirm_delete = st.checkbox("このデータを完全に削除してもよろしいですか？", key=f"conf_{idx}")

        c_sub, c_del = st.columns(2)
        
        if c_sub.form_submit_button("✅ 更新保存", use_container_width=True):
            df.at[idx, '魚種'] = new_fish
            df.at[idx, '全長_cm'] = new_len
            df.at[idx, '場所'] = new_place
            df.at[idx, '気温'] = new_temp
            df.at[idx, '風速'] = new_wind
            if '降水量' in df.columns: df.at[idx, '降水量'] = new_rain
            df.at[idx, '潮位_cm'] = new_tide
            df.at[idx, '潮位フェーズ'] = new_phase
            df.at[idx, '備考'] = new_memo
            
            # 保存処理
            save_df = df.drop(columns=['search_label']) if 'search_label' in df.columns else df
            conn.update(spreadsheet=url, data=save_df.iloc[::-1])
            
            # 保存後はセッション状態をクリア
            st.session_state[recalc_key] = None
            st.cache_data.clear()
            st.success("更新完了しました！")
            st.rerun()

        if c_del.form_submit_button("🗑️ 削除実行", type="primary", use_container_width=True):
            if confirm_delete:
                df = df.drop(idx)
                save_df = df.drop(columns=['search_label']) if 'search_label' in df.columns else df
                conn.update(spreadsheet=url, data=save_df.iloc[::-1])
                st.session_state[recalc_key] = None
                st.cache_data.clear()
                st.rerun()
