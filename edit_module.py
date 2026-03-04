import pandas as pd
import requests
from datetime import timedelta

def get_tide_details(res_dummy, dt):
    """
    2025年(直接リスト形式)と2026年(dataキー形式)の両方に対応した潮汐解析
    """
    try:
        combined_events = []
        target_days = [dt - timedelta(days=1), dt, dt + timedelta(days=1)]
        
        # URLから地点コードを抽出 (例: HS)
        station_code = "HS"
        if isinstance(res_dummy, str) and "/data/" in res_dummy:
             station_code = res_dummy.split('/')[-1].replace('.json', '')

        hourly_data = {}

        for d in target_days:
            url = f"https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{d.year}/{station_code}.json"
            try:
                r = requests.get(url)
                if r.status_code != 200: continue
                raw_json = r.json()
                
                # --- 階層構造の吸収 ---
                # 2026年版は {'data': [...]} だが、2025年版は直後に [...]
                items = raw_json.get('data', raw_json) if isinstance(raw_json, dict) else raw_json
                
                # --- 日付比較の柔軟化 ---
                # 検索用: "20250101"
                search_date = d.strftime("%Y%m%d")
                
                day_info = None
                for item in items:
                    # データのdate: "2025-01-01" や "2026- 3- 4" から記号を除去 -> "20250101"
                    clean_item_date = str(item.get('date', '')).replace("-", "").replace(" ", "")
                    if clean_item_date == search_date:
                        day_info = item
                        break
                
                if day_info:
                    # イベント取得
                    for ev in day_info.get('events', []):
                        t_str = str(ev.get('time', '')).strip()
                        if ":" in t_str:
                            ev_dt = pd.to_datetime(f"{d.strftime('%Y-%m-%d')} {t_str}")
                            combined_events.append({"time": ev_dt, "type": ev.get('type', '').lower()})
                    
                    # 当日の潮位計算用
                    if d.date() == dt.date():
                        hourly_data = [int(v) if str(v).strip().replace('-','').isdigit() else 0 for v in day_info.get('hourly', [])]
            except:
                continue

        # 重複削除とソート
        events = sorted([dict(t) for t in {tuple(d.items()) for d in combined_events}], key=lambda x: x['time'])

        # 潮位算出
        current_cm = 0
        if hourly_data:
            h, mi = dt.hour, dt.minute
            t1 = hourly_data[h]
            t2 = hourly_data[(h+1)%24] if h < 23 else hourly_data[h]
            current_cm = int(round(t1 + (t2 - t1) * (mi / 60.0)))

        # 10分割フェーズ判定
        phase_str = "不明"
        prev_ev = None
        next_ev = None
        for i in range(len(events)):
            if events[i]['time'] <= dt: prev_ev = events[i]
            if events[i]['time'] > dt:
                next_ev = events[i]
                break

        if prev_ev and next_ev:
            total_dur = (next_ev['time'] - prev_ev['time']).total_seconds() / 60
            elapsed = (dt - prev_ev['time']).total_seconds() / 60
            if total_dur > 0:
                ten_parts = min(max(int((elapsed / total_dur) * 10) + 1, 1), 10)
                label = "上げ" if "low" in prev_ev['type'] else "下げ"
                phase_str = f"{label}{ten_parts}分"
        
        return {"cm": current_cm, "phase": phase_str, "events": events, "hourly": hourly_data}

    except Exception as e:
        return {"cm": 0, "phase": f"エラー:{str(e)[:10]}", "events": [], "hourly": []}
