import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import traceback

# [2026-02-27] AIとの会話や釣果情報は外部に漏洩・学習利用・共有されることはありません。

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

    # --- 再計算ロジック ---
    if st.button(f"🔄 気象・潮汐データを再計算する", key=f"recalc_btn_{idx}", use_container_width=True):
        try:
            with st.status("データ再計算中...", expanded=True):
                raw_dt = str(df.at[idx, 'datetime']).strip()
                dt_obj = pd.to_datetime(raw_dt)
                
                lat, lon = float(df.at[idx, 'lat']), float(df.at[idx, 'lon'])
                station = station_func(lat, lon)
                
                temp, w_s, w_d, rain = weather_func(lat, lon, dt_obj)
                
                # 潮汐詳細（潮位・フェーズ・イベント）を取得
                d_data = tide_func(station['code'], dt_obj) 
                
                if d_data is None:
                    st.error("潮汐データの取得に失敗しました。")
                    return

                # 月齢と潮名の計算
                m_age = moon_func(dt_obj) # ここで _age 等のミスがないよう注意
                t_name = tide_name_func(m_age)
                
                # 計算結果をセッションに一時保存
                st.session_state[temp_data_key] = {
                    "気温": temp, "風速": w_s, "風向": w_d, "降水量": rain,
                    "潮位_cm": d_data.get('cm', 0),
                    "月齢": m_age,
                    "潮名": t_name,
                    "潮位フェーズ": d_data.get('phase', "不明"),
                    "観測所": station['name']
                }
                st.session_state[form_ver_key] += 1
                st.success("再計算完了！")
                st.rerun()
        except Exception as e:
            st.error(f"❌ 取得エラー: {e}")
            st.code(traceback.format_exc())

    # --- フォーム表示 ---
    t_v = st.session_state.get(temp_data_key, {})
    has_new = temp_data_key in st.session_state

    def get_v(key, col, default):
        if has_new and key in t_v: return t_v[key]
        return df.at[idx, col] if col in df.columns and pd.notna(df.at[idx, col]) else default

    ver = st.session_state[form_ver_key]
    with st.form(key=f"edit_form_{idx}_v{ver}"):
        st.write(f"📝 ID:{idx} のデータを編集")
        
        c_f, c_l, c_p = st.columns([2, 1, 2])
        new_fish = c_f.text_input("魚種", value=str(df.at[idx, '魚種']))
        new_len = c_l.number_input("全長(cm)", value=float(df.at[idx, '全長_cm']) if '全長_cm' in df.columns else 0.0)
        new_place = c_p.text_input("場所", value=str(df.at[idx, '場所']))
        
        c1, c2, c3, c4 = st.columns(4)
        new_temp = c1.number_input("気温", value=float(get_v("気温", "気温", 0.0)))
        new_wind_s = c2.number_input("風速", value=float(get_v("風速", "風速", 0.0)))
        new_wind_d = c3.text_input("風向", value=str(get_v("風向", "風向", "不明")))
        new_rain = c4.number_input("降水量", value=float(get_v("降水量", "降水量", 0.0)))
        
        c5, c6, c7 = st.columns(3)
        new_tide_cm = c5.number_input("潮位_cm", value=int(get_v("潮位_cm", "潮位_cm", 0)))
        new_tide_name = c6.text_input("潮名", value=str(get_v("潮名", "潮名", "不明")))
        new_moon_age = c7.number_input("月齢", value=float(get_v("月齢", "月齢", 0.0)))
        
        new_phase = st.text_input("潮位フェーズ", value=str(get_v("潮位フェーズ", "潮位フェーズ", "不明")))
        new_lure = st.text_input("ルアー", value=str(df.at[idx, 'ルアー']) if 'ルアー' in df.columns else "")
        new_memo = st.text_area("備考", value=str(df.at[idx, '備考']) if '備考' in df.columns else "")
        
        st.divider()
        confirm_del = st.checkbox("このデータを完全に削除する")
        c_save, c_del = st.columns(2)
        
        if c_save.form_submit_button("✅ 更新内容を保存", use_container_width=True):
            latest_df = conn.read(spreadsheet=url, ttl="0s")
            updates = {
                '魚種': new_fish, '全長_cm': new_len, '場所': new_place,
                '気温': new_temp, '風速': new_wind_s, '風向': new_wind_d, '降水量': new_rain,
                '潮位_cm': new_tide_cm, '潮名': new_tide_name, '月齢': new_moon_age,
                '潮位フェーズ': new_phase, 'ルアー': new_lure, '備考': new_memo
            }
            for col, val in updates.items():
                if col in latest_df.columns:
                    latest_df.at[idx, col] = val
            
            conn.update(spreadsheet=url, data=latest_df)
            st.cache_data.clear()
            st.success("更新しました！")
            st.rerun()

        if c_del.form_submit_button("🗑️ 削除", type="primary"):
            if confirm_del:
                latest_df = conn.read(spreadsheet=url, ttl="0s")
                latest_df = latest_df.drop(idx).reset_index(drop=True)
                conn.update(spreadsheet=url, data=latest_df)
                st.cache_data.clear()
                st.rerun()
