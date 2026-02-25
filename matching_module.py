def get_jma_tide_hs():
    """気象庁 suisan/txt フォーマット(136col)を精密解析"""
    now = datetime.now()
    station_code = "HS"
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/{station_code}.txt"
    
    default_res = (150, "上げ5分")
    
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200: return default_res
        
        lines = res.text.splitlines()
        # 日付フォーマットの照合 (26 1 1HS のような形式に対応)
        # データの73文字目から日付が始まる (YY MM DD SS)
        target_date_part = f"{now.strftime('%y %-m %-d').ljust(6)}{station_code}"
        
        day_data = None
        for line in lines:
            if len(line) < 80: continue
            # 72カラム目以降に日付と地点コードが含まれる
            if station_code in line[78:80] and str(now.day) in line[75:78]:
                # より厳密に月日をチェック
                day_data = line
                break
        
        if not day_data: return default_res

        # 1. 毎時潮位の取得 (3文字ずつ24時間分 = 72文字)
        hourly = []
        for i in range(24):
            val = day_data[i*3 : (i+1)*3].replace(" ", "")
            hourly.append(int(val) if val else 0)
        
        t1 = hourly[now.hour]
        t2 = hourly[now.hour+1] if now.hour < 23 else hourly[now.hour]
        current_cm = int(round(t1 + (t2 - t1) * (now.minute / 60.0)))

        # 2. 満潮・干潮時刻の抽出 (データ内の位置を固定)
        events = []
        today_str = now.strftime('%Y%m%d')
        # 満潮(80-107) 7文字おきに4つ
        for i in range(4):
            t_start = 80 + (i * 7)
            t_part = day_data[t_start : t_start+4].replace(" ", "")
            if t_part and t_part != "9999":
                ev_time = datetime.strptime(today_str + t_part.zfill(4), '%Y%m%d%H%M')
                events.append({"time": ev_time, "type": "満潮"})
        # 干潮(108-135) 7文字おきに4つ
        for i in range(4):
            t_start = 108 + (i * 7)
            t_part = day_data[t_start : t_start+4].replace(" ", "")
            if t_part and t_part != "9999":
                ev_time = datetime.strptime(today_str + t_part.zfill(4), '%Y%m%d%H%M')
                events.append({"time": ev_time, "type": "干潮"})
        
        events = sorted(events, key=lambda x: x['time'])

        # 3. 潮位フェーズ判定
        phase_text = "不明"
        # 現在時刻より前の最新イベント
        prev_ev = next((e for e in reversed(events) if e['time'] <= now), None)
        # 現在時刻より後の最初のイベント
        next_ev = next((e for e in events if e['time'] > now), None)

        if prev_ev and next_ev:
            duration = (next_ev['time'] - prev_ev['time']).total_seconds()
            elapsed = (now - prev_ev['time']).total_seconds()
            if duration > 0:
                p_type = "上げ" if prev_ev['type'] == "干潮" else "下げ"
                step = max(1, min(9, int((elapsed / duration) * 10)))
                phase_text = f"{p_type}{step}分"
                
                # 潮止まり付近の判定
                ratio = elapsed / duration
                if ratio < 0.1: phase_text = prev_ev['type']
                elif ratio > 0.9: phase_text = next_ev['type']

        return current_cm, phase_text
    except:
        return default_res
