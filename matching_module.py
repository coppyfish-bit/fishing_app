import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

def show_matching_page(df=None):
    st.title("🏹 SeaBass Matcher Pro")
    st.caption("本渡瀬戸のリアルタイム推測潮位と10段階フェーズ")

    now = datetime.now()
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/HS.txt"

    try:
        res = requests.get(url, timeout=10)
        lines = res.text.splitlines()
        
        # --- 1. 潮位データの取得と推測 (Linear Interpolation) ---
        target_y, target_m, target_d = int(now.strftime('%y')), now.month, now.day
        day_line = next((l for l in lines if len(l) > 100 and 
                         int(l[72:74]) == target_y and 
                         int(l[74:76]) == target_m and 
                         int(l[76:78]) == target_d and 
                         l[78:80].strip() == "HS"), None)

        current_tide_est = 150 # デフォルト

        if day_line:
            hourly_tides = [int(day_line[i*3 : (i+1)*3].strip() or 0) for i in range(24)]
            h = now.hour
            m = now.minute
            
            # 現在の時と次の時のデータから分単位で推測
            t1 = hourly_tides[h]
            t2 = hourly_tides[h+1] if h < 23 else hourly_tides[h]
            
            # 線形補間: t1 + (t2 - t1) * (分 / 60)
            current_tide_est = int(t1 + (t2 - t1) * (m / 60.0))

            # --- 2. 3日間の潮汐イベント取得 (フェーズ用) ---
            events = []
            for d_offset in [-1, 0, 1]:
                target_date = now + timedelta(days=d_offset)
                d_str = target_date.strftime('%Y%m%d')
                d_line = next((l for l in lines if len(l) > 100 and 
                               int(l[72:74]) == int(target_date.strftime('%y')) and 
                               int(l[74:76]) == target_date.month and 
                               int(l[76:78]) == target_date.day and 
                               l[78:80].strip() == "HS"), None)
                if d_line:
                    for start, e_type in [(80, "満潮"), (108, "干潮")]:
                        for i in range(4):
                            pos = start + (i * 7)
                            t_str = d_line[pos : pos+4].strip()
                            if t_str and t_str != "9999":
                                events.append({"time": datetime.strptime(d_str + t_str, '%Y%m%d%H%M'), "type": e_type})
            
            events.sort(key=lambda x: x['time'])
            prev_e = next((e for e in reversed(events) if e['time'] <= now), None)
            next_e = next((e for e in events if e['time'] > now), None)

            # --- 3. 画面表示 ---
            st.write("### 🕒 現在の海況推測")
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("推測現在潮位", f"{current_tide_est} cm", delta=f"毎時データ: {t1}→{t2}")
                st.caption(f"※{h}:00と{h+1}:00の間を{m}分時点で補完")

            if prev_e and next_e:
                total_dur = (next_e['time'] - prev_e['time']).total_seconds()
                elapsed = (now - prev_e['time']).total_seconds()
                ratio = elapsed / total_dur
                progress = max(1, min(9, int(ratio * 10)))
                direction = "下げ" if prev_e['type'] == "満潮" else "上げ"
                
                if ratio < 0.1: phase_label = f"{prev_e['type']}（止まり）"
                elif ratio > 0.9: phase_label = f"{next_e['type']}（止まり）"
                else: phase_label = f"{direction}{progress}分"

                with col2:
                    st.metric("潮汐フェーズ", phase_label)
                    st.write(f"次は **{next_e['type']}** ({next_e['time'].strftime('%H:%M')})")
                
                st.progress(ratio, text=f"フェーズ進捗度: {int(ratio*100)}%")

            # 過去データとのマッチングなど、後続の処理へ...
            st.divider()
            st.info("この推測値を入力条件として、過去の釣果を検索します。")
            
    except Exception as e:
        st.error(f"解析エラー: {e}")
