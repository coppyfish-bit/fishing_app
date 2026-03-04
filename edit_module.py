import streamlit as st
import pandas as pd
from datetime import datetime

def show_edit_page(conn, url, weather_func, station_func, tide_func, moon_func, tide_name_func):
    st.subheader("🔄 登録情報の修正・削除")
    df = conn.read(spreadsheet=url, ttl="0s")
    if df.empty:
        st.info("データがありません。")
        return

    df_reversed = df.iloc[::-1]
    labels = [f"ID:{i} | {df.at[i, 'datetime']} | {df.at[i, '場所']}" for i in df_reversed.index]
    
    selected_label = st.selectbox("編集したいデータを選んでください", options=labels, index=None, key="selector_main")

    if selected_label:
        target_idx = int(selected_label.split('|')[0].replace('ID:', '').strip())
        st.divider()
        render_edit_form(df, target_idx, conn, url, weather_func, station_func, tide_func, moon_func, tide_name_func)

def render_edit_form(df, idx, conn, url, weather_func, station_func, tide_func, moon_func, tide_name_func):
    if 'filename' in df.columns and pd.notna(df.at[idx, 'filename']):
        st.image(df.at[idx, 'filename'], width=400)
    
    temp_data_key = f"edit_temp_{idx}"
    form_ver_key = f"edit_ver_{idx}"
    if form_ver_key not in st.session_state:
        st.session_state[form_ver_key] = 0

    # --- 再取得ボタン ---
    if st.button(f"🔄 最新の気象・潮汐を計算して反映させる", key=f"recalc_btn_{idx}"):
        try:
            with st.status("データ取得診断中...", expanded=True) as status:
                raw_dt = str(df.at[idx, 'datetime']).strip()
                while raw_dt.endswith(":"): raw_dt = raw_dt[:-1]
                dt_obj = pd.to_datetime(raw_dt)
                
                lat = float(df.at[idx, 'lat']) if pd.notna(df.at[idx, 'lat']) else 35.0
                lon = float(df.at[idx, 'lon']) if pd.notna(df.at[idx, 'lon']) else 135.0
                
                # 1. 気象
                temp, w_s, w_d, rain = weather_func(lat, lon, dt_obj)
                
                # 2. 潮汐（ここが怪しいので詳細に表示）
                station = station_func(lat, lon)
                st.write(f"📍 判定された観測所: {station['name']} ({station['code']})")
                
                d_data = tide_func(station['code'], dt_obj)
                st.write(f"📦 取得されたデータ型: {type(d_data)}")
                
                # 潮位データの抽出をより堅牢に
                t_cm = 0
                t_ph = "不明"
                if isinstance(d_data, dict):
                    # キーが存在するか、値がNoneでないか徹底チェック
                    t_cm = d_data.get('cm', d_data.get('tide_cm', 0))
                    t_ph = d_data.get('phase', d_data.get('tide_phase', "不明"))
                    st.write(f"✅ 抽出結果: {t_cm}cm, {t_ph}")
                else:
                    st.warning("⚠️ 潮汐データが辞書形式で戻ってきていません。")

                t_name = tide_name_func(moon_func(dt_obj))
                
                st.session_state[temp_data_key] = {
                    "temp": temp, "wind_s": w_s, "wind_d": w_d, "rain": rain,
                    "tide_cm": t_cm, "tide_name": t_name, "phase": t_ph
                }
                st.session_state[form_ver_key] += 1
                status.update(label="診断完了！", state="complete", expanded=False)
                st.rerun()
        except Exception as e:
            st.error(f"❌ 再取得エラー: {str(e)}")

    # --- 値の決定ロジック ---
    t_data = st.session_state.get(temp_data_key, {})
    has_new = temp_data_key in st.session_state and st.session_state[temp_data_key] is not None

    def get_v(key, col, default):
        if has_new and key in t_data: return t_data[key]
        return df.at[idx, col] if col in df.columns and pd.notna(df.at[idx, col]) else default

    # フォーム
    ver = st.session_state[form_ver_key]
    with st.form(key=f"edit_form_{idx}_v{ver}"):
        st.info(f"ID:{idx} を編集中")
        c_f, c_l, c_p = st.columns([2, 1, 2])
        new_fish = c_f.text_input("魚種", value=str(df.at[idx, '魚種']))
        new_len = c_l.number_input("全長(cm)", value=float(df.at[idx, '全長_cm']) if pd.notna(df.at[idx, '全長_cm']) else 0.0, step=0.1)
        new_place = c_p.text_input("場所", value=str(df.at[idx, '場所']))
        
        c1, c2, c3 = st.columns(3)
        new_temp = c1.number_input("気温(℃)", value=float(get_v("temp", "気温", 0.0)))
        new_wind_s = c2.number_input("風速(m)", value=float(get_v("wind_s", "風速", 0.0)))
        new_wind_d = c3.text_input("風向", value=str(get_v("wind_d", "風向", "不明")))
        
        c4, c5, c6 = st.columns(3)
        new_rain = c4.number_input("降水(48h)", value=float(get_v("rain", "降水量", 0.0)))
        new_tide_cm = c5.number_input("潮位(cm)", value=int(get_v("tide_cm", "潮位_cm", 0)))
        new_tide_name = c6.text_input("潮名", value=str(get_v("tide_name", "潮名", "不明")))
        
        new_phase = st.text_input("潮位フェーズ", value=str(get_v("phase", "潮位フェーズ", "不明")))
        new_memo = st.text_area("備考", value=str(df.at[idx, '備考']) if '備考' in df.columns and pd.notna(df.at[idx, '備考']) else "")
        
        st.markdown("---")
        confirm_del = st.checkbox("このデータを完全に削除する", key=f"del_confirm_{idx}")
        c_save, c_del = st.columns(2)
        
        if c_save.form_submit_button("✅ 更新内容を保存する", use_container_width=True):
            latest_df = conn.read(spreadsheet=url, ttl="0s")
            cols = ['魚種', '全長_cm', '場所', '気温', '風速', '風向', '降水量', '潮位_cm', '潮名', '潮位フェーズ', '備考']
            vals = [new_fish, new_len, new_place, new_temp, new_wind_s, new_wind_d, new_rain, new_tide_cm, new_tide_name, new_phase, new_memo]
            for c, v in zip(cols, vals):
                if c in latest_df.columns: latest_df.at[idx, c] = v
            
            conn.update(spreadsheet=url, data=latest_df)
            st.session_state[temp_data_key] = None
            st.cache_data.clear()
            st.success("保存しました！")
            st.rerun()

        if c_del.form_submit_button("🗑️ 削除実行", type="primary", use_container_width=True):
            if confirm_del:
                latest_df = conn.read(spreadsheet=url, ttl="0s")
                latest_df = latest_df.drop(idx)
                conn.update(spreadsheet=url, data=latest_df)
                st.session_state[temp_data_key] = None
                st.cache_data.clear()
                st.rerun()
