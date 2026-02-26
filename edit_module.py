import streamlit as st
import pandas as pd
from datetime import datetime

def show_edit_page(conn, url):
    st.subheader("🔄 登録情報の修正・削除")
    df = conn.read(spreadsheet=url, ttl=300)
    if df.empty:
        st.info("データがありません。")
        return
    df = df.iloc[::-1].copy()

    st.markdown("### 📸 最近の記録を修正")
    df_recent = df.head(5)
    for idx in df_recent.index:
        label = f"✨ 最新: {df.at[idx, 'datetime']} | {df.at[idx, '場所']} | {df.at[idx, '魚種']}"
        with st.expander(label, expanded=True):
            render_edit_form(df, idx, conn, url)

# --- 共通の修正フォーム関数 ---
def render_edit_form(df, idx, conn, url):
    if 'filename' in df.columns and df.at[idx, 'filename']:
        st.image(df.at[idx, 'filename'], width=400)
    
    # セッション状態のキー
    temp_data_key = f"temp_recalc_{idx}"
    # フォームを強制リセットするためのカウンター
    form_version_key = f"form_ver_{idx}"
    
    if form_version_key not in st.session_state:
        st.session_state[form_version_key] = 0

    st.write("💡 **データが正しくない場合はこちら**")
    
    # --- 🔄 再取得ボタン ---
    if st.button(f"🔄 気象・潮汐データを再取得する", key=f"btn_{idx}", use_container_width=True):
        try:
            with st.spinner("最新データを取得中..."):
                import app
                raw_dt = str(df.at[idx, 'datetime']).replace("-", "/").strip()
                parts = raw_dt.split(":")
                clean_dt_str = f"{parts[0]}:{parts[1]}" if len(parts) > 2 else raw_dt
                dt_obj = datetime.strptime(clean_dt_str, '%Y/%m/%d %H:%M')
                
                lat, lon = float(df.at[idx, 'lat']), float(df.at[idx, 'lon'])
                temp, wind_s, wind_d, rain = app.get_weather_data_openmeteo(lat, lon, dt_obj)
                station = app.find_nearest_tide_station(lat, lon)
                tide_res = app.get_tide_details(station['code'], dt_obj)
                
                # セッションに保存
                st.session_state[temp_data_key] = {
                    "temp": temp, "wind": wind_s, "rain": rain,
                    "tide": tide_res['cm'] if tide_res else 0,
                    "phase": tide_res.get('phase', "不明") if tide_res else "不明"
                }
                # 【重要】フォームのバージョンを上げて強制リセットをかける
                st.session_state[form_version_key] += 1
                st.success("取得完了！値を反映しました。")
                st.rerun() 

        except Exception as e:
            st.error(f"エラー: {e}")

    # 表示する値の決定
    has_temp_data = temp_data_key in st.session_state and st.session_state[temp_data_key] is not None
    t_data = st.session_state.get(temp_data_key, {})

    val_temp = float(t_data["temp"]) if has_temp_data else float(df.at[idx, '気温'])
    val_wind = float(t_data["wind"]) if has_temp_data else float(df.at[idx, '風速'])
    val_rain = float(t_data["rain"]) if has_temp_data else (float(df.at[idx, '降水量']) if '降水量' in df.columns else 0.0)
    val_tide = int(t_data["tide"]) if has_temp_data else int(df.at[idx, '潮位_cm'])
    val_phase = t_data["phase"] if has_temp_data else (str(df.at[idx, '潮位フェーズ']) if '潮位フェーズ' in df.columns else "")

    # --- 修正フォーム本体 ---
    # keyにform_versionを混ぜることで、再取得時に「全く別のフォーム」として認識させる
    ver = st.session_state[form_version_key]
    with st.form(key=f"form_{idx}_v{ver}"):
        st.write("📝 **釣果・環境データ**")
        col1, col2, col3 = st.columns([2, 1, 2])
        new_fish = col1.text_input("魚種", value=df.at[idx, '魚種'])
        new_len = col2.number_input("全長", value=float(df.at[idx, '全長_cm']), step=0.1)
        new_place = col3.text_input("場所", value=df.at[idx, '場所'])
        
        c1, c2, c3, c4, c5 = st.columns(5)
        new_temp = c1.number_input("気温", value=val_temp)
        new_wind = c2.number_input("風速", value=val_wind)
        new_rain = c3.number_input("降水", value=val_rain)
        new_tide = c4.number_input("潮位", value=val_tide)
        new_phase = c5.text_input("フェーズ", value=val_phase)
        
        new_memo = st.text_area("備考", value=df.at[idx, '備考'] if pd.notna(df.at[idx, '備考']) else "")

        if st.form_submit_button("✅ 更新内容を保存する", use_container_width=True):
            df.at[idx, '魚種'] = new_fish
            df.at[idx, '全長_cm'] = new_len
            df.at[idx, '場所'] = new_place
            df.at[idx, '気温'] = new_temp
            df.at[idx, '風速'] = new_wind
            if '降水量' in df.columns: df.at[idx, '降水量'] = new_rain
            df.at[idx, '潮位_cm'] = new_tide
            df.at[idx, '潮位フェーズ'] = new_phase
            df.at[idx, '備考'] = new_memo
            
            save_df = df.drop(columns=['search_label']) if 'search_label' in df.columns else df
            conn.update(spreadsheet=url, data=save_df.iloc[::-1])
            
            # 完了後リセット
            st.session_state[temp_data_key] = None
            st.cache_data.clear()
            st.success("保存しました！")
            st.rerun()
