import streamlit as st
import requests
import re
from datetime import datetime, timedelta
import pandas as pd

def get_day_events_final(date, code):
    url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{date.year}/{code}.txt"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200: return []
        
        lines = res.text.splitlines()
        yy, mm, dd = date.strftime('%y'), str(date.month), str(date.day)
        pattern = rf"{yy}\s+{mm}\s+{dd}\s*{code}"
        
        line = next((l for l in lines if re.search(pattern, l)), None)
        if not line: return []

        # 地点記号(HS)以降の数値をすべて抽出
        pos = line.find(code)
        nums = re.findall(r'-?\d+', line[pos + len(code):])
        
        # --- 本渡瀬戸(HS)完全適合ロジック ---
        # nums[0] : 謎の1桁 (無視)
        # nums[1:9] : 満潮 4ペア [時分, 潮位, 時分, 潮位...]
        # nums[9] : 謎の数値 (干潮の前の仕切り。これも無視)
        # nums[10:18] : 干潮 4ペア [時分, 潮位, 時分, 潮位...]
        
        day_events = []
        date_str = date.strftime('%Y%m%d')

        # 1. 満潮抽出
        high_tide_data = nums[1:9]
        for i in range(0, len(high_tide_data), 2):
            t_str, cm = high_tide_data[i], high_tide_data[i+1]
            if t_str != "9999" and len(t_str) <= 4:
                ev_t = datetime.strptime(date_str + t_str.zfill(4), '%Y%m%d%H%M')
                day_events.append({"time": ev_t, "type": "満潮", "cm": int(cm)})

        # 2. 干潮抽出 (インデックス10から開始)
        low_tide_data = nums[10:18]
        for i in range(0, len(low_tide_data), 2):
            if i+1 < len(low_tide_data):
                t_str, cm = low_tide_data[i], low_tide_data[i+1]
                if t_str != "9999" and len(t_str) <= 4:
                    ev_t = datetime.strptime(date_str + t_str.zfill(4), '%Y%m%d%H%M')
                    day_events.append({"time": ev_t, "type": "干潮", "cm": int(cm)})
        
        return day_events
    except:
        return []

# --- 実行表示部 ---
st.title("🌊 満干潮・完全補足デバッガー")

with st.sidebar:
    code = st.text_input("地点", "HS")
    test_dt = st.date_input("基準日", datetime.now())
    test_tm = st.time_input("基準時刻", datetime.now().time())
    execute = st.button("🔥 執念の再解析")

if execute:
    base_dt = datetime.combine(test_dt, test_tm)
    all_events = []
    # 前後3日分を結合
    for i in [-1, 0, 1]:
        all_events.extend(get_day_events_final(base_dt + timedelta(days=i), code))
    
    all_events.sort(key=lambda x: x['time'])

    # 直前・直後特定
    prev = next((e for e in reversed(all_events) if e['time'] <= base_dt), None)
    nxt = next((e for e in all_events if e['time'] > base_dt), None)

    # メイン表示
    c1, c2 = st.columns(2)
    with c1:
        if prev: st.metric("🎯 直前のイベント", f"{prev['type']}", f"{prev['time'].strftime('%m/%d %H:%M')} ({prev['cm']}cm)")
        else: st.error("直前なし")
    with c2:
        if nxt: st.metric("⌛ 次のイベント", f"{nxt['type']}", f"{nxt['time'].strftime('%m/%d %H:%M')} ({nxt['cm']}cm)")
        else: st.error("直後なし")

    st.write("### 📋 解析された全イベント（三日間）")
    if all_events:
        st.table(pd.DataFrame(all_events).assign(時刻=lambda d: d['time'].dt.strftime('%m/%d %H:%M'))[['時刻', 'type', 'cm']])
    else:
        st.error("イベントが一つも抽出されておらん！")
