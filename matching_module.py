import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

def show_matching_page(df=None):
    st.title("🏹 SeaBass Matcher Pro")
    
    # 日本時間を確実に取得
    now = datetime.now()
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/HS.txt"

    try:
        res = requests.get(url, timeout=10)
        lines = res.text.splitlines()
        
        # --- 1. 潮位の分単位推測 ---
        target_y = int(now.strftime('%y'))
        target_m = now.month
        target_d = now.day
        
        # 今日の行を厳密に抽出 (72-74年, 74-76月, 76-78日, 78-80地点コード)
        day_line = None
        for line in lines:
            if len(line) < 80: continue
            try:
                if (int(line[72:74]) == target_y and 
                    int(line[74:76]) == target_m and 
                    int(line[76:78]) == target_d and 
                    line[78:80].strip() == "HS"):
                    day_line = line
                    break
            except: continue

        current_tide_est = 0
        if day_line:
            hourly_tides = [int(day_line[i*3 : (i+1)*3].strip() or 0) for i in range(24)]
            h, m = now.hour, now.minute
            t1 = hourly_tides[h]
            t2 = hourly_tides[h+1] if h < 23 else hourly_tides[h]
            current_tide_est = int(t1 + (t2 - t1) * (m / 60.0))

        # --- 2. 3日間のイベント取得と厳密な日付管理 ---
        events = []
        for d_offset in [-1, 0, 1]:
            t_date = now + timedelta(days=d_offset)
            ty, tm, td = int(t_date.strftime('%y')), t_date.month, t_date.day
            d_prefix = t_date.strftime('%Y%m%d')
            
            # 各日付の行を特定
            d_line = None
            for line in lines:
                if len(line) < 80: continue
                try:
                    if (int(line[72:74]) == ty and int(line[74:76]) == tm and 
                        int(line[76:78]) == td and line[78:80].strip() == "HS"):
                        d_line = line
                        break
                except: continue

            if d_line:
                for start, e_type in [(80, "満潮"), (108, "干潮")]:
                    for i in range(4):
                        pos = start + (i * 7)
                        t_raw = d_line[pos : pos+4].strip()
                        if t_raw and t_raw != "9999" and t_raw.isdigit():
                            ev_t = datetime.strptime(d_prefix + t_raw, '%Y%m%d%H%M')
                            events.append({"time": ev_t, "type": e_type})
        
        # 重複排除と時刻ソート
        events = sorted([dict(t) for t in {tuple(d.items()) for d in events}], key=lambda x: x['time'])

        # --- 3. フェーズ判定 ---
        # 今この瞬間に最も近い「前」と「次」のイベントを特定
        prev_e = next((e for e in reversed(events) if e['time'] <= now), None)
        next_e = next((e for e in events if e['time'] > now), None)

        st.subheader("🕒 本渡瀬戸のリアルタイム海況")
        col1, col2 = st.columns(2)

        if day_line:
            with col1:
                st.metric("推測現在潮位", f"{current_tide_est} cm", delta=f"{t1} → {t2}")
                st.caption(f"現在の推移: {'下げ（下落中）' if t2 < t1 else '上げ（上昇中）'}")

        if prev_e and next_e:
            duration = (next_e['time'] - prev_e['time']).total_seconds()
            elapsed = (now - prev_e['time']).total_seconds()
            ratio = elapsed / duration
            progress = max(1, min(9, int(ratio * 10)))
            
            direction = "下げ" if prev_e['type'] == "満潮" else "上げ"
            
            if ratio < 0.1: phase_label = f"{prev_e['type']}（止まり）"
            elif ratio > 0.9: phase_label = f"{next_e['type']}（止まり）"
            else: phase_label = f"{direction}{progress}分"

            with col2:
                st.metric("現在のフェーズ", phase_label)
                st.write(f"次は **{next_e['type']}** ({next_e['time'].strftime('%m/%d %H:%M')})")
            
            st.progress(ratio, text=f"潮汐進捗: {int(ratio*100)}%")

    except Exception as e:
        st.error(f"判定エラー: {e}")
