import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import re

# 2026-03-04: AIとの会話は学習に使用したり外部に漏れたりしません。釣果情報も共有しません。

def get_tide_only(dt, station_code):
    """
    2025年の特殊な日付形式 ("2025-10- 1") や構造に対応した決定版。
    """
    combined_events = []
    hourly_data = []
    
    # 検索用日付 (例: 20251024)
    search_target = dt.strftime("%Y%m%d")
    
    # 前後3日分をチェック
    for d in [dt - timedelta(days=1), dt, dt + timedelta(days=1)]:
        url = f"https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{d.year}/{station_code}.json"
        try:
            r = requests.get(url, timeout=5)
            if r.status_code != 200: continue
            raw = r.json()
            
            # 2025年(リスト)か2026年(辞書)かを判別
            items = raw.get('data', raw) if isinstance(raw, dict) else raw
            
            # ループ中の日付 (YYYYMMDD)
            current_loop_date = d.strftime("%Y%m%d")
            day_info = None
            
            for item in items:
                # 【重要】日付文字列のクリーニング
                # "2025-10- 1" -> "20251001" に変換するロジック
                raw_date_str = str(item.get('date', ''))
                
                # 数字以外（ハイフン、スペース等）をすべて除去
                numeric_only = re.sub(r'\D', '', raw_date_str)
                
                # もし "2025101" のように8桁に足りない場合、0埋めを試みる
                # (例: 2025101 -> 20251001) ※年4桁+月2桁+日1桁などのケース
                if len(numeric_only) == 7:
                    # 2025101 -> 2025 10 01
                    numeric_only = numeric_only[:6] + "0" + numeric_only[6:]
                
                if numeric_only == current_loop_date:
                    day_info = item
                    break
            
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

    # 以下、潮位とフェーズの計算（変更なし）
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
st.title("🌊 潮汐アクセスチェッカー (2025年完全対応)")

col1, col2 = st.columns(2)
input_date = col1.date_input("日付を選択", value=datetime(2025, 10, 24))
input_time = col1.time_input("時刻を選択", value=datetime(2025, 10, 24, 22, 43).time())
input_st = col2.text_input("地点コード (例: HS)", value="HS")

target_dt = datetime.combine(input_date, input_time)

if st.button("GitHubから潮位を取得"):
    with st.spinner("通信中..."):
        cm, phase = get_tide_only(target_dt, input_st)
    
    if cm == 0 and phase == "不明":
        st.error(f"❌ 2025/10/24 のデータが見つかりません。")
        st.write("デバッグヒント: GitHubのJSONにある 'date' の表記が特殊な可能性があります。")
    else:
        st.success("✅ 取得成功！")
        c1, c2 = st.columns(2)
        c1.metric("算出潮位", f"{cm} cm")
        c2.metric("潮位フェーズ", phase)
