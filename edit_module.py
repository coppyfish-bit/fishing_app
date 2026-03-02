import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# ★ ここには絶対に app を import しない！

def show_edit_page(conn, url, weather_func, station_func, tide_func, moon_func, tide_name_func):
    st.subheader("🔄 登録情報の修正・削除")
    # 最新データの読み込み
    df_raw = conn.read(spreadsheet=url, ttl="10s")
    if df_raw.empty:
        st.info("データがありません。")
        return
    
    # 全体を最新順に並び替え
    df = df_raw.iloc[::-1].copy()

    # --- 1. 直近5件の表示（展開状態） ---
    st.markdown("### 📸 直近5件の記録")
    df_recent = df.head(5)
    for idx in df_recent.index:
        dt_val = df.at[idx, 'datetime']
        dt_str = dt_val.strftime('%Y/%m/%d %H:%M') if isinstance(dt_val, pd.Timestamp) else str(dt_val)
        
        label = f"✨ 最新: {dt_str} | {df.at[idx, '場所']} | {df.at[idx, '魚種']}"
        with st.expander(label, expanded=True):
            render_edit_form(df, idx, conn, url, weather_func, station_func, tide_func, moon_func, tide_name_func)

    st.markdown("---")

    # --- 2. 過去データの選択編集（リストから選択） ---
    st.markdown("### 🔍 過去のデータをリストから選んで編集")
    df['select_label'] = df['datetime'].astype(str) + " | " + df['場所'].astype(str) + " | " + df['魚種'].astype(str)
    
    selected_label = st.selectbox(
        "編集したいデータを選択してください",
        options=df['select_label'].tolist(),
        index=None,
        placeholder="ここをクリックして検索・選択..."
    )

    if selected_label:
        selected_idx = df[df['select_label'] == selected_label].index[0]
        st.info(f"選択中: {selected_label}")
        render_edit_form(df, selected_idx, conn, url, weather_func, station_func, tide_func, moon_func, tide_name_func)

