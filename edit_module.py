import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

def show_edit_page(conn, url, weather_func, station_func, tide_func, moon_func, tide_name_func):
    st.subheader("🔄 登録情報の修正・削除")
    df_raw = conn.read(spreadsheet=url, ttl="10s")
    if df_raw.empty:
        st.info("データがありません。")
        return
    
    df = df_raw.iloc[::-1].copy()

    st.markdown("### 📸 直近5件の記録")
    df_recent = df.head(5)
    for idx in df_recent.index:
        dt_val = df.at[idx, 'datetime']
        dt_str = dt_val.strftime('%Y/%m/%d %H:%M') if isinstance(dt_val, pd.Timestamp) else str(dt_val)
        label = f"✨ 最新: {dt_str} | {df.at[idx, '場所']} | {df.at[idx, '魚種']}"
        with st.expander(label, expanded=True):
            render_edit_form(df, idx, conn, url, weather_func, station_func, tide_func, moon_func, tide_name_func)

    st.markdown("---")
    st.markdown("### 🔍 過去のデータをリストから選んで編集")
    df['select_label'] = df['datetime'].astype(str) + " | " + df['場所'].astype(str) + " | " + df['魚種'].astype(str)
    selected_label = st.selectbox("編集したいデータを選択", options=df['select_label'].tolist(), index=None)

    if selected_label:
        selected_idx = df[df['select_label'] == selected_label].index[0]
        render_edit_form(df, selected_idx, conn, url, weather_func, station_func, tide_func, moon_func, tide_name_func)

def render_edit_form(df, idx, conn, url, weather_func, station_func, tide_func, moon_func, tide_name_func):
    if 'filename' in df.columns and pd.notna(df.at[idx, 'filename']):
        st.image(df.at[idx, 'filename'], width=400)
    
    temp_data_key = f"temp_recalc_{idx}"
    form_version_key = f"form_ver_{idx}"
    
    if form_version_key not in st.session_state:
        st.session_state[form_version_key] = 0

    # --- 再取得ボタン ---
    if st.button(f"🔄 気象・潮汐データを再取得する", key=f"btn_{idx}", use_container_width=True):
        try:
            with st.spinner("最新データを計算中..."):
                raw_val = str(df.at[idx, 'datetime']).replace("-", "/").strip()
                dt_obj = pd.to_datetime(raw_val[:16])
                lat, lon = float(df.at[idx, 'lat']), float(df.at[idx, 'lon'])
                
                # データ取得
                temp, w_s, w_d, rain = weather_func(lat, lon, dt_obj)
                station = station_func(lat, lon)
                d_data = tide_func(station['code'], dt_obj)
                
                # 辞書から取得
                t_cm = d_data.get('cm', 0) if isinstance(d_data, dict) else 0
                t_ph = d_data.get('phase', "不明") if isinstance(d_data, dict) else "不明"
                
                # セッション保存
                st.session_state[temp_data_key] = {
                    "temp": temp, "wind_s": w_s, "wind_d": w_d, "rain": rain,
                    "tide_cm": t_cm, "tide_name": tide_name_func(moon_func(dt_obj)), "phase": t_ph
                }
                # バージョンを上げることでフォームを強制再生成させる
                st.session_state[form_version_key] += 1
                st.rerun() 
        except Exception as e:
            st.error(f"再取得エラー: {e}")

    # --- 値の確定ロジック ---
    t_data = st.session_state.get(temp_data_key, {})
    has_new = temp_data_key in st.session_state and st.session_state[temp_data_key] is not None

    def val(k, col, d):
        return t_data[k] if has_new and k in t_data else (df.at[idx, col] if col in df.columns and pd.notna(df.at[idx, col]) else d)

    # フォームを表示（ver を key に含めることで、再取得時に中身が書き換わる）
    ver = st.session_state[form_version_key]
    with st.form(key=f"form_{idx}_v{ver}"):
        st.write("📝 **データの修正**")
        c_f, c_l, c_p = st.columns([2, 1, 2])
        new_fish = c_f.text_input("魚種", value=df.at[idx, '魚種'])
        new_len = c_l.number_input("全長(cm)", value=float(df.at[idx, '全長_cm']) if pd.notna(df.at[idx, '全長_cm']) else 0.0, step=0.1)
        new_place = c_p.text_input("場所", value=df.at[idx, '場所'])
        
        c1, c2, c3 = st.columns(3)
        new_temp = c1.number_input("気温(℃)", value=float(val("temp", "気温", 0.0)))
        new_wind_s = c2.number_number("風速(m)", value=float(val("wind_s", "風速", 0.0)))
        new_wind_d = c3.text_input("風向", value=str(val("wind_d", "風向", "不明")))
        
        c4, c5, c6 = st.columns(3)
        new_rain = c4.number_input("降水(48h)", value=float(val("rain", "降水量", 0.0)))
        new_tide_cm = c5.number_input("潮位(cm)", value=int(val("tide_cm", "潮位_cm", 0)))
        new_tide_name = c6.text_input("潮名", value=str(val("tide_name", "潮名", "不明")))
        
        new_phase = st.text_input("潮位フェーズ", value=str(val("phase", "潮位フェーズ", "不明")))
        new_memo = st.text_area("備考", value=df.at[idx, '備考'] if pd.notna(df.at[idx, '備考']) else "")
        
        st.markdown("---")
        confirm_delete = st.checkbox("このデータを完全に削除する", key=f"del_check_{idx}")
        c_save, c_del = st.columns(2)
        
        if c_save.form_submit_button("✅ 更新内容を保存する", use_container_width=True):
            df_to_save = conn.read(spreadsheet=url, ttl="0s")
            for col, v in [('魚種', new_fish), ('全長_cm', new_len), ('場所', new_place), ('気温', new_temp), ('風速', new_wind_s), ('風向', new_wind_d), ('降水量', new_rain), ('潮位_cm', new_tide_cm), ('潮名', new_tide_name), ('潮位フェーズ', new_phase), ('備考', new_memo)]:
                if col in df_to_save.columns: df_to_save.at[idx, col] = v
            conn.update(spreadsheet=url, data=df_to_save)
            st.session_state[temp_data_key] = None
            st.cache_data.clear()
            st.success("修正を保存しました！")
            st.rerun()
            
        if c_del.form_submit_button("🗑️ 削除実行", type="primary", use_container_width=True):
            if confirm_delete:
                df_to_save = conn.read(spreadsheet=url, ttl="0s")
                conn.update(spreadsheet=url, data=df_to_save.drop(idx))
                st.session_state[temp_data_key] = None
                st.cache_data.clear()
                st.rerun()
