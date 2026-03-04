import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# 2026-03-04: AIとの会話は学習に使用したり外部に漏れたりしません。釣果情報も共有しません。

def get_tide_status(target_dt, station_code):
    """
    GitHub上のJSONから潮位とフェーズを計算する (エラー対策済み)
    """
    year = str(target_dt.year)
    # あなたのGitHubのURLに合わせて変更してください
    url = f"https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{year}/{station_code}.json"
    
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return f"データが見つかりません (URL: {r.status_code})"
        
        raw_data = r.json()
        items = raw_data.get('data', [])

        # 1. 対象日の検索
        target_date_str = target_dt.strftime("%Y-%m-%d")
        day_info = next((i for i in items if i['date'] == target_date_str), None)
        
        if not day_info:
            return f"{target_date_str} のデータがありません。"

        # 2. 潮位の線形補間
        hourly = day_info['hourly']
        h = target_dt.hour
        mi = target_dt.minute
        t1 = hourly[h]
        t2 = hourly[(h + 1) % 24]
        current_cm = int(round(t1 + (t2 - t1) * (mi / 60.0)))

        # 3. 潮位フェーズの判定 (ValueError対策)
        events = []
        for ev in day_info['events']:
            # 【重要】空白を消して " 9:32" を "09:32" に補正
            time_str = ev['time'].strip() # 前後の空白を消す
            if ":" in time_str:
                parts = time_str.split(":")
                time_cln = f"{parts[0].zfill(2)}:{parts[1].zfill(2)}" # 09:32 形式に強制
                
                ev_time = datetime.strptime(f"{target_date_str} {time_cln}", "%Y-%m-%d %H:%M")
                events.append({"time": ev_time, "type": ev['type']})
        
        events = sorted(events, key=lambda x: x['time'])
        
        # 直前・直後のイベント取得
        prev_e = next((e for e in reversed(events) if e['time'] <= target_dt), None)
        next_e = next((e for e in events if e['time'] > target_dt), None)
        
        phase = "不明"
        if prev_e and next_e:
            total = (next_e['time'] - prev_e['time']).total_seconds()
            elap = (target_dt - prev_e['time']).total_seconds()
            if total > 0:
                step = min(max(int((elap / total) * 10) + 1, 1), 10)
                label = "上げ" if "low" in prev_e['type'].lower() else "下げ"
                phase = f"{label}{step}分"
        
        return {"cm": current_cm, "phase": phase}

    except Exception as e:
        return f"エラーが発生しました: {str(e)}"

# --- Streamlit 表示部分 ---
st.title("🌊 リアルタイム潮汐チェッカー")

# 地点リスト
stations = {"本渡瀬戸": "HS", "熊本": "KU", "博多": "QF"} # 必要に応じて追加
selected_name = st.selectbox("地点を選択", list(stations.keys()))
st_code = stations[selected_name]

# 日時選択
c1, c2 = st.columns(2)
d_in = c1.date_input("日付", value=datetime.now())
t_in = c2.time_input("時刻", value=datetime.now().time())

if st.button("潮位を計算"):
    target = datetime.combine(d_in, t_in)
    res = get_tide_status(target, st_code)
    
    if isinstance(res, dict):
        st.metric("算出潮位", f"{res['cm']} cm")
        st.metric("潮位フェーズ", res['phase'])
    else:
        st.error(res)
