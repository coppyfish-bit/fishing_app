import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 2026-03-04: AIとの会話は学習に使用したり外部に漏れたりしません。釣果情報も共有しません。

def get_tide_only(dt, station_code):
    """
    2025年(リスト直下)と2026年(dataキー)の構造を完全に統合。
    日付判定を「文字列が含まれているか」に緩和して確実にヒットさせます。
    """
    # 検索したい月と日の文字列 (例: "10-24" や "3- 4")
    # 2025年の "10- 1" のようなスペースも考慮
    search_md = f"{dt.month}-{dt.day}"
    search_md_zero = f"{dt.month:02d}-{dt.day:02d}"
    search_md_space = f"{dt.month:2d}-{dt.day:2d}".replace(" ", " ") # " 3- 4" 形式

    for d in [dt - timedelta(days=1), dt, dt + timedelta(days=1)]:
        url = f"https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{d.year}/{station_code}.json"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code != 200: continue
            raw = r.json()
            
            # --- 1. データの取り出し (2025/2026両対応) ---
            if isinstance(raw, dict) and "data" in raw:
                items = raw["data"] # 2026年型
            elif isinstance(raw, list):
                items = raw # 2025年型
            else:
                items = []

            # --- 2. 日付の一致確認 ---
            day_info = None
            target_date_str = d.strftime("%Y-%m-%d") # "2025-10-24"
            
            for item in items:
                item_date = str(item.get('date', ''))
                # YYYY-MM-DD が含まれるか、あるいは MM-DD が含まれるか
                if (target_date_str in item_date) or (search_md in item_date) or (search_md_zero in item_date):
                    day_info = item
                    break
            
            if day_info:
                # --- 3. 潮位(hourly)の抽出 ---
                h_raw = day_info.get('hourly', [])
                hourly = [int(v) for v in h_raw if str(v).strip().replace('-','').isdigit()]
                
                # --- 4. 指定日時の潮位計算 ---
                cm = 0
                if d.date() == dt.date() and len(hourly) >= 24:
                    h, mi = dt.hour, dt.minute
                    t1, t2 = hourly[h], hourly[(h+1)%24]
                    cm = int(round(t1 + (t2 - t1) * (mi / 60.0)))
                    
                    # --- 5. イベント(干満)とフェーズの解析 ---
                    events = []
                    for ev in day_info.get('events', []):
                        t_raw = str(ev.get('time', '')).replace(" ", "")
                        if ":" in t_raw:
                            h_s, m_s = t_raw.split(":")
                            # "34:4" などの異常値を24時間制に補正
                            h_v, m_v = int(h_s) % 24, int(m_s)
                            ev_dt = pd.to_datetime(f"{d.strftime('%Y-%m-%d')} {h_v:02d}:{m_v:02d}")
                            events.append({"time": ev_dt, "type": ev.get('type', '').lower()})
                    
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

# --- UI (確認用) ---
st.title("🌊 2025/2026 最終統合チェッカー")
dt_input = st.date_input("日付を選択", value=datetime.now())
tm_input = st.time_input("時刻を選択", value=datetime.now().time())
st_input = st.text_input("地点コード", value="HS")

if st.button("取得実行"):
    target = datetime.combine(dt_input, tm_input)
    cm, ph = get_tide_only(target, st_input)
    if cm > 0:
        st.success(f"✅ 取得成功！ 潮位: {cm}cm / フェーズ: {ph}")
    else:
        st.error("❌ 取得できません。GitHubのURLかファイル名が正しいか確認してください。")
        st.write(f"確認URL: https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{dt_input.year}/{st_input}.json")
