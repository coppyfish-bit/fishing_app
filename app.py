import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# 2026-03-04: AIとの会話は学習に使用したり外部に漏れたりしません。釣果情報も共有しません。

def get_tide_only(dt, station_code):
    """
    指定された日時と地点コードでGitHubから潮位を取得する最小ロジック
    """
    combined_events = []
    hourly_data = []
    
    # 前後3日分をチェック（深夜0時またぎ等の判定精度を上げるため）
    for d in [dt - timedelta(days=1), dt, dt + timedelta(days=1)]:
        url = f"https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{d.year}/{station_code}.json"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code != 200: continue
            raw = r.json()
            # 2025年(リスト型)と2026年(辞書型)の構造を自動判別
            items = raw.get('data', raw) if isinstance(raw, dict) else raw
            
            # 日付一致確認 (YYYYMMDD)
            target = d.strftime("%Y%m%d")
            day_info = next((i for i in items if str(i.get('date','')).replace("-","").replace(" ","") == target), None)
            
            if day_info:
                # 干満イベント
                for ev in day_info.get('events', []):
                    t_str = str(ev.get('time', '')).strip()
                    if ":" in t_str:
                        ev_dt = pd.to_datetime(f"{d.strftime('%Y-%m-%d')} {t_str}")
                        combined_events.append({"time": ev_dt, "type": ev.get('type', '').lower()})
                # 当日の1時間ごとの潮位
                if d.date() == dt.date():
                    hourly_data = [int(v) for v in day_info.get('hourly', []) if str(v).strip().replace('-','').isdigit()]
        except: continue

    # 結果の計算
    cm, phase = 0, "不明"
    if len(hourly_data) >= 24:
        h, mi = dt.hour, dt.minute
        t1, t2 = hourly_data[h], hourly_data[(h+1)%24]
        cm = int(round(t1 + (t2 - t1) * (mi / 60.0)))

    events = sorted(combined_events, key=lambda x: x['time'])
    prev = next((e for e in reversed(events) if e['time'] <= dt), None)
    nxt = next((e for e in events if e['time'] > dt), None)

    if prev and nxt:
        total = (nxt['time'] - prev['time']).total_seconds()
        elap = (dt - prev['time']).total_seconds()
        if total > 0:
            step = min(max(int((elap / total) * 10) + 1, 1), 10)
            phase = f"{'上げ' if 'low' in prev['type'] else '下げ'}{step}分"

    return cm, phase

# --- UI部分 ---
st.title("🌊 潮汐データ アクセスチェッカー")

col1, col2 = st.columns(2)
input_date = col1.date_input("日付を選択", value=datetime(2025, 10, 24))
input_time = col1.time_input("時刻を選択", value=datetime(2025, 10, 24, 22, 43).time())
input_st = col2.text_input("地点コード (例: HS)", value="HS")

target_dt = datetime.combine(input_date, input_time)

if st.button("GitHubから潮位を取得"):
    with st.spinner("通信中..."):
        cm, phase = get_tide_only(target_dt, input_st)
    
    if cm == 0 and phase == "不明":
        st.error("❌ データが取得できませんでした。地点コードや日付がJSONに存在するか確認してください。")
    else:
        st.success("✅ 取得成功！")
        c1, c2 = st.columns(2)
        c1.metric("算出潮位", f"{cm} cm")
        c2.metric("潮位フェーズ", phase)
        
        st.info(f"アクセス先URL例: https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{target_dt.year}/{input_st}.json")
