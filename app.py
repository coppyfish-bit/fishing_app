import streamlit as st
import requests
import re
from datetime import datetime
import pandas as pd

st.set_page_config(page_title="Tide Detail Debugger", layout="wide")

st.markdown("<h1 style='color: #00ffd0;'>🌊 潮位・直近イベント解析デバッガー</h1>", unsafe_allow_html=True)

# 観測所定義
TIDE_STATIONS = [{"name": "本渡瀬戸", "code": "HS"}, {"name": "三角", "code": "MS"}, {"name": "苓北", "code": "RH"}]

with st.sidebar:
    st.header("⚙️ パラメータ")
    station = st.selectbox("観測所", TIDE_STATIONS, format_func=lambda x: x['name'])
    target_date = st.date_input("解析日", datetime.now())
    target_time = st.time_input("解析時刻（この直前のイベントを探します）", datetime.now().time())
    execute = st.button("🔥 潮位データを解析", use_container_width=True)

if execute:
    now_dt = datetime.combine(target_date, target_time)
    code = station['code']
    url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{now_dt.year}/{code}.txt"
    
    st.info(f"🌐 取得先: {url}")
    
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            st.error("データ取得失敗")
        else:
            lines = res.text.splitlines()
            # 正規表現で日付と地点を検索 (YY MM DD HS)
            yy, mm, dd = now_dt.strftime('%y'), str(now_dt.month), str(now_dt.day)
            pattern = rf"{yy}\s+{mm}\s+{dd}\s*{code}"
            
            target_line = next((l for l in lines if re.search(pattern, l)), None)
            
            if not target_line:
                st.error("該当日のデータ行が見つかりません。")
            else:
                st.success("✅ データ行を特定しました。")
                st.code(target_line)
                
                # 全数値を抽出
                nums = re.findall(r'-?\d+', target_line)
                
                # 1. 現在の潮位
                hourly = [int(n) for n in nums[:24]]
                h, m = now_dt.hour, now_dt.minute
                t1 = hourly[h]
                t2 = hourly[h+1] if h < 23 else hourly[h]
                current_cm = int(round(t1 + (t2 - t1) * (m / 60.0)))
                
                # 2. 満干潮イベントのリスト化
                event_data = nums[27:]
                events = []
                today_str = now_dt.strftime('%Y%m%d')
                
                for i in range(0, 8, 2): # 満潮
                    if i+1 < len(event_data) and event_data[i] != "9999":
                        ev_t = datetime.strptime(today_str + event_data[i].zfill(4), '%Y%m%d%H%M')
                        events.append({"time": ev_t, "type": "満潮", "cm": event_data[i+1]})
                
                for i in range(8, 16, 2): # 干潮
                    if i+1 < len(event_data) and event_data[i] != "9999":
                        ev_t = datetime.strptime(today_str + event_data[i].zfill(4), '%Y%m%d%H%M')
                        events.append({"time": ev_t, "type": "干潮", "cm": event_data[i+1]})
                
                events.sort(key=lambda x: x['time'])
                
                # 3. 「直前」と「直後」を特定
                prev_event = None
                next_event = None
                for e in events:
                    if e['time'] <= now_dt:
                        prev_event = e
                    elif e['time'] > now_dt and next_event is None:
                        next_event = e
                
                # --- 結果表示 ---
                col1, col2, col3 = st.columns(3)
                col1.metric("推定潮位", f"{current_cm} cm")
                
                if prev_event:
                    col2.metric("🎯 直前のイベント", f"{prev_event['type']}", f"{prev_event['time'].strftime('%H:%M')} ({prev_event['cm']}cm)", delta_color="inverse")
                else:
                    col2.write("直前のイベントなし")
                
                if next_event:
                    col3.metric("⌛ 次のイベント", f"{next_event['type']}", f"{next_event['time'].strftime('%H:%M')} ({next_event['cm']}cm)")

                st.markdown("### 📋 本日の全イベント一覧")
                st.table(pd.DataFrame([{"時刻": e['time'].strftime('%H:%M'), "種別": e['type'], "潮位(cm)": e['cm']} for e in events]))

    except Exception as e:
        st.error(f"解析エラー: {e}")
