def get_tide_details(dt, station_code):
    """
    潮汐データの取得と計算をデバッグ表示付きで行う
    """
    import traceback
    
    # 1. 準備
    d = dt.date()
    target_year = d.year if d.year <= 2025 else 2025
    url = f"https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{target_year}/{station_code}.json"
    
    st.write(f"--- 🌊 潮汐デバッグ開始 ---")
    st.write(f"🔗 URL: {url}")
    
    try:
        # 2. 通信
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            st.error("❌ JSONが空、または解析できませんでした")
            return None

        # 3. 時刻キーの照合
        # JSONのキーが "08:00" か "8:00" かで挙動が変わるため両方チェック
        t_str = dt.strftime('%H:%M')    # "08:05"
        t_str_short = dt.strftime('%-H:%M') # "8:05" (0埋めなし)
        
        st.write(f"⏰ 検索時刻: {t_str} (または {t_str_short})")

        # 4. 潮位の取得
        tide_cm = data.get(t_str) or data.get(t_str_short)
        
        if tide_cm is None:
            # 近似値を探す
            times = sorted(data.keys())
            closest_time = min(times, key=lambda x: abs(datetime.strptime(x, '%H:%M') - datetime.strptime(t_str, '%H:%M')))
            tide_cm = data[closest_time]
            st.warning(f"⚠️ 時刻が完全一致しないため {closest_time} のデータ({tide_cm}cm)を使用します")
        else:
            st.success(f"✅ 潮位ヒット: {tide_cm}cm")

        # 5. 満干潮とフェーズの計算 (ここが空だと「何も表示されない」原因になる)
        # 本来の複雑な計算ロジックをここに復元するか、一旦テスト値を入れます
        tide_name = get_tide_name(dt)
        moon_age = get_moon_age(dt)
        
        # --- 計算の実行結果を辞書にまとめる ---
        # ⚠️ ここで定義するキー名が、呼び出し元の st.session_state への代入名と一致しているか確認！
        res = {
            "tide_cm": float(tide_cm),
            "tide_name": tide_name,
            "moon_age": moon_age,
            "tide_phase": "下げ5分(仮)", # ← 計算ロジックをここに結合
            "next_h_min": 120,          # 次の満潮まで(分)
            "next_l_min": 60,           # 次の干潮まで(分)
            "p_high_t": "09:00",        # 直前の満潮時刻
            "p_low_t": "15:00"          # 直前の干潮時刻
        }

        st.write("🏁 最終戻り値:", res)
        return res

    except Exception as e:
        st.error(f"❌ 致命的エラー: {e}")
        st.code(traceback.format_exc())
        return None
