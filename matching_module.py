import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

def show_matching_page(df=None):
    st.title("🏹 SeaBass Matcher Pro")
    
    now = datetime.now()
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/HS.txt"

    try:
        res = requests.get(url, timeout=10)
        lines = res.text.splitlines()
        
        # --- 1. 潮位の分単位推測 (推測ロジック復活) ---
        target_y, target_m, target_d = int(now.strftime('%y')), now.month, now.day
        day_line = next((l for l in lines if len(l) > 100 and 
                         int(l[72:74]) == target_y and 
                         int(l[74:76]) == target_m and 
                         int(l[76:78]) == target_d and 
                         l[78:80].strip() == "HS"), None)
        
        current_tide_est = 0
        if day_line:
            hourly_tides = [int(day_line[i*3 : (i+1)*3].strip() or 0) for i in range(24)]
            h, m = now.hour, now.minute
            t1 = hourly_tides[h]
            t2 = hourly_tides[h+1] if h < 23 else hourly_tides[h]
            # 線形補間
            current_tide_est = int(t1 + (t2 - t1) * (m / 60.0))

        # --- 2. 3日間のイベント取得と厳密なソート ---
        events = []
        for d_offset in [-1, 0, 1]:
            t_date = now + timedelta(days=d_offset)
            d_str = t_date.strftime('%Y%m%d')
            d_line = next((l for l in lines if len(l) > 100 and 
                           int(l[72:74]) == int(t_date.strftime('%y')) and 
                           int(l[74:76]) == t_date.month and 
                           int(l[76:78]) == t_date.day and 
                           l[78:80].strip() == "HS"), None)
            if d_line:
                for start, e_type in [(80, "満潮"), (108, "干潮")]:
                    for i in range(4):
                        pos = start + (i * 7)
                        t_raw = d_line[pos : pos+4].strip()
                        if t_raw and t_raw != "9999" and t_raw.isdigit():
                            ev_t = datetime.strptime(d_str + t_raw, '%Y%m%d%H%M')
                            events.append({"time": ev_t, "type": e_type})
        
        # 重複を排除して時刻順にソート
        events = sorted([dict(t) for t in {tuple(d.items()) for d in events}], key=lambda x: x['time'])

        # --- 3. フェーズ判定 ---
        prev_e = next((e for e in reversed(events) if e['time'] <= now), None)
        next_e = next((e for e in events if e['time'] > now), None)

        st.subheader("🕒 本渡瀬戸のリアルタイム海況")
        col1, col2 = st.columns(2)

        if day_line:
            with col1:
                st.metric("推測現在潮位", f"{current_tide_est} cm", delta=f"{t1}→{t2}")
                st.caption(f"現在の推移: {'下落中' if t2 < t1 else '上昇中'}")

        if prev_e and next_e:
            duration = (next_e['time'] - prev_e['time']).total_seconds()
            elapsed = (now - prev_e['time']).total_seconds()
            ratio = elapsed / duration
            progress = max(1, min(9, int(ratio * 10)))
            
            # 直前が「満潮」なら「下げ」、直前が「干潮」なら「上げ」
            direction = "下げ" if prev_e['type'] == "満潮" else "上げ"
            
            if ratio < 0.1: phase_label = f"{prev_e['type']}（止まり）"
            elif ratio > 0.9: phase_label = f"{next_e['type']}（止まり）"
            else: phase_label = f"{direction}{progress}分"

            with col2:
                st.metric("現在のフェーズ", phase_label)
                st.write(f"次は **{next_e['type']}** ({next_e['time'].strftime('%H:%M')})")
            
            st.progress(ratio, text=f"進捗: {int(ratio*100)}%")

    except Exception as e:
        st.error(f"判定エラー: {e}")
