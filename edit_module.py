import streamlit as st
import pandas as pd
from datetime import datetime
import traceback

def show_edit_page(conn, url, weather_func, station_func, tide_func, moon_func, tide_name_func):
    st.subheader("🔄 釣果レコードの修正・管理")
    
    # 最新のデータを取得
    df = conn.read(spreadsheet=url, ttl="0s")
    if df.empty:
        st.info("データがありません。")
        return

    # 新しい順に並び替え
    df_display = df.iloc[::-1]

    for idx in df_display.index:
        # レコードごとに一意のキーを作成
        record = df.loc[idx]
        
        # カード形式のコンテナ
        with st.container(border=True):
            col_img, col_info = st.columns([1, 2])
            
            with col_img:
                # 写真を表示
                img_url = record.get('filename', "")
                if img_url:
                    st.image(img_url, use_container_width=True)
                else:
                    st.warning("画像なし")
                
                st.caption(f"📅 {record.get('datetime', '不明')}")
                st.caption(f"📍 {record.get('場所', '不明')}")

            with col_info:
                st.write(f"### ID: {idx} | {record.get('魚種', '不明')}")
                
                # 編集フォームを展開（あらかじめ開いた状態にするためのexpander）
                with st.expander("📝 このレコードを編集する", expanded=False):
                    render_edit_form(df, idx, conn, url, weather_func, station_func, tide_func, moon_func, tide_name_func)

def render_edit_form(df, idx, conn, url, weather_func, station_func, tide_func, moon_func, tide_name_func):
    temp_data_key = f"edit_temp_{idx}"
    form_ver_key = f"edit_ver_{idx}"
    
    # デフォルト座標（本渡瀬戸）
    DEFAULT_LAT = 32.4539
    DEFAULT_LON = 130.2033
    
    if form_ver_key not in st.session_state:
        st.session_state[form_ver_key] = 0

    # --- 再計算ロジック ---
    if st.button(f"🔄 気象・潮汐を再計算(自動補完)", key=f"recalc_v2_{idx}", use_container_width=True):
        try:
            with st.spinner("最新ロジックで再計算中..."):
                # 1. 日時の取得
                raw_dt = str(df.at[idx, 'datetime']).strip()
                dt_obj = pd.to_datetime(raw_dt)
                
                # 2. 緯度・経度の取得（空の場合はデフォルト値を使用）
                try:
                    lat_val = df.at[idx, 'lat']
                    lon_val = df.at[idx, 'lon']
                    
                    # 値がNaN（空）または 0 の場合にデフォルトを割り当て
                    lat = float(lat_val) if pd.notna(lat_val) and lat_val != 0 else DEFAULT_LAT
                    lon = float(lon_val) if pd.notna(lon_val) and lon_val != 0 else DEFAULT_LON
                    
                    if lat == DEFAULT_LAT:
                        st.info("ℹ️ 座標データがないため、本渡瀬戸を基準に計算します。")
                except:
                    lat, lon = DEFAULT_LAT, DEFAULT_LON
                    st.info("ℹ️ 座標エラーのため、本渡瀬戸を基準に計算します。")
                
                # 3. 潮汐・気象データの取得
                station = station_func(lat, lon)
                temp, w_s, w_d, rain = weather_func(lat, lon, dt_obj)
                d_data = tide_func(station['code'], dt_obj) 
                
              # --- edit_page の再計算ロジック部分を修正 ---
                if d_data:
                    m_age = moon_func(dt_obj)
                    t_name = tide_name_func(m_age)
                    
                    # フェーズの取得を安全にする
                    raw_phase = d_data.get('phase', "不明")
                    # もしフェーズが「デバッグ中」や「Error」などの文字列なら「不明」に置き換えるガード
                    if "デバッグ" in raw_phase or "Error" in raw_phase:
                        raw_phase = "不明"
                
                    # 計算結果をセッションに一時保存
                    st.session_state[temp_data_key] = {
                        "気温": temp, "風速": w_s, "風向": w_d, "降水量": rain,
                        "潮位_cm": d_data.get('cm', 0),
                        "月齢": m_age, "潮名": t_name,
                        "潮位フェーズ": raw_phase # 安全な値を代入
                    st.session_state[form_ver_key] += 1
                    st.success("再計算が完了しました。保存ボタンを押すと確定します。")
                    st.rerun()
        except Exception as e:
            st.error(f"再計算エラー: {e}")

    # --- 入力フォーム ---
    t_v = st.session_state.get(temp_data_key, {})
    has_new = temp_data_key in st.session_state

    def get_v(key, col, default):
        if has_new and key in t_v: return t_v[key]
        val = df.at[idx, col] if col in df.columns else default
        return val if pd.notna(val) else default

    ver = st.session_state[form_ver_key]
    with st.form(key=f"edit_form_final_{idx}_{ver}"):
        c1, c2, c3 = st.columns([2, 1, 2])
        new_fish = c1.text_input("🐟 魚種", value=str(df.at[idx, '魚種']))
        new_len = c2.number_input("📏 全長(cm)", value=float(get_v(None, '全長_cm', 0.0)))
        new_place = c3.text_input("📍 場所", value=str(df.at[idx, '場所']))

        c_w1, c_w2, c_w3, c_w4 = st.columns(4)
        new_temp = c_w1.number_input("🌡️ 気温", value=float(get_v("気温", "気温", 0.0)))
        new_wind_s = c_w2.number_input("💨 風速", value=float(get_v("風速", "風速", 0.0)))
        new_wind_d = c_w3.text_input("🧭 風向", value=str(get_v("風向", "風向", "不明")))
        new_rain = c_w4.number_input("☔ 降水", value=float(get_v("降水量", "降水量", 0.0)))

        c_t1, c_t2, c_t3 = st.columns(3)
        new_tide_cm = c_t1.number_input("🌊 潮位cm", value=int(get_v("潮位_cm", "潮位_cm", 0)))
        new_tide_name = c_t2.text_input("🌊 潮名", value=str(get_v("潮名", "潮名", "不明")))
        new_moon_age = c_t3.number_input("🌙 月齢", value=float(get_v("月齢", "月齢", 0.0)))

        new_phase = st.text_input("📈 潮位フェーズ", value=str(get_v("潮位フェーズ", "潮位フェーズ", "不明")))
        new_lure = st.text_input("🪝 ルアー", value=str(df.at[idx, 'ルアー']) if 'ルアー' in df.columns else "")
        new_memo = st.text_area("🗒️ 備考", value=str(df.at[idx, '備考']) if '備考' in df.columns else "")

        # 保存・削除ボタン
        st.divider()
        confirm_del = st.checkbox(f"ID:{idx} を完全に削除する", key=f"del_check_{idx}")
        btn_save, btn_del = st.columns(2)
        
        if btn_save.form_submit_button("💾 修正を保存", use_container_width=True, type="primary"):
            latest_df = conn.read(spreadsheet=url, ttl="0s")
            # データの更新
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
            st.success("保存完了！")
            st.rerun()

        if btn_del.form_submit_button("🗑️ 削除実行", use_container_width=True):
            if confirm_del:
                latest_df = conn.read(spreadsheet=url, ttl="0s")
                latest_df = latest_df.drop(idx).reset_index(drop=True)
                conn.update(spreadsheet=url, data=latest_df)
                st.cache_data.clear()
                st.rerun()
            else:
                st.warning("削除する場合はチェックを入れてください。")



