import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import re

# AIとの会話は学習に使用したり外部に漏れたりしません。釣果情報も共有しません。

def get_tide_only(dt, station_code):
    search_date = dt.strftime("%Y-%m-%d") # "2025-10-24"
    
    for d in [dt - timedelta(days=1), dt, dt + timedelta(days=1)]:
        url = f"https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{d.year}/{station_code}.json"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code != 200: continue
            raw = r.json()
            items = raw.get('data', raw) if isinstance(raw, dict) else raw
            
            # 日付検索
            target_str = d.strftime("%Y-%m-%d")
            day_info = next((i for i in items if target_str in str(i.get('date', ''))), None)
            
            if day_info:
                # 1. 潮位計算 (hourly)
                h_raw = day_info.get('hourly', [])
                hourly = [int(v) for v in h_raw if str(v).strip().replace('-','').isdigit()]
                
                current_cm = 0
                if d.date() == dt.date() and len(hourly) >= 24:
                    h, mi = dt.hour, dt.minute
                    t1, t2 = hourly[h], hourly[(h+1)%24]
                    current_cm = int(round(t1 + (t2 - t1) * (mi / 60.0)))

                    # 2. イベント解析（スペースや異常な時間を補正）
                    events = []
                    for ev in day_info.get('events', []):
                        t_raw = str(ev.get('time', '')).replace(" ", "") # スペース除去
                        if ":" in t_raw:
                            h_s, m_s = t_raw.split(":")
                            # "34:4" のような異常値を 24時間以内に収める（例: 34-24=10時）
                            hour_val = int(h_s) % 24 
                            min_val = int(m_s)
                            ev_dt = pd.to_datetime(f"{d.strftime('%Y-%m-%d')} {hour_val:02d}:{min_val:02d}")
                            events.append({"time": ev_dt, "type": ev.get('type', '').lower()})
                    
                    # 3. 10分割フェーズ判定
                    phase = "不明"
                    events = sorted(events, key=lambda x: x['time'])
                    prev_e = next((e for e in reversed(events) if e['time'] <= dt), None)
                    next_e = next((e for e in events if e['time'] > dt), None)
                    
                    if prev_e and next_e:
                        total = (next_e['time'] - prev_e['time']).total_seconds()
                        elap = (dt - prev_e['time']).total_seconds()
                        if total > 0:
                            step = min(max(int((elap / total) * 10) + 1, 1), 10)
                            label = "上げ" if "low" in prev_e['type'] else "下げ"
                            phase = f"{label}{step}分"
                    
                    return current_cm, phase
        except: continue
    return 0, "不明"

# --- UI ---
st.title("🎣 2025年データ解析テスト")
target = datetime.combine(st.date_input("日付", datetime(2025, 10, 24)), 
                         st.time_input("時刻", datetime(2025,10,24,22,43).time()))

if st.button("データ取得"):
    cm, ph = get_tide_only(target, "HS")
    if cm > 0:
        st.success(f"✅ 取得成功！ 潮位: {cm}cm / フェーズ: {ph}")
    else:
        st.error("❌ 取得失敗。ロジックを再確認します。")
