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
        
        # --- 1. 3日間の全イベントを正確に抽出 ---
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
                # 満潮(80~), 干潮(108~)
                for start, e_type in [(80, "満潮"), (108, "干潮")]:
                    for i in range(4):
                        pos = start + (i * 7)
                        t_raw = d_line[pos : pos+4].strip()
                        if t_raw and t_raw != "9999" and t_raw.isdigit():
                            ev_t = datetime.strptime(d_str + t_raw, '%Y%m%d%H%M')
                            events.append({"time": ev_t, "type": e_type})
        
        # 時刻順にソート（これが重要）
        events.sort(key=lambda x: x['time'])

        # --- 2. 現在時刻を挟む「前」と「次」のイベントを特定 ---
        prev_e = None
        next_e = None
        for i in range(len(events) - 1):
            if events[i]['time'] <= now < events[i+1]['time']:
                prev_e = events[i]
                next_e = events[i+1]
                break

        # --- 3. 画面表示と判定 ---
        if prev_e and next_e:
            duration = (next_e['time'] - prev_e['time']).total_seconds()
            elapsed = (now - prev_e['time']).total_seconds()
            ratio = elapsed / duration
            
            # 10段階計算
            progress = max(1, min(9, int(ratio * 10)))
            
            # 【判定の核心】直前が満潮なら「下げ」、直前が干潮なら「上げ」
            direction = "下げ" if prev_e['type'] == "満潮" else "上げ"
            
            if ratio < 0.1: phase_label = f"{prev_e['type']}（潮止まり）"
            elif ratio > 0.9: phase_label = f"{next_e['type']}（潮止まり）"
            else: phase_label = f"{direction}{progress}分"

            st.subheader("🕒 本渡瀬戸のリアルタイム海況")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("現在のフェーズ", phase_label)
                st.caption(f"起点: {prev_e['type']} ({prev_e['time'].strftime('%H:%M')})")
            with col2:
                st.metric("次の潮汐", next_e['type'])
                st.write(f"時刻: **{next_e['time'].strftime('%H:%M')}**")
            
            st.progress(ratio, text=f"進捗率: {int(ratio*100)}%")

        # スケジュール確認（デバッグ用）
        with st.expander("📅 潮汐スケジュール確認"):
            st.table([{"日付": e['time'].strftime('%m/%d'), "時刻": e['time'].strftime('%H:%M'), "状態": e['type']} for e in events if abs((e['time']-now).days) <= 1])

    except Exception as e:
        st.error(f"判定エラー: {e}")
