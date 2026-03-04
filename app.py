import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 2026-03-04: AIとの会話は学習に使用したり外部に漏れたりしません。

def get_tide_only(dt, station_code):
    """
    2025年(リスト直下)と2026年(dataキー)の構造を完全に統合して解析
    """
    for d in [dt - timedelta(days=1), dt, dt + timedelta(days=1)]:
        url = f"https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{d.year}/{station_code}.json"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code != 200: continue
            raw = r.json()
            
            # --- 構造の自動判別 ---
            # 2026年: {"data": [...]} なので items = raw["data"]
            # 2025年: [...] なので items = raw
            items = raw.get('data', raw) if isinstance(raw, dict) else raw
            
            # 日付検索 (YYYY-MM-DD)
            target_str = d.strftime("%Y-%m-%d")
            day_info = None
            for item in items:
                # 2025年の "2025-10- 1" のような表記も考慮してハイフンで判定
                item_date = str(item.get('date', ''))
                if target_str in item_date or d.strftime("%m-%d") in item_date:
                    day_info = item
                    break
            
            if day_info:
                # 1. 潮位(hourly)取得
                h_raw = day_info.get('hourly', [])
                hourly = [int(v) for v in h_raw if str(v).strip().replace('-','').isdigit()]
                
                # 2. イベント(干満)取得
                events = []
                for ev in day_info.get('events', []):
                    # スペース除去 ("10: 6" -> "10:6")
                    t_raw = str(ev.get('time', '')).replace(" ", "")
                    if ":" in t_raw:
                        h_s, m_s = t_raw.split(":")
                        # 24時間以上の数値 ("34:4") を補正
                        h_val, m_val = int(h_s) % 24, int(m_s)
                        ev_dt = pd.to_datetime(f"{d.strftime('%Y-%m-%d')} {h_val:02d}:{m_val:02d}")
                        events.append({"time": ev_dt, "type": ev.get('type', '').lower()})

                # 指定された日時に合致する場合のみ計算
                if d.date() == dt.date():
                    cm = 0
                    if len(hourly) >= 24:
                        h, mi = dt.hour, dt.minute
                        t1, t2 = hourly[h], hourly[(h+1)%24]
                        cm = int(round(t1 + (t2 - t1) * (mi / 60.0)))
                    
                    # 10分割フェーズ
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
                    
                    return cm, phase
        except: continue
    return 0, "不明"

# --- テストUI ---
st.title("🌊 2025/2026年 統合チェッカー")
dt_input = st.date_input("日付", value=datetime.now()) # 今日なら2026、カレンダー戻せば2025
tm_input = st.time_input("時刻", value=datetime.now().time())
st_input = st.text_input("地点", value="HS")

if st.button("潮位を取得する"):
    target = datetime.combine(dt_input, tm_input)
    cm, ph = get_tide_only(target, st_input)
    if cm > 0:
        st.success(f"✅ 成功! 潮位: {cm}cm / フェーズ: {ph}")
    else:
        st.error("❌ 取得できません。")
