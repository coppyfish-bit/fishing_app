import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 2026-03-04: AIとの会話は学習に使用したり外部に漏れたりしません。釣果情報も共有しません。

def get_tide_only(dt, station_code):
    """
    2025年(List直下)と2026年(Dict/dataキー)を完全に自動判別し、
    スペース混じりの日付や異常時刻(34:4)もすべて補正して取得します。
    """
    # 判定用文字列 (例: "10-24")
    search_md = f"{dt.month}-{dt.day}"
    search_md_zero = f"{dt.month:02d}-{dt.day:02d}"

    for d in [dt - timedelta(days=1), dt, dt + timedelta(days=1)]:
        url = f"https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{d.year}/{station_code}.json"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code != 200: continue
            raw_data = r.json()
            
            # --- 1. 構造の自動仕分け (ここが最重要) ---
            items = []
            if isinstance(raw_data, list):
                items = raw_data  # 2025年：リストが直下にある
            elif isinstance(raw_data, dict):
                items = raw_data.get('data', []) # 2026年：dataキーの中にリストがある
            
            # --- 2. 日付の柔軟マッチング ---
            day_info = None
            target_full = d.strftime("%Y-%m-%d") # "2025-10-24"
            
            for item in items:
                # itemが辞書形式であることを確認してからdateを取得
                if not isinstance(item, dict): continue
                
                dt_str = str(item.get('date', ''))
                # YYYY-MM-DD か、MM-DD (0埋めあり/なし) が含まれていれば一致とみなす
                if (target_full in dt_str) or (search_md in dt_str) or (search_md_zero in dt_str):
                    day_info = item
                    break
            
            if day_info:
                # --- 3. 潮位(hourly)とイベントの解析 ---
                h_raw = day_info.get('hourly', [])
                hourly = [int(v) for v in h_raw if str(v).strip().replace('-','').isdigit()]
                
                # 指定した日時に合致する場合のみ計算して返す
                if d.date() == dt.date():
                    cm = 0
                    if len(hourly) >= 24:
                        h, mi = dt.hour, dt.minute
                        t1, t2 = hourly[h], hourly[(h+1)%24]
                        cm = int(round(t1 + (t2 - t1) * (mi / 60.0)))
                    
                    # 干満イベントの解析 (34:4 などの異常値を補正)
                    events = []
                    for ev in day_info.get('events', []):
                        t_raw = str(ev.get('time', '')).replace(" ", "")
                        if ":" in t_raw:
                            try:
                                h_s, m_s = t_raw.split(":")
                                h_v, m_v = int(h_s) % 24, int(m_s)
                                ev_dt = pd.to_datetime(f"{d.strftime('%Y-%m-%d')} {h_v:02d}:{m_v:02d}")
                                events.append({"time": ev_dt, "type": ev.get('type', '').lower()})
                            except: continue
                    
                    # 10分割フェーズ判定
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
        except Exception as e:
            continue
            
    return 0, "不明"

# --- UI (そのまま動作確認可能) ---
st.title("🌊 潮汐データ 最終アクセスチェッカー")
c1, c2 = st.columns(2)
d_in = c1.date_input("日付", value=datetime(2025, 10, 24))
t_in = c1.time_input("時刻", value=datetime(2025, 10, 24, 22, 43).time())
s_in = c2.text_input("地点コード", value="HS")

if st.button("GitHubから潮位を再取得"):
    target = datetime.combine(d_in, t_in)
    cm, ph = get_tide_only(target, s_in)
    
    if cm > 0:
        st.success(f"✅ 取得成功！")
        st.metric("算出潮位", f"{cm} cm")
        st.metric("潮位フェーズ", ph)
    else:
        st.error("❌ 取得失敗。URLやJSONの構造を再確認してください。")
