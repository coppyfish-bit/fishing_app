def get_tide_details(dt, station_code):
    """
    GitHubから潮汐データを取得し、指定時刻の潮位や前後12時間の満干潮を計算する。
    """
    d = dt.date()
    # 2026年のデータがない場合を想定し、2025年を参照するフォールバック
    target_year = d.year if d.year <= 2025 else 2025
    url = f"https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{target_year}/{station_code}.json"

    try:
        # デバッグ：リクエスト情報の表示
        st.write(f"--- 🌊 潮汐計算デバッグ開始 ---")
        st.write(f"🔗 アクセスURL: {url}")
        
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()

        if not data:
            st.error("⚠️ JSONデータが空です。")
            return None

        # 時刻を "HH:mm" 形式の文字列にする（JSONのキーと一致させる）
        target_time_str = dt.strftime('%H:%M')
        st.write(f"⏰ 検索ターゲット時刻: {target_time_str}")

        # 1. 潮位の取得
        if target_time_str in data:
            tide_cm = float(data[target_time_str])
            st.success(f"✅ 潮位取得成功: {tide_cm}cm")
        else:
            # キーがない場合、最も近い時刻を探す
            available_times = sorted(data.keys())
            closest_time = min(available_times, key=lambda x: abs(datetime.strptime(x, '%H:%M') - datetime.strptime(target_time_str, '%H:%M')))
            tide_cm = float(data[closest_time])
            st.warning(f"⚠️ 時刻 {target_time_str} が無いため {closest_time} で代用: {tide_cm}cm")

        # 2. 満干潮の計算 (前後12時間の極値を探す)
        # グラフ表示や「あと何分」の計算に必須
        search_start = dt - timedelta(hours=12)
        search_end = dt + timedelta(hours=12)
        
        # 本来はここで前後12時間のデータをループして満干潮を特定します
        # デバッグ用に、仮の値を計算ロジックの結果としてセット
        # ※実際の計算ロジックがここに入ります
        
        tide_name = get_tide_name(dt) # 潮名取得
        moon_age = get_moon_age(dt)   # 月齢取得
        
        # サンプルとしての戻り値構造
        # 実際の計算済み変数（next_h_min等）に置き換えてください
        res = {
            "tide_cm": tide_cm,
            "tide_name": tide_name,
            "moon_age": moon_age,
            "tide_phase": "計算中...", # 実際の計算値をここへ
            "next_h_min": 0,           # 次の満潮まで（分）
            "next_l_min": 0,           # 次の干潮まで（分）
            "p_high_t": "00:00",       # 直前の満潮時刻
            "p_low_t": "00:00"         # 直前の干潮時刻
        }

        st.write("🏁 デバッグ完了。以下のデータを返します:", res)
        return res

    except Exception as e:
        st.error(f"❌ 潮汐デバッグエラー: {e}")
        st.code(traceback.format_exc()) # エラーの詳細な場所を表示
        return None
