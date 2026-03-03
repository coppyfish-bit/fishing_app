import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import re

def get_day_events_hybrid(date, code):
    url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{date.year}/{code.upper()}.txt"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200: return []
        
        lines = res.text.splitlines()
        # 日付の検索パターン（例: "26 3 3HS" や "26  3  3HS" に対応）
        yy, mm, dd = date.strftime('%y'), date.month, date.day
        # 数字と地点記号の並びを正規表現で探す（位置がズレていても行を特定するため）
        pattern = rf"{yy}\s+{mm}\s+{dd}\s*{code.upper()}"
        
        target_line = None
        for line in lines:
            if re.search(pattern, line):
                target_line = line
                break
        
        if not target_line: return []

    # --- 基準点（地点記号）からの相対スライス ---
        # 仕様書では地点記号(79-80)の直後(81)から満潮が始まる
        # つまり、HSという文字を見つけ、その2文字後からがデータだ
        base_idx = target_line.find(code.upper()) + len(code.upper())
        
        day_events = []
        d_str = date.strftime('%Y%m%d')

        # 1. 満潮解析 (地点記号の直後から28文字分)
        high_part = target_line[base_idx : base_idx + 28]
        for i in range(0, 28, 7):
            t, h = high_part[i:i+4], high_part[i+4:i+7]
            if t.strip() != "9999" and t.strip() != "":
                day_events.append({
                    "time": datetime.strptime(d_str + t.strip().zfill(4), '%Y%m%d%H%M'),
                    "type": "満潮", "cm": h.strip()
                })

        # 2. 干潮解析 (満潮解析の直後から28文字分)
        low_part = target_line[base_idx + 28 : base_idx + 56]
        for i in range(0, 28, 7):
            t, l = low_part[i:i+4], low_part[i+4:i+7]
            if t.strip() != "9999" and t.strip() != "":
                day_events.append({
                    "time": datetime.strptime(d_str + t.strip().zfill(4), '%Y%m%d%H%M'),
                    "type": "干潮", "cm": l.strip()
                })
        
        return day_events
    except Exception as e:
        # st.error(f"Error: {e}") # デバッグ用
        return []

# --- 実行 UI は前回と同じ ---
# --- メイン UI ---
with st.sidebar:
    st.header("🛠️ 設定")
    station_code = st.text_input("地点コード", "HS").upper()
    # 2026年3月3日の現在時刻を基準
    base_dt = datetime.now()
    st.write(f"現在時刻: {base_dt.strftime('%Y/%m/%d %H:%M')}")
    execute = st.button("🔥 解析実行", use_container_width=True)

if execute:
    # 三日分を連結
    all_events = []
    for i in [-1, 0, 1]:
        all_events.extend(get_day_events_fixed(base_dt + timedelta(days=i), station_code))
    
    all_events.sort(key=lambda x: x['time'])

    # 直前・直後特定
    prev = next((e for e in reversed(all_events) if e['time'] <= base_dt), None)
    nxt = next((e for e in all_events if e['time'] > base_dt), None)

    # 結果表示
    st.markdown("### 🎯 潮汐イベント特定結果")
    c1, c2 = st.columns(2)
    with c1:
        if prev:
            st.metric("🎯 直前のイベント", f"{prev['type']}", f"{prev['time'].strftime('%m/%d %H:%M')} ({prev['cm']}cm)")
        else:
            st.error("直前のイベントなし")
    with c2:
        if nxt:
            st.metric("⌛ 次のイベント", f"{nxt['type']}", f"{nxt['time'].strftime('%m/%d %H:%M')} ({nxt['cm']}cm)")
        else:
            st.error("次のイベントなし")

    st.markdown("---")
    st.markdown("### 📋 連結された全イベント（三日間）")
    if all_events:
        df = pd.DataFrame(all_events)
        df['時刻'] = df['time'].dt.strftime('%m/%d %H:%M')
        st.table(df[['時刻', 'type', 'cm']].rename(columns={'type':'種別', 'cm':'潮位(cm)'}))
    else:
        st.error("イベントが一つも抽出されておらん！")
