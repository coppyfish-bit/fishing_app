import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Tide Fixed-Width Debugger", layout="wide")
st.markdown("<h1 style='color: #00ffd0;'>🌊 最終固定長解析・三日連結デバッガー</h1>", unsafe_allow_html=True)

def get_day_events_fixed(date, code):
    """仕様書に基づき、カラム指定でデータをブチ抜く"""
    url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{date.year}/{code.upper()}.txt"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200: return []
        
        lines = res.text.splitlines()
        # 仕様書: 年月日は73-78カラム(2桁x3)
        yy = date.strftime('%y')
        mm = f"{date.month:2d}" # 1桁なら前にスペース
        dd = f"{date.day:2d}"   # 1桁なら前にスペース
        
        target_line = None
        for line in lines:
            # カラム73-80 (Index 72:80) をチェック
            if line[72:74] == yy and line[74:76] == mm and line[76:78] == dd:
                target_line = line
                break
        
        if not target_line: return []

        day_events = []
        d_str = date.strftime('%Y%m%d')

        # 満潮: 81-108カラム (Index 80-108) -> 7文字(4+3)×4回
        high_part = target_line[80:108]
        for i in range(0, 28, 7):
            t, h = high_part[i:i+4], high_part[i+4:i+7]
            if t != "9999":
                day_events.append({
                    "time": datetime.strptime(d_str + t, '%Y%m%d%H%M'),
                    "type": "満潮", "cm": h.strip()
                })

        # 干潮: 109-136カラム (Index 108-136) -> 7文字(4+3)×4回
        low_part = target_line[108:136]
        for i in range(0, 28, 7):
            t, l = low_part[i:i+4], low_part[i+4:i+7]
            if t != "9999":
                day_events.append({
                    "time": datetime.strptime(d_str + t, '%Y%m%d%H%M'),
                    "type": "干潮", "cm": l.strip()
                })
        
        return day_events
    except:
        return []

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
