import streamlit as st
import pandas as pd
from datetime import datetime
import traceback

# AIとの会話は学習に使用したり外部に漏れたりしません。釣果情報も共有しません。

def show_edit_page(conn, url, weather_func, station_func, tide_func, moon_func, tide_name_func):
    st.subheader("🔄 登録情報の修正・削除")
    
    # 最新データを読み込み
    df = conn.read(spreadsheet=url, ttl="0s")
    
    if df.empty:
        st.info("データがありません。")
        return

    # ID（インデックス）を逆順にして、新しい順に選択肢を作成
    df_reversed = df.iloc[::-1]
    labels = [f"ID:{i} | {df.at[i, 'datetime']} | {df.at[i, '場所']}" for i in df_reversed.index]
    
    selected_label = st.selectbox("編集したいデータを選んでください", options=labels, index=None, key="selector_main")

    if selected_label:
        # IDを取り出す
        target_idx = int(selected_label.split('|')[0].replace('ID:', '').strip())
        st.divider()
        render_edit_form(df, target_idx, conn, url, weather_func, station_func, tide_func, moon_func, tide_name_func)

def render_edit_form(df, idx, conn, url, weather_func, station_func, tide_func, moon_func, tide_name_func):
    # セッション状態のキー定義
    temp_data_key = f"edit_temp_{idx}"
    form_ver_key = f"edit_ver_{idx}"
    
    if form_ver_key not in st.session_state:
        st.session_state[form_ver_key] = 0

    # --- 再取得ボタン ---
    if st.button(f"🔄 気象・潮汐データを再計算する", key=f"recalc_btn_{idx}", use_container_width=True):
        try:
            with st.status("最新データ（GitHub & 気象API）から取得中...", expanded=True):
                # 1. 日時のパース
                raw_dt = str(df.at[idx, 'datetime']).strip()
                # 予期せぬゴミ取り
                while raw_dt.endswith(":"): raw_dt = raw_dt[:-1]
                dt_obj = pd.to_datetime(raw_dt)
                
                # 2. 座標の取得
                lat, lon = float(df.at[idx, 'lat']), float(df.at[idx, 'lon'])
                
                # 3. 各関数の実行
                temp, w_s, w_d, rain = weather_func(lat, lon, dt_obj)
                station = station_func(lat, lon)
                
                # --- 潮位取得 (GitHub連携) ---
                # app.py側の get_tide_details の仕様 (Response または URL を受け取る) に合わせる
                t_url = f"https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{dt_obj.year}/{station['code']}.json"
                
                # ここで直接解析関数を呼ぶ（tide_func = get_tide_details）
                d_data = tide_func(t_url, dt_obj) 
                
                t_name = tide_name_func(moon_func(dt_obj))
                
                # 4. セッション保存（フォームのデフォルト値を書き換えるため）
                st.session_state[temp_data_key] = {
                    "temp": temp, "wind_s": w_s, "wind_d": w_d, "rain": rain,
                    "tide_cm": d_data.get('cm', 0),
                    "tide_name": t_name,
                    "phase": d_data.get('phase', "不明")
                }
                st.session_state[form_ver_key] += 1
                st.success("再計算が完了しました！下のフォームに反映されています。")
                st.rerun()
        except Exception as e:
            st.error(f"❌ 取得エラー: {e}")
            st.code(traceback.format_exc())

    # --- フォーム表示 ---
    t_v = st.session_state.get(temp_data_key, {})
    has_new = temp_data_key in st.session_state

    # 新しく計算された値があればそれを選び、なければ既存のDFから取る関数
    def get_v(key, col, default):
        if has_new and key in t_v:
            return t_v[key]
        return df.at[idx, col] if col in df.columns and pd.notna(df.at[idx, col]) else default

    # フォームの「バージョン」を上げることで、初期値を強制的に更新する仕組み
    ver = st.session_state[form_ver_key]
    with st.form(key=f"edit_form_{idx}_v{ver}"):
        st.write(f"📝 ID:{idx} のデータを編集")
        
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
        
        st.divider()
        confirm_del = st.checkbox("⚠️ このデータを完全に削除する")
        c_save, c_del = st.columns(2)
        
        # 保存処理
        if c_save.form_submit_button("✅ 更新内容を保存", use_container_width=True):
            latest_df = conn.read(spreadsheet=url, ttl="0s")
            
            # 書き換えデータのマッピング
            updates = {
                '魚種': new_fish, '全長_cm': new_len, '場所': new_place,
                '気温': new_temp, '風速': new_wind_s, '風向': new_wind_d,
                '降水量': new_rain, '潮位_cm': new_tide_cm, '潮名': new_tide_name,
                '潮位フェーズ': new_phase, '備考': new_memo
            }
            
            for col, val in updates.items():
                if col in latest_df.columns:
                    latest_df.at[idx, col] = val
            
            conn.update(spreadsheet=url, data=latest_df)
            st.cache_data.clear() # キャッシュを消して最新を反映
            st.success("スプレッドシートを更新しました！")
            st.rerun()

        # 削除処理
        if c_del.form_submit_button("🗑️ 削除実行", type="primary", use_container_width=True):
            if confirm_del:
                latest_df = conn.read(spreadsheet=url, ttl="0s")
                latest_df = latest_df.drop(idx).reset_index(drop=True) # インデックスを詰める
                conn.update(spreadsheet=url, data=latest_df)
                st.cache_data.clear()
                st.warning("データを削除しました。")
                st.rerun()
            else:
                st.error("削除する場合は、上のチェックボックスをオンにしてください。")
