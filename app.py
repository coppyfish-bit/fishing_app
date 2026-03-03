import streamlit as st
import requests
from datetime import datetime, timedelta

def get_day_events_standard(date, code):
    url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{date.year}/{code.upper()}.txt"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200: return []
        
        lines = res.text.splitlines()
        # 日付文字列を作成 (例: "26 3 3") ※1桁の場合は前にスペースが入る可能性があるが、
        # 仕様書通りなら 73-78カラム（2桁x3）なので、スライスで探すのが確実。
        target_line = None
        yy, mm, dd = date.strftime('%y'), f"{date.month:2d}", f"{date.day:2d}"
        
        for line in lines:
            # 73-80カラム付近に "YYMMDDHS" があるかチェック
            # Pythonのスライスは0始まりなので カラム73-80 は [72:80]
            if line[72:74] == yy and line[74:76].strip() == str(date.month) and line[76:78].strip() == str(date.day):
                target_line = line
                break
        
        if not target_line: return []

        day_events = []
        date_str = date.strftime('%Y%m%d')

        # 1. 満潮解析 (81-108カラム -> スライス [80:108])
        # 4桁(時刻) + 3桁(潮位) の7文字セットが4つ並んでいる
        high_part = target_line[80:108]
        for i in range(0, 28, 7):
            t_str = high_part[i:i+4]   # 時刻 4桁
            h_str = high_part[i+4:i+7] # 潮位 3桁
            if t_str != "9999":
                ev_t = datetime.strptime(date_str + t_str, '%Y%m%d%H%M')
                day_events.append({"time": ev_t, "type": "満潮", "cm": int(h_str)})

        # 2. 干潮解析 (109-136カラム -> スライス [108:136])
        low_part = target_line[108:136]
        for i in range(0, 28, 7):
            t_str = low_part[i:i+4]   # 時刻 4桁
            l_str = low_part[i+4:i+7] # 潮位 3桁
            if t_str != "9999":
                ev_t = datetime.strptime(date_str + t_str, '%Y%m%d%H%M')
                day_events.append({"time": ev_t, "type": "干潮", "cm": int(l_str)})
        
        return day_events
    except Exception as e:
        return []

# --- 判定部（三日分統合） ---
def get_tide_context(base_dt, code):
    all_events = []
    # 前・今・次の3日分を回す
    for i in [-1, 0, 1]:
        all_events.extend(get_day_events_standard(base_dt + timedelta(days=i), code))
    
    all_events.sort(key=lambda x: x['time'])
    
    # 直前と直後を特定
    prev = next((e for e in reversed(all_events) if e['time'] <= base_dt), None)
    nxt = next((e for e in all_events if e['time'] > base_dt), None)
    
    return prev, nxt, all_events
