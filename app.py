def get_tide_details(dt, station_code):
    # ... (URL生成などは既存のまま) ...
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        # === 【デバッグ用コードここから】 ===
        st.write("--- 🌊 潮汐計算デバッグ ---")
        st.write(f"取得した地点: {station_code}")
        
        # 1. そもそもデータがあるか
        if not data:
            st.error("⚠️ JSONデータが空です")
            return None

        # 2. 検索対象の時刻（分単位に丸めて確認）
        target_time = dt.strftime('%H:%M')
        st.write(f"検索ターゲット時刻: {target_time}")

        # 3. 直近のデータ1件をサンプル表示
        sample_key = list(data.keys())[0] if data else "なし"
        st.write(f"データサンプル (最初の1件): {sample_key} -> {data.get(sample_key)}")
        
        # 4. 検索ロジックがヒットしているか
        if target_time in data:
            st.success(f"✅ 時刻 {target_time} の直接ヒットに成功！")
        else:
            st.warning(f"⚠️ 時刻 {target_time} の直接データがありません。近似値を検索します。")
        # === 【デバッグ用コードここまで】 ===

        # ... (以下、潮位・フェーズの計算ロジック) ...
        
        # 計算結果を返す直前にもデバッグを入れる
        res = {
            "tide_cm": tide_cm, "tide_name": tide_name, "moon_age": moon_age,
            "tide_phase": tide_phase, "next_h_min": next_h_min,
            "next_l_min": next_l_min, "p_high_t": p_high_t, "p_low_t": p_low_t
        }
        st.write("🏁 最終計算結果:", res)
        return res

    except Exception as e:
        st.error(f"❌ 取得エラー詳細: {e}")
        return None
