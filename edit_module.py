def render_edit_form(df, idx, conn, url):
    # 1. 写真の表示
    if 'filename' in df.columns and df.at[idx, 'filename']:
        st.image(df.at[idx, 'filename'], width=400)
    
    # --- 🔄 【ここが再取得ボタン】 ---
    # 視認性を高めるため、フォームの直前に目立つ形で配置
    st.markdown("---")
    st.write("💡 **データが正しくない場合はこちら**")
    if st.button(f"🔄 気象・潮汐データを再取得する", key=f"recalc_btn_{idx}", use_container_width=True):
        try:
            with st.spinner("気象庁とOpen-Meteoから最新データを取得中..."):
                # 文字列のdatetimeをオブジェクトに変換
                dt_obj = datetime.strptime(df.at[idx, 'datetime'], '%Y/%m/%d %H:%M')
                lat = float(df.at[idx, 'lat'])
                lon = float(df.at[idx, 'lon'])
                
                # app.pyから関数を読み込む（app.pyと同じファイルなら不要ですが、安全のためここで定義）
                # ※ここでお使いの関数名に合わせてください
                from app import get_weather_data_openmeteo, find_nearest_tide_station, get_tide_details
                
                temp, wind_s, wind_d, rain = get_weather_data_openmeteo(lat, lon, dt_obj)
                station = find_nearest_tide_station(lat, lon)
                tide_res = get_tide_details(station['code'], dt_obj)
                
                # DataFrameの内容をメモリ上で書き換える
                df.at[idx, '気温'] = temp
                df.at[idx, '風速'] = wind_s
                if tide_res:
                    df.at[idx, '潮位_cm'] = tide_res['cm']
                
                st.toast("✅ 最新データを取得しました！ 下のフォームで確認して保存してください。")
        except Exception as e:
            st.error(f"再取得に失敗しました: {e}")
    st.markdown("---")

    # 2. 編集フォーム
    with st.form(key=f"form_{idx}"):
        st.write("📝 **基本情報**")
        col1, col2 = st.columns(2)
        new_fish = col1.text_input("魚種", value=df.at[idx, '魚種'], key=f"f_{idx}")
        new_len = col2.number_input("全長(cm)", value=float(df.at[idx, '全長_cm']), step=0.1, key=f"l_{idx}")
        new_place = col1.text_input("場所", value=df.at[idx, '場所'], key=f"p_{idx}")
        
        st.write("🌤️ **環境データ**")
        c1, c2, c3, c4 = st.columns(4)
        new_temp = c1.number_input("気温(℃)", value=float(df.at[idx, '気温']), key=f"t_{idx}")
        new_wind = c2.number_input("風速(m)", value=float(df.at[idx, '風速']), key=f"w_{idx}")
        new_tide = c3.number_input("潮位(cm)", value=int(df.at[idx, '潮位_cm']), key=f"td_{idx}")
        
        # 潮位フェーズ欄を追加
        current_ph = df.at[idx, '潮位フェーズ'] if '潮位フェーズ' in df.columns and pd.notna(df.at[idx, '潮位フェーズ']) else ""
        new_phase = c4.text_input("潮位フェーズ", value=current_ph, key=f"ph_{idx}", placeholder="例: 上げ3分")
        
        new_memo = st.text_area("備考", value=df.at[idx, '備考'] if pd.notna(df.at[idx, '備考']) else "", key=f"m_{idx}")

        c_sub, c_del = st.columns(2)
        if c_sub.form_submit_button("✅ この内容で更新", use_container_width=True):
            # 書き換え
            df.at[idx, '魚種'] = new_fish
            df.at[idx, '全長_cm'] = new_len
            df.at[idx, '場所'] = new_place
            df.at[idx, '気温'] = new_temp
            df.at[idx, '風速'] = new_wind
            df.at[idx, '潮位_cm'] = new_tide
            df.at[idx, '潮位フェーズ'] = new_phase
            df.at[idx, '備考'] = new_memo
            
            # スプレッドシート保存（一時的な列を除去して元の順序に戻す）
            save_df = df.drop(columns=['search_label']) if 'search_label' in df.columns else df
            conn.update(spreadsheet=url, data=save_df.iloc[::-1])
            st.success("スプレッドシートを更新しました！")
            st.rerun()

        if c_del.form_submit_button("🗑️ この行を削除", type="primary", use_container_width=True):
            df = df.drop(idx)
            save_df = df.drop(columns=['search_label']) if 'search_label' in df.columns else df
            conn.update(spreadsheet=url, data=save_df.iloc[::-1])
            st.warning("削除が完了しました。")
            st.rerun()
