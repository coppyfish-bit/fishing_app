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
    temp_data_key = f"edit_temp_{idx}"
    form_ver_key = f"edit_ver_{idx}"
    
    if form_ver_key not in st.session_state:
        st.session_state[form_ver_key] = 0

    # --- 再取得ボタン ---
    if st.button(f"🔄 気象・潮汐データを再取得する", key=f"recalc_btn_{idx}", use_container_width=True):
        try:
            with st.status("データ解析中...", expanded=True) as status:
                # 1. 日時のクリーニング
                raw_dt = str(df.at[idx, 'datetime']).strip()
                while raw_dt.endswith(":"): raw_dt = raw_dt[:-1]
                dt_obj = pd.to_datetime(raw_dt)
                
                lat = float(df.at[idx, 'lat'])
                lon = float(df.at[idx, 'lon'])
                
                # 2. 気象・潮汐の取得
                # ※ app.py側のtide_func内でエラーが起きるのを防ぐため、
                # 呼び出しをtry-exceptで包むか、app.py側の修正が必要です。
                temp, w_s, w_d, rain = weather_func(lat, lon, dt_obj)
                station = station_func(lat, lon)
                
                # ここでapp.pyのtide_func（JSON解析）が走ります
                d_data = tide_func(station['code'], dt_obj)
                
                t_cm = d_data.get('cm', 0) if isinstance(d_data, dict) else 0
                t_ph = d_data.get('phase', "不明") if isinstance(d_data, dict) else "不明"
                t_name = tide_name_func(moon_func(dt_obj))
                
                # 結果をセッションに保存
                st.session_state[temp_data_key] = {
                    "temp": temp, "wind_s": w_s, "wind_d": w_d, "rain": rain,
                    "tide_cm": t_cm, "tide_name": t_name, "phase": t_ph
                }
                st.session_state[form_ver_key] += 1
                status.update(label="取得完了！", state="complete")
                st.write(f"🔍 検索対象日時: {dt_obj}")
                st.rerun()
        except Exception as e:
            st.error(f"❌ 解析エラー: {e}")
            st.info("💡 JSONデータ内に '10: 6' のような不正な空白が含まれているようです。app.py の get_tide_details 内で .replace(' ', '') を適用する必要があります。")

    # --- フォーム表示 ---
    t_data = st.session_state.get(temp_data_key, {})
    has_new = temp_data_key in st.session_state

    def get_v(key, col, default):
        if has_new and key in t_data: return t_data[key]
        return df.at[idx, col] if col in df.columns and pd.notna(df.at[idx, col]) else default

    ver = st.session_state[form_ver_key]
    with st.form(key=f"edit_form_{idx}_v{ver}"):
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
        
        if st.form_submit_button("✅ 更新内容を保存する", use_container_width=True):
            latest_df = conn.read(spreadsheet=url, ttl="0s")
            update_map = {'魚種': new_fish, '全長_cm': new_len, '場所': new_place, '気温': new_temp, '風速': new_wind_s, '風向': new_wind_d, '降水量': new_rain, '潮位_cm': new_tide_cm, '潮名': new_tide_name, '潮位フェーズ': new_phase, '備考': new_memo}
            for col, val in update_map.items():
                if col in latest_df.columns: latest_df.at[idx, col] = val
            conn.update(spreadsheet=url, data=latest_df)
            st.session_state[temp_data_key] = None
            st.cache_data.clear()
            st.success("保存完了！")
            st.rerun()