def render_edit_form(df, idx, conn, url, weather_func, station_func, tide_func, moon_func, tide_name_func):
    if 'filename' in df.columns and pd.notna(df.at[idx, 'filename']):
        st.image(df.at[idx, 'filename'], width=400)
    
    temp_data_key = f"temp_recalc_{idx}"
    form_version_key = f"form_ver_{idx}"
    
    if form_version_key not in st.session_state:
        st.session_state[form_version_key] = 0

    if st.button(f"🔄 気象・潮汐データを再取得する", key=f"btn_{idx}", use_container_width=True):
        try:
            with st.spinner("最新データを計算中..."):
                raw_val = str(df.at[idx, 'datetime']).replace("-", "/").strip()
                clean_dt_str = raw_val[:16]
                if clean_dt_str.endswith(":"):
                    clean_dt_str = clean_dt_str[:-1]
                
                try:
                    dt_obj = datetime.strptime(clean_dt_str, '%Y/%m/%d %H:%M')
                except:
                    dt_obj = pd.to_datetime(clean_dt_str)
                
                lat, lon = float(df.at[idx, 'lat']), float(df.at[idx, 'lon'])
                
                # ★受け取った関数をそのまま使う！
                temp, w_s, w_d, rain = weather_func(lat, lon, dt_obj)
                station = station_func(lat, lon)
                
                all_events = []
                tide_cm = 0
                for delta in [-1, 0, 1]:
                    # ★受け取った関数を使う
                    d_data = tide_func(station['code'], dt_obj + timedelta(days=delta))
                    if d_data:
                        if 'events' in d_data: all_events.extend(d_data['events'])
                        if delta == 0: tide_cm = d_data['cm']

                all_events = sorted({ev['time']: ev for ev in all_events}.values(), key=lambda x: x['time'])
                
                tide_phase = "不明"
                search_dt = dt_obj + timedelta(minutes=5)
                prev_ev = next((e for e in reversed(all_events) if e['time'] <= search_dt), None)
                next_ev = next((e for e in all_events if e['time'] > search_dt), None)
                
                if prev_ev and next_ev:
                    duration = (next_ev['time'] - prev_ev['time']).total_seconds()
                    elapsed = (dt_obj - prev_ev['time']).total_seconds()
                    if duration > 0:
                        p_type = "上げ" if "干" in prev_ev['type'] else "下げ"
                        step = max(1, min(9, int((elapsed / duration) * 10)))
                        tide_phase = f"{p_type}{step}分"

                # ★受け取った関数をそのまま使う！
                st.session_state[temp_data_key] = {
                    "temp": temp, "wind_s": w_s, "wind_d": w_d, "rain": rain,
                    "tide_cm": tide_cm,
                    "tide_name": tide_name_func(moon_func(dt_obj)),
                    "phase": tide_phase
                }
                st.session_state[form_version_key] += 1
                st.rerun() 
        except Exception as e:
            st.error(f"再取得エラー: {e}")

    # (修正フォーム部分は省略。前回と同じでOK)
    # ... (前回の修正コードのフォーム部分をここに配置) ...
    has_temp_data = temp_data_key in st.session_state and st.session_state[temp_data_key] is not None
    t_data = st.session_state.get(temp_data_key, {})
    try:
        val_temp = float(t_data["temp"]) if has_temp_data else float(df.at[idx, '気温'])
        val_wind_s = float(t_data["wind_s"]) if has_temp_data else float(df.at[idx, '風速'])
        val_wind_d = t_data["wind_d"] if has_temp_data else (str(df.at[idx, '風向']) if '風向' in df.columns else "不明")
        val_rain = float(t_data["rain"]) if has_temp_data else (float(df.at[idx, '降水量']) if '降水量' in df.columns else 0.0)
        val_tide_cm = int(t_data["tide_cm"]) if has_temp_data else int(df.at[idx, '潮位_cm'])
        val_tide_name = t_data["tide_name"] if has_temp_data else (str(df.at[idx, '潮名']) if '潮名' in df.columns else "不明")
        val_phase = t_data["phase"] if has_temp_data else (str(df.at[idx, '潮位フェーズ']) if '潮位フェーズ' in df.columns else "不明")
    except:
        val_temp, val_wind_s, val_wind_d, val_rain, val_tide_cm, val_tide_name, val_phase = 0, 0, "不明", 0, 0, "不明", "不明"

    ver = st.session_state[form_version_key]
    with st.form(key=f"form_{idx}_v{ver}"):
        st.write("📝 **データの修正**")
        col_f, col_l, col_p = st.columns([2, 1, 2])
        new_fish = col_f.text_input("魚種", value=df.at[idx, '魚種'])
        new_len = col_l.number_input("全長(cm)", value=float(df.at[idx, '全長_cm']), step=0.1)
        new_place = col_p.text_input("場所", value=df.at[idx, '場所'])
        c1, c2, c3 = st.columns(3)
        new_temp = c1.number_input("気温(℃)", value=val_temp)
        new_wind_s = c2.number_input("風速(m)", value=val_wind_s)
        new_wind_d = c3.text_input("風向", value=val_wind_d)
        c4, c5, c6 = st.columns(3)
        new_rain = c4.number_input("降水(48h)", value=val_rain)
        new_tide_cm = c5.number_input("潮位(cm)", value=val_tide_cm)
        new_tide_name = c6.text_input("潮名", value=val_tide_name)
        new_phase = st.text_input("潮位フェーズ", value=val_phase)
        new_memo = st.text_area("備考", value=df.at[idx, '備考'] if pd.notna(df.at[idx, '備考']) else "")
        st.markdown("---")
        confirm_delete = st.checkbox("このデータを完全に削除する", key=f"del_check_{idx}")
        c_save, c_del = st.columns(2)
        if c_save.form_submit_button("✅ 更新内容を保存する", use_container_width=True):
            df_to_save = conn.read(spreadsheet=url, ttl="0s")
            df_to_save.at[idx, '魚種'] = new_fish
            df_to_save.at[idx, '全長_cm'] = new_len
            df_to_save.at[idx, '場所'] = new_place
            df_to_save.at[idx, '気温'] = new_temp
            df_to_save.at[idx, '風速'] = new_wind_s
            if '風向' in df_to_save.columns: df_to_save.at[idx, '風向'] = new_wind_d
            if '降水量' in df_to_save.columns: df_to_save.at[idx, '降水量'] = new_rain
            df_to_save.at[idx, '潮位_cm'] = new_tide_cm
            if '潮名' in df_to_save.columns: df_to_save.at[idx, '潮名'] = new_tide_name
            if '潮位フェーズ' in df_to_save.columns: df_to_save.at[idx, '潮位フェーズ'] = new_phase
            df_to_save.at[idx, '備考'] = new_memo
            conn.update(spreadsheet=url, data=df_to_save)
            st.session_state[temp_data_key] = None
            st.cache_data.clear()
            st.success("修正を保存しました！")
            st.rerun()
        if c_del.form_submit_button("🗑️ 削除実行", type="primary", use_container_width=True):
            if confirm_delete:
                df_to_save = conn.read(spreadsheet=url, ttl="0s")
                df_to_save = df_to_save.drop(idx)
                conn.update(spreadsheet=url, data=df_to_save)
                st.session_state[temp_data_key] = None
                st.cache_data.clear()
                st.rerun()
