import streamlit as st
import pandas as pd
from datetime import datetime

# AIとの会話は学習に使用したり外部に漏れたりしません。釣果情報も共有しません。

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

    if st.button(f"🔄 最新の気象・潮汐を計算して反映させる", key=f"recalc_btn_{idx}"):
        try:
            with st.status("🔍 潮位0cmの原因を調査中...", expanded=True) as status:
                # 1. 日時の正規化チェック
                raw_dt = str(df.at[idx, 'datetime']).strip()
                while raw_dt.endswith(":"): raw_dt = raw_dt[:-1]
                dt_obj = pd.to_datetime(raw_dt)
                st.write(f"📅 検索日時: {dt_obj.strftime('%Y-%m-%d %H:%M')}")
                
                # 2. 座標と観測所
                lat = float(df.at[idx, 'lat'])
                lon = float(df.at[idx, 'lon'])
                station = station_func(lat, lon)
                st.write(f"📍 観測所: {station['name']} (コード: {station['code']})")
                
                # 3. 気象取得
                temp, w_s, w_d, rain = weather_func(lat, lon, dt_obj)
                
                # 4. 潮汐取得実行
                d_data = tide_func(station['code'], dt_obj)
                
                # 詳細ログ
                if not d_data or (isinstance(d_data, dict) and d_data.get('cm') == 0):
                    st.warning("⚠️ 潮位が0として返されました。app.pyの get_tide_details 内で、指定日時のデータがJSONから見つかっていない可能性があります。")
                    st.write("取得結果オブジェクト:", d_data)
                
                t_cm = d_data.get('cm', 0) if isinstance(d_data, dict) else 0
                t_ph = d_data.get('phase', "不明") if isinstance(d_data, dict) else "不明"
                t_name = tide_name_func(moon_func(dt_obj))
                
                st.session_state[temp_data_key] = {
                    "temp": temp, "wind_s": w_s, "wind_d": w_d, "rain": rain,
                    "tide_cm": t_cm, "tide_name": t_name, "phase": t_ph
                }
                st.session_state[form_ver_key] += 1
                status.update(label="調査完了", state="complete", expanded=False)
                st.rerun()
        except Exception as e:
            st.error(f"❌ 再取得エラー: {str(e)}")

    # --- 以下、前回のフォーム表示・保存ロジックと同じ ---
    t_data = st.session_state.get(temp_data_key, {})
    has_new = temp_data_key in st.session_state and st.session_state[temp_data_key] is not None
    def get_v(key, col, default):
        if has_new and key in t_data: return t_data[key]
        return df.at[idx, col] if col in df.columns and pd.notna(df.at[idx, col]) else default

    ver = st.session_state[form_ver_key]
    with st.form(key=f"edit_form_{idx}_v{ver}"):
        st.info(f"ID:{idx} を編集中")
        c_f, c_l, c_p = st.columns([2, 1, 2])
        new_fish = c_f.text_input("魚種", value=str(df.at[idx, '魚種']))
        new_len = c_l.number_input("全長(cm)", value=float(df.at[idx, '全長_cm']) if '全長_cm' in df.columns else 0.0, step=0.1)
        new_place = c_p.text_input("場所", value=str(df.at[idx, '場所']))
        
        c1, c2, c3 = st.columns(3)
        new_temp = c1.number_input("気温", value=float(get_v("temp", "気温", 0.0)))
        new_wind_s = c2.number_input("風速", value=float(get_v("wind_s", "風速", 0.0)))
        new_wind_d = c3.text_input("風向", value=str(get_v("wind_d", "風向", "不明")))
        
        c4, c5, c6 = st.columns(3)
        new_rain = c4.number_input("降水量", value=float(get_v("rain", "降水量", 0.0)))
        new_tide_cm = c5.number_input("潮位_cm", value=int(get_v("tide_cm", "潮位_cm", 0)))
        new_tide_name = c6.text_input("潮名", value=str(get_v("tide_name", "潮名", "不明")))
        new_phase = st.text_input("潮位フェーズ", value=str(get_v("phase", "潮位フェーズ", "不明")))
        new_memo = st.text_area("備考", value=str(df.at[idx, '備考']) if '備考' in df.columns else "")
        
        st.markdown("---")
        confirm_del = st.checkbox("このデータを完全に削除する", key=f"del_confirm_{idx}")
        c_save, c_del = st.columns(2)
        
        if c_save.form_submit_button("✅ 更新内容を保存する", use_container_width=True):
            latest_df = conn.read(spreadsheet=url, ttl="0s")
            update_map = {'魚種': new_fish, '全長_cm': new_len, '場所': new_place, '気温': new_temp, '風速': new_wind_s, '風向': new_wind_d, '降水量': new_rain, '潮位_cm': new_tide_cm, '潮名': new_tide_name, '潮位フェーズ': new_phase, '備考': new_memo}
            for col, val in update_map.items():
                if col in latest_df.columns: latest_df.at[idx, col] = val
            conn.update(spreadsheet=url, data=latest_df)
            st.session_state[temp_data_key] = None
            st.cache_data.clear()
            st.success("更新しました！")
            st.rerun()

        if c_del.form_submit_button("🗑️ 削除実行", type="primary", use_container_width=True):
            if confirm_del:
                latest_df = conn.read(spreadsheet=url, ttl="0s")
                conn.update(spreadsheet=url, data=latest_df.drop(idx))
                st.session_state[temp_data_key] = None
                st.cache_data.clear()
                st.rerun()
