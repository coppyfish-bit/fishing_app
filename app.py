import pandas as pd
import requests
from datetime import timedelta
import streamlit as st

# AIとの会話は学習に使用したり外部に漏れたりしません。釣果情報も共有しません。

def get_tide_details(res, dt):
    """
    2025/2026年両対応・前後3日解析・10分割フェーズ算出
    """
    import pandas as pd
    import requests
    from datetime import timedelta

    # 初期値の設定（エラー時もこの形式で返す）
    result = {"cm": 0, "phase": "不明", "events": [], "hourly": []}
    
    try:
        # 1. 地点コードの特定 (URLから抽出)
        station_code = "HS"
        if isinstance(res, str) and "/data/" in res:
            station_code = res.split('/')[-1].replace('.json', '')
        
        combined_events = []
        hourly_data = []
        
        # 2. 前後3日分のデータをループで取得
        target_days = [dt - timedelta(days=1), dt, dt + timedelta(days=1)]
        
        for d in target_days:
            url = f"https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{d.year}/{station_code}.json"
            try:
                r = requests.get(url, timeout=5)
                if r.status_code != 200:
                    continue
                
                raw_json = r.json()
                # 2025年(リスト直下)か2026年(dataキー)かを判別してデータを展開
                items = raw_json.get('data', raw_json) if isinstance(raw_json, dict) else raw_json
                
                # 日付の正規化比較 (YYYYMMDD)
                search_date = d.strftime("%Y%m%d")
                day_info = next((item for item in items if str(item.get('date')).replace("-","").replace(" ","") == search_date), None)
                
                if day_info:
                    # イベント(干満時刻)を統合リストに追加
                    for ev in day_info.get('events', []):
                        t_str = str(ev.get('time', '')).strip()
                        if ":" in t_str:
                            ev_dt = pd.to_datetime(f"{d.strftime('%Y-%m-%d')} {t_str}")
                            combined_events.append({"time": ev_dt, "type": ev.get('type', '').lower()})
                    
                    # 当日の潮位(hourly)を保持
                    if d.date() == dt.date():
                        h_raw = day_info.get('hourly', [])
                        hourly_data = [int(v) for v in h_raw if str(v).strip().replace('-','').isdigit()]
            except:
                continue

        # 3. 潮位(cm)の計算
        if len(hourly_data) >= 24:
            h, mi = dt.hour, dt.minute
            t1, t2 = hourly_data[h], hourly_data[(h+1)%24]
            result["cm"] = int(round(t1 + (t2 - t1) * (mi / 60.0)))
            result["hourly"] = hourly_data

        # 4. 10分割フェーズの算出
        events = sorted([dict(t) for t in {tuple(d.items()) for d in combined_events}], key=lambda x: x['time'])
        result["events"] = events
        
        prev_ev, next_ev = None, None
        for i in range(len(events)):
            if events[i]['time'] <= dt:
                prev_ev = events[i]
            if events[i]['time'] > dt:
                next_ev = events[i]
                break

        if prev_ev and next_ev:
            total_dur = (next_ev['time'] - prev_ev['time']).total_seconds() / 60
            elapsed = (dt - prev_ev['time']).total_seconds() / 60
            if total_dur > 0:
                ten_parts = min(max(int((elapsed / total_dur) * 10) + 1, 1), 10)
                label = "上げ" if "low" in prev_ev['type'] else "下げ"
                result["phase"] = f"{label}{ten_parts}分"

        return result

    except Exception as e:
        # 万が一のエラー時も空の辞書を返してUI崩壊を防ぐ
        return result
