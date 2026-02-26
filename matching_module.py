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
        
        # --- 1. 潮位推測ロジック ---
        target_y, target_m, target_d = int(now.strftime('%y')), now.month, now.day
        day_line = next((l for l in lines if len(l) > 100 and 
                         int(l[72:74]) == target_y and 
                         int(l[74:76]) == target_m and 
                         int(l[76:78]) == target_d and 
                         l[78:80].strip() == "HS"), None)

        if day_line:
            hourly_tides = [int(day_line[i*3 : (i+1)*3].strip() or 0) for i in range(24)]
            h, m = now.hour, now.minute
            t1 = hourly_tides[h]
            t2 = hourly_tides[h+1] if h < 23 else hourly_tides[h]
            current_tide_est = int(t1 + (t2 - t1) * (m / 60.0))

            # --- 2. 3日間イベント取得（エラー回避処理） ---
            events = []
            for d_offset in [-1, 0, 1]:
                target_date = now + timedelta(days=d_offset)
                date_prefix = target_date.strftime('%Y%m%d')
                
                d_line = next((l for l in lines if len(l) > 100 and 
                               int(l[72:74]) == int(target_date.strftime('%y')) and 
                               int(l[74:76]) == target_date.month and 
                               int(l[76:78]) == target_date.day and 
                               l[78:80].strip() == "HS"), None)
                
                if d_line:
                    for start, e_type in [(80, "満潮"), (108, "干潮")]:
                        for i in range(4):
                            pos = start + (i * 7)
                            # 7文字（時刻4+潮位3）を取得
                            raw_data = d_line[pos : pos+7].strip()
                            if len(raw_data) >= 4:
                                t_str = raw_data[:4] # 確実に最初の4文字（時分）だけを取得
                                if t_str != "9999" and t_str.isdigit():
                                    try:
                                        # 秒数などの余計な解析をさせないよう、文字列連結後に解析
                                        clean_time_str = f"{date_prefix}{t_str}"
                                        ev_time = datetime.strptime(clean_time_str, '%Y%m%d%H%M')
                                        events.append({"time": ev_time, "type": e_type})
                                    except:
                                        continue
            
            events.sort(key=lambda x: x['time'])
            prev_e = next((e for e in reversed(events) if e['time'] <= now), None)
            next_e = next((e for e in events if e['time'] > now), None)

            # --- 3. 画面表示 ---
            st.subheader("🕒 現在の海況推測 (本渡瀬戸)")
            c1, c2 = st.columns(2)
            
            with c1:
                st.metric("推測現在潮位", f"{current_tide_est} cm", delta=f"{t1} → {t2}")
                st.caption(f"毎時データを分単位で補完")

            if prev_e and next_e:
                duration = (next_e['time'] - prev_e['time']).total_seconds()
                elapsed = (now - prev_e['time']).total_seconds()
                ratio = elapsed / duration
                progress = max(1, min(9, int(ratio * 10)))
                direction = "下げ" if prev_e['type'] == "満潮" else "上げ"
                
                phase_label = f"{direction}{progress}分"
                if ratio < 0.1: phase_label = f"{prev_e['type']}（止まり）"
                if ratio > 0.9: phase_label = f"{next_e['type']}（止まり）"

                with c2:
                    st.metric("潮汐フェーズ", phase_label)
                    st.write(f"次は **{next_e['type']}** ({next_e['time'].strftime('%H:%M')})")
                
                st.progress(ratio)
            
            st.divider()
            # ここに過去データとのマッチング表示を続ける
            
    except Exception as e:
        st.error(f"解析エラー: {e}")
        st.info("データの特定の箇所で読み取りエラーが発生しました。修正版を適用してください。")
