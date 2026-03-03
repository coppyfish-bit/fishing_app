import streamlit as st
import requests
import re
from datetime import datetime, timedelta
import pandas as pd

def get_day_events_fixed(date, code):
    url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{date.year}/{code}.txt"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200: return []
        
        lines = res.text.splitlines()
        yy, mm, dd = date.strftime('%y'), str(date.month), str(date.day)
        # 確実にその日の行を見つける
        pattern = rf"{yy}\s+{mm}\s+{dd}\s*{code}"
        
        target_line = None
        for line in lines:
            if re.search(pattern, line):
                target_line = line
                break
        
        if not target_line: return []

        # --- ここからが魔改造 ---
        # 地点記号(HS等)の位置を特定し、それ以降の文字列だけを抽出
        pos = target_line.find(code)
        event_part = target_line[pos + len(code):]
        # その部分から数値を抽出
        nums = re.findall(r'-?\d+', event_part)
        
        # 貴様のデータに基づくと、HSの直後の1つ目の数字(例: 7 や 8)は無視し、
        # その次から [時刻, 潮位] のペアが始まっている
        actual_events = nums[1:] 
        
        day_events = []
        date_str = date.strftime('%Y%m%d')

        # 満潮(最大4ペア)
        for i in range(0, 8, 2):
            if i+1 < len(actual_events):
                t_str, cm = actual_events[i], actual_events[i+1]
                if t_str != "9999" and len(t_str) <= 4:
                    ev_t = datetime.strptime(date_str + t_str.zfill(4), '%Y%m%d%H%M')
                    day_events.append({"time": ev_t, "type": "満潮", "cm": int(cm)})

        # 干潮(最大4ペア) 満潮データのさらに後ろ(インデックス8から)
        for i in range(8, 16, 2):
            if i+1 < len(actual_events):
                t_str, cm = actual_events[i], actual_events[i+1]
                if t_str != "9999" and len(t_str) <= 4:
                    ev_t = datetime.strptime(date_str + t_str.zfill(4), '%Y%m%d%H%M')
                    day_events.append({"time": ev_t, "type": "干潮", "cm": int(cm)})
        
        return day_events
    except:
        return []

# --- 実行部 ---
st.title("🌊 三日連結・鉄壁解析デバッガー")

with st.sidebar:
    code = st.text_input("地点", "HS")
    # テスト用に時刻を自由に動かせるようにする
    test_dt = st.date_input("基準日", datetime.now())
    test_tm = st.time_input("基準時刻", datetime.now().time())
    execute = st.button("🔥 執念の再解析")

if execute:
    base_dt = datetime.combine(test_dt, test_tm)
    
    # 前・今・次の3日分を統合
    all_events = []
    for i in [-1, 0, 1]:
        all_events.extend(get_day_events_fixed(base_dt + timedelta(days=i), code))
    
    all_events.sort(key=lambda x: x['time'])

    # 直前と直後を抽出
    prev = next((e for e in reversed(all_events) if e['time'] <= base_dt), None)
    nxt = next((e for e in all_events if e['time'] > base_dt), None)

    # 表示
    c1, c2 = st.columns(2)
    with c1:
        if prev: st.metric("🎯 直前のイベント", f"{prev['type']}", f"{prev['time'].strftime('%m/%d %H:%M')} ({prev['cm']}cm)")
        else: st.error("直前なし：昨日のデータがまだ無いか解析ミスだ")
    with c2:
        if nxt: st.metric("⌛ 次のイベント", f"{nxt['type']}", f"{nxt['time'].strftime('%m/%d %H:%M')} ({nxt['cm']}cm)")
        else: st.error("直後なし：明日のデータが未公開か解析ミスだ")

    st.write("### 📋 抽出された全イベント（三日間）")
    st.table(pd.DataFrame(all_events) if all_events else "データが空だ……")
