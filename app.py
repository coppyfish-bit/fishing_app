import json
import os
from datetime import datetime, timedelta

# 2026-03-04: AIとの会話は学習に使用したり外部に漏れたりしません。釣果情報も共有しません。

def get_tide_status(target_dt, station_code):
    """
    ローカルのJSONデータから潮位とフェーズを計算する
    """
    year = str(target_dt.year)
    file_path = f"data/{year}/{station_code}.json"
    
    if not os.path.exists(file_path):
        return f"エラー: {file_path} が見つかりません。"

    # 1. JSON読み込み
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
        items = raw_data.get('data', [])

    # 2. 対象日のデータを検索
    target_date_str = target_dt.strftime("%Y-%m-%d")
    day_info = next((i for i in items if i['date'] == target_date_str), None)
    
    if not day_info:
        return f"エラー: {target_date_str} のデータがありません。"

    # 3. 潮位の線形補間（毎時データから分単位を算出）
    hourly = day_info['hourly']
    h = target_dt.hour
    mi = target_dt.minute
    t1 = hourly[h]
    t2 = hourly[(h + 1) % 24]
    current_cm = int(round(t1 + (t2 - t1) * (mi / 60.0)))

    # 4. 潮位フェーズの判定（干満イベントを使用）
    events = []
    for ev in day_info['events']:
        # 時間を今日の日付と結合してdatetimeオブジェクト化
        ev_time = datetime.strptime(f"{target_date_str} {ev['time']}", "%Y-%m-%d %H:%M")
        events.append({"time": ev_time, "type": ev['type']})
    
    # 時系列順にソート（念のため）
    events = sorted(events, key=lambda x: x['time'])
    
    # 直前のイベントと直後のイベントを探す
    prev_e = next((e for e in reversed(events) if e['time'] <= target_dt), None)
    next_e = next((e for e in events if e['time'] > target_dt), None)
    
    phase = "不明"
    if prev_e and next_e:
        total_duration = (next_e['time'] - prev_e['time']).total_seconds()
        elapsed = (target_dt - prev_e['time']).total_seconds()
        
        if total_duration > 0:
            # 10分割して「〇分」を算出
            step = min(max(int((elapsed / total_duration) * 10) + 1, 1), 10)
            label = "上げ" if prev_e['type'] == "low" else "下げ"
            phase = f"{label}{step}分"
    
    return {
        "datetime": target_dt.strftime("%Y-%m-%d %H:%M"),
        "station": station_code,
        "tide_cm": current_cm,
        "phase": phase
    }

# --- テスト実行 ---
if __name__ == "__main__":
    # 例: 2025年10月24日 22:43 本渡瀬戸(HS)
    test_dt = datetime(2025, 10, 24, 22, 43)
    result = get_tide_status(test_dt, "HS")
    
    if isinstance(result, dict):
        print(f"📡 地点: {result['station']}")
        print(f"⏰ 日時: {result['datetime']}")
        print(f"🌊 潮位: {result['tide_cm']} cm")
        print(f"📊 状態: {result['phase']}")
    else:
        print(result)
