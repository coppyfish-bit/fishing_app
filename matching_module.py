import streamlit as st
import requests
import pandas as pd
from datetime import datetime

def show_matching_page(df=None):
    st.title("🌊 潮位・10段階フェーズ判定デバッグ")
    
    now = datetime.now()
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/HS.txt"

    try:
        res = requests.get(url, timeout=10)
        lines = res.text.splitlines()
        target_y, target_m, target_d = int(now.strftime('%y')), now.month, now.day
        
        # 今日のデータ行を抽出
        day_line = next((l for l in lines if len(l) > 100 and int(l[72:74]) == target_y and int(l[74:76]) == target_m and int(l[76:78]) == target_d and l[78:80] == "HS"), None)
        
        if day_line:
            # --- 1. 満干潮時刻の抽出 ---
            events = []
            today_str = now.strftime('%Y%m%d')
            # 満潮(80列目~)、干潮(108列目~)
            for start, e_type in [(80, "満潮"), (108, "干潮")]:
                for i in range(4):
                    pos = start + (i * 7)
                    t_str = day_line[pos : pos+4].strip()
                    if t_str and t_str != "9999":
                        ev_time = datetime.strptime(today_str + t_str.zfill(4), '%Y%m%d%H%M')
                        events.append({"time": ev_time, "type": e_type})
            
            events.sort(key=lambda x: x['time'])

            # --- 2. 現在のフェーズ判定 ---
            # 直前のイベントと次のイベントを探す
            prev_e = next((e for e in reversed(events) if e['time'] <= now), None)
            next_e = next((e for e in events if e['time'] > now), None)

            st.write("### 🕒 潮汐解析結果")

            if prev_e and next_e:
                # 満干潮の間隔(秒)
                total_duration = (next_e['time'] - prev_e['time']).total_seconds()
                # 前回から現在までの経過(秒)
                elapsed = (now - prev_e['time']).total_seconds()
                
                # 1〜9の段階に分割
                progress = int((elapsed / total_duration) * 10)
                progress = max(1, min(9, progress)) # 潮止まりを除外
                
                # 次が干潮なら「下げ」、次が満潮なら「上げ」
                direction = "下げ" if next_e['type'] == "干潮" else "上げ"
                
                # 端の処理（潮止まり付近）
                if (elapsed / total_duration) < 0.1:
                    phase_label = f"{prev_e['type']}（潮止まり）"
                elif (elapsed / total_duration) > 0.9:
                    phase_label = f"{next_e['type']}（潮止まり）"
                else:
                    phase_label = f"{direction}{progress}分"

                # 結果表示
                c1, c2 = st.columns(2)
                c1.metric("現在のフェーズ", phase_label)
                c2.metric("次のイベント", f"{next_e['type']} ({next_e['time'].strftime('%H:%M')})")
                
                st.progress(elapsed / total_duration, text=f"進捗率: {int(elapsed/total_duration*100)}%")
                
            else:
                st.warning("前後どちらかの満干潮データが取得できないため、フェーズが判定できません。")
                # 最初のイベント前、または最後のイベント後の処理
                if not prev_e and next_e:
                    st.write(f"現在は本日最初のイベント（{next_e['type']}）に向かっています。")

            # --- 3. 潮位の確認 ---
            hourly_tides = [int(day_line[i*3 : (i+1)*3].strip() or 0) for i in range(24)]
            current_tide = hourly_tides[now.hour + 1] if now.minute >= 30 and now.hour < 23 else hourly_tides[now.hour]
            st.write(f"**現在の潮位（付近）:** `{current_tide} cm`")
            
            # 参考: 本日のスケジュール
            with st.expander("📅 本日の満干潮スケジュール"):
                st.table([{"時刻": e['time'].strftime('%H:%M'), "状態": e['type']} for e in events])

        else:
            st.error("データの抽出に失敗しました。")

    except Exception as e:
        st.error(f"エラー発生: {e}")

if __name__ == "__main__":
    show_matching_page()
