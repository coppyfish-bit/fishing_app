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
    # セッションキー
    temp_data_key = f"edit_temp_{idx}"
    debug_key = f"debug_log_{idx}"
    
    # --- 再取得ボタン ---
    if st.button(f"🔄 潮位が0になる原因を詳しく調べる", key=f"recalc_btn_{idx}"):
        try:
            logs = []
            raw_dt = str(df.at[idx, 'datetime']).strip()
            while raw_dt.endswith(":"): raw_dt = raw_dt[:-1]
            dt_obj = pd.to_datetime(raw_dt)
            
            logs.append(f"📅 検索日時: {dt_obj}")
            
            lat = float(df.at[idx, 'lat'])
            lon = float(df.at[idx, 'lon'])
            station = station_func(lat, lon)
            logs.append(f"📍 観測所: {station['name']} ({station['code']})")
            
            # 潮汐関数を直接叩く
            d_data = tide_func(station['code'], dt_obj)
            logs.append(f"📦 取得された生データ: {d_data}")
            
            # 気象
            temp, w_s, w_d, rain = weather_func(lat, lon, dt_obj)
            
            # 結果をセッションに保存（rerunしない！）
            st.session_state[temp_data_key] = {
                "temp": temp, "wind_s": w_s, "wind_d": w_d, "rain": rain,
                "tide_cm": d_data.get('cm', 0) if isinstance(d_data, dict) else 0,
                "tide_name": tide_name_func(moon_func(dt_obj)),
                "phase": d_data.get('phase', "不明") if isinstance(d_data, dict) else "不明"
            }
            st.session_state[debug_key] = logs
            # st.rerun() をあえて消しました。その場で結果を表示するためです。
        except Exception as e:
            st.error(f"❌ エラー発生: {e}")

    # デバッグログがセッションにあれば表示
    if debug_key in st.session_state:
        with st.expander("🔍 診断レポート（ここを確認してください）", expanded=True):
            for log in st.session_state[debug_key]:
                st.write(log)
            if "生データ: None" in str(st.session_state[debug_key]) or "{'cm': 0" in str(st.session_state[debug_key]):
                st.error("❗ 潮位データが取得できていません。GitHubのJSONに2026年のデータがない可能性があります。")

    # --- フォーム表示 ---
    t_data = st.session_state.get(temp_data_key, {})
    has_new = temp_data_key in st.session_state
    def get_v(key, col, default):
        if has_new and key in t_data: return t_data[key]
        return df.at[idx, col] if col in df.columns and pd.notna(df.at[idx, col]) else default

    with st.form(key=f"form_{idx}"):
        st.write(f"ID:{idx} の編集")
        # （中略：前回のフォーム入力項目と同じ）
        new_fish = st.text_input("魚種", value=str(df.at[idx, '魚種']))
        new_temp = st.number_input("気温", value=float(get_v("temp", "気温", 0.0)))
        new_tide_cm = st.number_input("潮位_cm", value=int(get_v("tide_cm", "潮位_cm", 0)))
        
        if st.form_submit_button("✅ この内容で保存"):
            # 保存処理...
            st.success("保存完了")
