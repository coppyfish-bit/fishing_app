import pandas as pd
import requests
from datetime import timedelta

def fetch_tide_data(dt, station_code):
    """
    日時(dt)と地点コード(station_code)から潮位とフェーズを10分割で取得する
    """
    # 1. 前後3日分のイベントをマージして日付またぎに対応
    combined_events = []
    hourly_data = []
    
    for d in [dt - timedelta(days=1), dt, dt + timedelta(days=1)]:
        url = f"https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{d.year}/{station_code}.json"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code != 200: continue
            
            raw = r.json()
            # 2025年(リスト)と2026年(辞書)の両構造に対応
            items = raw.get('data', raw) if isinstance(raw, dict) else raw
            
            # 日付一致確認
            search_date = d.strftime("%Y%m%d")
            day_info = next((i for i in items if str(i.get('date','')).replace("-","").replace(" ","") == search_date), None)
            
            if day_info:
                # 干満イベント
                for ev in day_info.get('events', []):
                    t_str = str(ev.get('time', '')).strip()
                    if ":" in t_str:
                        ev_dt = pd.to_datetime(f"{d.strftime('%Y-%m-%d')} {t_str}")
                        combined_events.append({"time": ev_dt, "type": ev.get('type', '').lower()})
                # 当日の潮位
                if d.date() == dt.date():
                    hourly_data = [int(v) for v in day_info.get('hourly', []) if str(v).strip().replace('-','').isdigit()]
        except: continue

    # 2. 現在の潮位計算(cm)
    current_cm = 0
    if len(hourly_data) >= 24:
        h, mi = dt.hour, dt.minute
        t1, t2 = hourly_data[h], hourly_data[(h+1)%24]
        current_cm = int(round(t1 + (t2 - t1) * (mi / 60.0)))

    # 3. 10分割フェーズ判定
    phase = "不明"
    events = sorted(combined_events, key=lambda x: x['time'])
    prev_ev = next((e for e in reversed(events) if e['time'] <= dt), None)
    next_ev = next((e for e in events if e['time'] > dt), None)

    if prev_ev and next_ev:
        total = (next_ev['time'] - prev_ev['time']).total_seconds()
        elapsed = (dt - prev_ev['time']).total_seconds()
        if total > 0:
            step = min(max(int((elapsed / total) * 10) + 1, 1), 10)
            phase = f"{'上げ' if 'low' in prev_ev['type'] else '下げ'}{step}分"

    return {"cm": current_cm, "phase": phase}

# --- 使い方例 ---
# target_dt = pd.to_datetime("2025-10-24 22:43:00")
# result = fetch_tide_data(target_dt, "HS")
# print(result) # {'cm': 186, 'phase': '上げ9分'} などの辞書が返ります
