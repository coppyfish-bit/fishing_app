import pandas as pd
import requests
from datetime import timedelta
import streamlit as st

# AIとの会話は学習に使用したり外部に漏れたりしません。釣果情報も共有しません。

def get_tide_details(res_dummy, dt):
    """
    2025年(リスト)と2026年(dict)の両構造に対応し、UIを壊さない安定版。
    """
    try:
        # 1. 地点コードの抽出 (例: HS)
        station_code = "HS"
        if isinstance(res_dummy, str) and "/data/" in res_dummy:
            station_code = res_dummy.split('/')[-1].replace('.json', '')
        
        combined_events = []
        hourly_data = []
        
        # 前後3日分のデータを統合
        target_days = [dt - timedelta(days=1), dt, dt + timedelta(days=1)]
        
        for d in target_days:
            url = f"https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{d.year}/{station_code}.json"
            try:
                r = requests.get(url, timeout=5)
                if r.status_code != 200: continue
                
                raw_json = r.json()
                # 2025年(リスト直下)か2026年(dataキー)かを判別
                items = raw_json.get('data', raw_json) if isinstance(raw_json, dict) else raw_json
                
                # 日付の正規化 (YYYYMMDD) で検索
                search_date = d.strftime("%Y%m%d")
                
                day_info = None
                for item in items:
                    clean_date = str(item.get('date', '')).replace("-", "").replace(" ", "")
                    if clean_date == search_date:
                        day_info = item
                        break
                
                if day_info:
                    # イベント(干満)抽出
                    for ev in day_info.get('events', []):
                        t_str = str(ev.get('time', '')).strip()
                        if ":" in t_str:
                            ev_dt = pd.to_datetime(f"{d.strftime('%Y-%m-%d')} {t_str}")
                            combined_events.append({"time": ev_dt, "type": ev.get('type', '').lower()})
                    
                    # 当日の潮位(hourly)抽出
                    if d.date() == dt.date():
                        h_raw = day_info.get('hourly', [])
                        hourly_data = [int(v) for v in h_raw if str(v).strip().replace('-','').isdigit()]
            except:
                continue

        # 2. 現在の潮位計算
        current_cm = 0
        if len(hourly_data) >= 24:
            h, mi = dt.hour, dt.minute
            t1, t2 = hourly_data[h], hourly_data[(h+1)%24]
            current_cm = int(round(t1 + (t2 - t1) * (mi / 60.0)))

        # 3. 10分割フェーズ判定
        events = sorted([dict(t) for t in {tuple(d.items()) for d in combined_events}], key=lambda x: x['time'])
        phase_str = "不明"
        prev_ev, next_ev = None, None

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
        
        # 戻り値を辞書で返す (app.py側の期待値に合わせる)
        return {
            "cm": current_cm, 
            "phase": phase_str, 
            "events": events, 
            "hourly": hourly_data
        }

    except Exception as e:
        # UIを消さないためにエラーはログ出力にとどめる
        print(f"潮位解析エラー: {e}") 
        return {"cm": 0, "phase": "解析失敗", "events": [], "hourly": []}
