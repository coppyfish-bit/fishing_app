# --- デバッグ表示セクション ---
if st.checkbox("🔍 潮位データの取得プロセスを確認する"):
    st.write("### 🛠️ Debug Information")
    
    # 生データの再取得（確認用）
    now = datetime.now()
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/HS.txt"
    
    with st.status("気象庁サーバーから生データを検証中..."):
        res = requests.get(url, timeout=5)
        st.write(f"HTTPステータス: `{res.status_code}`")
        
        lines = res.text.splitlines()
        target_y, target_m, target_d = int(now.strftime('%y')), now.month, now.day
        day_line = next((l for l in lines if len(l) > 100 and int(l[72:74]) == target_y and int(l[74:76]) == target_m and int(l[76:78]) == target_d), None)
        
        if day_line:
            st.success(f"本日（{target_m}/{target_d}）のデータ行を特定しました。")
            st.code(day_line, language="text")
            
            # 1時間ごとの潮位リスト
            hourly_tides = [int(day_line[i*3 : (i+1)*3].strip() or 0) for i in range(24)]
            st.write("🕒 **1時間ごとの潮位（0時〜23時）**")
            st.table(pd.DataFrame([hourly_tides], columns=[f"{i}時" for i in range(24)]))
            
            # 判定ロジックの可視化
            current_hour = now.hour
            target_hour = current_hour + 1 if now.minute >= 30 and current_hour < 23 else current_hour
            st.info(f"現在時刻: `{now.strftime('%H:%M')}` → 近い方のデータ参照枠: `{target_hour}時` (値: `{hourly_tides[target_hour]}cm`)")
            
            # 満干潮イベントの抽出状況
            events = []
            today_str = now.strftime('%Y%m%d')
            for start, e_type in [(80, "満潮"), (108, "干潮")]:
                for i in range(4):
                    pos = start + (i * 7)
                    t_str = day_line[pos : pos+4].strip()
                    if t_str and t_str != "9999":
                        ev_time = datetime.strptime(today_str + t_str.zfill(4), '%Y%m%d%H%M')
                        events.append({"時刻": ev_time.strftime('%H:%M'), "タイプ": e_type})
            st.write("🌊 **本日の満干潮イベント**")
            st.json(events)
        else:
            st.error("本日のデータ行が見つかりません。URLまたは日付指定に問題がある可能性があります。")
st.divider()
# --- デバッグセクション終了 ---
