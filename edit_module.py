import streamlit as st
import pandas as pd
from datetime import datetime

# --- 共通の修正フォーム関数 ---
def render_edit_form(df, idx, conn, url):
    # 写真の表示
    if 'filename' in df.columns and df.at[idx, 'filename']:
        st.image(df.at[idx, 'filename'], width=400)
    
    # --- 🔄 気象・潮汐の再取得機能 ---
    # フォームの外に配置します（APIを叩いて値を上書きするため）
    if st.button("🌡️ 気象・潮汐情報を再取得して自動入力", key=f"recalc_{idx}"):
        try:
            with st.spinner("最新データを取得中..."):
                # 文字列のdatetimeをオブジェクトに変換
                dt_obj = datetime.strptime(df.at[idx, 'datetime'], '%Y/%m/%d %H:%M')
                lat, lon = float(df.at[idx, 'lat']), float(df.at[idx, 'lon'])
                
                # 既存の取得関数を利用（これらがapp.py内で定義されている前提）
                from app import get_weather_data_openmeteo, find_nearest_tide_station, get_tide_details
                
                # 気象データ
                temp, wind_s, wind_d, rain = get_weather_data_openmeteo(lat, lon, dt_obj)
                # 潮汐データ
                station = find_nearest_tide_station(lat, lon)
                tide_res = get_tide_details(station['code'], dt_obj)
                
                # DataFrameの値を直接書き換える（この後のformのvalueに反映される）
                df.at[idx, '気温'] = temp
                df.at[idx, '風速'] = wind_s
                df.at[idx, '風向'] = wind_d
                if tide_res:
                    df.at[idx, '潮位_cm'] = tide_res['cm']
                    # ここで再計算されたフェーズを自動で入れたい場合は以下も
                    # df.at[idx, '潮位フェーズ'] = calculated_phase 
                
                st.toast("気象情報を更新しました。下の「更新」ボタンで保存してください。")
        except Exception as e:
            st.error(f"再取得に失敗しました: {e}")

    # --- 編集フォーム ---
    with st.form(key=f"form_{idx}"):
        st.write("📝 **基本情報**")
        col1, col2 = st.columns(2)
        new_fish = col1.text_input("魚種", value=df.at[idx, '魚種'], key=f"f_{idx}")
        new_len = col2.number_input("全長(cm)", value=float(df.at[idx, '全長_cm']), step=0.1, key=f"l_{idx}")
        new_place = col1.text_input("場所", value=df.at[idx, '場所'], key=f"p_{idx}")
        
        st.write("🌤️ **環境データ**")
        c1, c2, c3, c4 = st.columns(4) # カラムを4つに増やしてフェーズを追加
        new_temp = c1.number_input("気温(℃)", value=float(df.at[idx, '気温']), key=f"t_{idx}")
        new_wind = c2.number_input("風速(m)", value=float(df.at[idx, '風速']), key=f"w_{idx}")
        new_tide = c3.number_input("潮位(cm)", value=int(df.at[idx, '潮位_cm']), key=f"td_{idx}")
        
        # 潮位フェーズの手入力欄（既存データがあればそれを、なければ空文字を初期値に）
        current_phase = df.at[idx, '潮位フェーズ'] if '潮位フェーズ' in df.columns else ""
        new_phase = c4.text_input("潮汐フェーズ", value=current_phase, key=f"ph_{idx}", placeholder="例: 上げ3分")
        
        new_memo = st.text_area("備考", value=df.at[idx, '備考'] if pd.notna(df.at[idx, '備考']) else "", key=f"m_{idx}")

        c_sub, c_del = st.columns(2)
        if c_sub.form_submit_button("✅ 更新", use_container_width=True):
            df.at[idx, '魚種'] = new_fish
            df.at[idx, '全長_cm'] = new_len
            df.at[idx, '場所'] = new_place
            df.at[idx, '気温'] = new_temp
            df.at[idx, '風速'] = new_wind
            df.at[idx, '潮位_cm'] = new_tide
            df.at[idx, '潮位フェーズ'] = new_phase # 追加
            
            # 保存処理
            save_df = df.drop(columns=['search_label']) if 'search_label' in df.columns else df
            conn.update(spreadsheet=url, data=save_df.iloc[::-1]) 
            st.success("更新完了！")
            st.rerun()

        if c_del.form_submit_button("🗑️ 削除", type="primary", use_container_width=True):
            df = df.drop(idx)
            save_df = df.drop(columns=['search_label']) if 'search_label' in df.columns else df
            conn.update(spreadsheet=url, data=save_df.iloc[::-1])
            st.warning("削除しました。")
            st.rerun()
