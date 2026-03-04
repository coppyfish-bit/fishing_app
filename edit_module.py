import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# AIとの会話は学習に使用したり外部に漏れたりしません。釣果情報も共有しません。

def show_edit_page(conn, url, weather_func, station_func, tide_func, moon_func, tide_name_func):
    st.subheader("🛠️ デバッグモード：登録情報の修正")
    df = conn.read(spreadsheet=url, ttl="0s")
    if df.empty:
        st.info("データがありません。")
        return

    df_reversed = df.iloc[::-1]
    labels = [f"ID:{i} | {df.at[i, 'datetime']} | {df.at[i, '場所']}" for i in df_reversed.index]
    selected_label = st.selectbox("デバッグするデータを選択", options=labels, index=None)

    if selected_label:
        target_idx = int(selected_label.split('|')[0].replace('ID:', '').strip())
        render_debug_form(df, target_idx, conn, url, weather_func, station_func, tide_func, moon_func, tide_name_func)

def render_debug_form(df, idx, conn, url, weather_func, station_func, tide_func, moon_func, tide_name_func):
    temp_data_key = f"debug_val_{idx}"
    
    # --- 🔍 デバッグ専用：再取得ボタン ---
    if st.button("🚀 潮位取得の全工程を追跡する", key=f"debug_btn_{idx}", type="primary"):
        with st.container(border=True):
            st.write("### 🛠️ 実行ログ")
            try:
                # 1. 日時の検証
                raw_dt = str(df.at[idx, 'datetime']).strip()
                dt_obj = pd.to_datetime(raw_dt)
                st.write(f"1. 検索日時: `{dt_obj}` (Type: {type(dt_obj)})")

                # 2. 観測所の検証
                lat, lon = float(df.at[idx, 'lat']), float(df.at[idx, 'lon'])
                station = station_func(lat, lon)
                st.write(f"2. 観測所判定: `{station['name']}` (Code: `{station['code']}`)")

                # 3. 潮汐関数の内部をシミュレート
                st.write("3. 潮汐データ取得中...")
                d_data = tide_func(station['code'], dt_obj)
                
                # 4. 生データの詳細表示
                st.write("---")
                st.write("#### 📦 取得されたデータの詳細")
                st.json(d_data) # ここで関数の戻り値をすべて表示
                
                if d_data and d_data.get('cm') == 0:
                    st.error("❗ 潮位が0です。JSON内にこの日時のデータが存在しないか、計算ロジックがスルーされています。")
                
                # 5. 気象等もついでに取得
                temp, w_s, w_d, rain = weather_func(lat, lon, dt_obj)
                t_name = tide_name_func(moon_func(dt_obj))

                # セッション保存（rerunはしない）
                st.session_state[temp_data_key] = {
                    "temp": temp, "wind_s": w_s, "wind_d": w_d, "rain": rain,
                    "tide_cm": d_data.get('cm', 0) if d_data else 0,
                    "tide_name": t_name, "phase": d_data.get('phase', "不明") if d_data else "不明"
                }
                st.success("取得シミュレーション完了。下のフォームに値を反映できます。")

            except Exception as e:
                st.exception(e)

    # --- 📝 編集フォーム ---
    t_v = st.session_state.get(temp_data_key, {})
    
    with st.form(key=f"debug_form_{idx}"):
        st.info("デバッグ結果を反映中（保存するまでスプレッドシートには書き込まれません）")
        
        c1, c2, c3 = st.columns(3)
        # 再取得データがあればそれ、なければ既存値を初期値にする
        new_temp = c1.number_input("気温", value=float(t_v.get("temp", df.at[idx, "気温"] if "気温" in df.columns else 0.0)))
        new_tide_cm = c2.number_input("潮位_cm", value=int(t_v.get("tide_cm", df.at[idx, "潮位_cm"] if "潮位_cm" in df.columns else 0)))
        new_phase = c3.text_input("潮位フェーズ", value=str(t_v.get("phase", df.at[idx, "潮位フェーズ"] if "潮位フェーズ" in df.columns else "不明")))
        
        new_memo =
