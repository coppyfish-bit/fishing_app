import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

def show_matching_page(df=None):
    st.title("🌊 潮位・フェーズ判定（3日間データ統合版）")
    
    now = datetime.now()
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/HS.txt"

    try:
        res = requests.get(url, timeout=10)
        lines = res.text.splitlines()
        
        events = []
        # 昨日(-1)、今日(0)、明日(+1)の3日分をループで解析
        for d_offset in [-1, 0, 1]:
            target_date = now + timedelta(days=d_offset)
            target_y, target_m, target_d = int(target_date.strftime('%y')), target_date.month, target_date.day
            date_str = target_date.strftime('%Y%m%d')

            # 対象日のデータ行（本渡：HS）を特定
            day_line = next((l for l in lines if len(l) > 100 and 
                             int(l[72:74]) == target_y and 
                             int(l[74:76]) == target_m and 
                             int(l[76:78]) == target_d and 
                             l[78:80].strip() == "HS"), None)
            
            if day_line:
                # 満潮(80〜), 干潮(108〜)
                for start, e_type in [(80, "満潮"), (108, "干潮")]:
                    for i in range(4):
                        pos = start + (i * 7)
                        raw_block = day_line[pos : pos+7].strip()
                        if len(raw_block) >= 4:
                            t_str = raw_block[:4]
                            if t_str != "9999" and t_str.isdigit():
                                try:
                                    ev_time = datetime.strptime(date_str + t_str, '%Y%m%d%H%M')
                                    events.append({"time": ev_time, "type": e_type})
                                except: continue
        
        # 全イベントを時刻順にソート
        events.sort(key=lambda x: x['time'])

        # --- 10段階フェーズ判定 ---
        # 今より前で最も近いイベント(prev)と、今より後で最も近いイベント(next)
        prev_e = next((e for e in reversed(events) if e['time'] <= now), None)
        next_e = next((e for e in events if e['time'] > now), None)

        st.write("### 🕒 リアルタイム潮汐解析")

        if prev_e and next_e:
            total_duration = (next_e['time'] - prev_e['time']).total_seconds()
            elapsed = (now - prev_e['time']).total_seconds()
            
            ratio = elapsed / total_duration
            # 1〜9段階
            progress = int(ratio * 10)
            progress = max(1, min(9, progress))
            
            # 直前が満潮なら「下げ」、直前が干潮なら「上げ」
            direction = "下げ" if prev_e['type'] == "満潮" else "上げ"
            
            # 潮止まり判定（前後10%）
            if ratio < 0.1:
                phase_label = f"{prev_e['type']}（潮止まり）"
            elif ratio > 0.9:
                phase_label = f"{next_e['type']}（潮止まり）"
            else:
                phase_label = f"{direction}{progress}分"

            # メイン表示
            col1, col2 = st.columns(2)
            with col1:
                st.metric("現在のフェーズ", phase_label)
                st.caption(f"起点: {prev_e['type']} ({prev_e['time'].strftime('%m/%d %H:%M')})")
            with col2:
                st.metric("次の潮汐時刻", next_e['time'].strftime('%H:%M'))
                st.write(f"次は **{next_e['type']}** に向かっています")
            
            st.progress(ratio, text=f"現在のフェーズ進捗: {int(ratio*100)}%")
            
        else:
            st.error("潮汐イベントの特定に失敗しました。データを確認してください。")

        # 3日間のスケジュール確認用
        with st.expander("📅 前後3日間の潮汐スケジュール（昨日〜明日）"):
            display_df = pd.DataFrame([
                {"日付": e['time'].strftime('%m/%d'), 
                 "時刻": e['time'].strftime('%H:%M'), 
                 "状態": e['type']} for e in events
            ])
            st.table(display_df)

    except Exception as e:
        st.error(f"解析エラー: {e}")

if __name__ == "__main__":
    show_matching_page()
