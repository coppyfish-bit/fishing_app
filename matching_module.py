import streamlit as st
import requests
import pandas as pd
from datetime import datetime

def show_matching_page(df=None):
    st.title("🌊 潮位・フェーズ判定（エラー修正版）")
    
    now = datetime.now()
    # 2026年現在のデータを取得
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/HS.txt"

    try:
        res = requests.get(url, timeout=10)
        lines = res.text.splitlines()
        target_y, target_m, target_d = int(now.strftime('%y')), now.month, now.day
        
        # 今日のデータ行を抽出
        day_line = next((l for l in lines if len(l) > 100 and int(l[72:74]) == target_y and int(l[74:76]) == target_m and int(l[76:78]) == target_d and l[78:80].strip() == "HS"), None)
        
        if day_line:
            # --- 1. 満干潮時刻の抽出（修正ポイント） ---
            events = []
            today_str = now.strftime('%Y%m%d')
            
            # 満潮(80〜107列), 干潮(108〜135列) を 7文字(時刻4+潮位3) ずつ読み取る
            for start, e_type in [(80, "満潮"), (108, "干潮")]:
                for i in range(4):
                    pos = start + (i * 7)
                    raw_block = day_line[pos : pos+7].strip()
                    if len(raw_block) >= 4: # 最低限「時刻4桁」がある場合
                        t_str = raw_block[:4] # 最初の4文字だけを時刻として使う
                        if t_str != "9999" and t_str.isdigit():
                            try:
                                # 秒数などを残さないよう、時分のみを厳密に変換
                                ev_time = datetime.strptime(today_str + t_str, '%Y%m%d%H%M')
                                events.append({"time": ev_time, "type": e_type})
                            except: continue
            
            events.sort(key=lambda x: x['time'])

            st.write("### 🕒 潮汐解析結果")

            # --- 2. フェーズ判定ロジック ---
            prev_e = next((e for e in reversed(events) if e['time'] <= now), None)
            next_e = next((e for e in events if e['time'] > now), None)

            if prev_e and next_e:
                total_duration = (next_e['time'] - prev_e['time']).total_seconds()
                elapsed = (now - prev_e['time']).total_seconds()
                
                # 進捗を0〜10で計算
                ratio = elapsed / total_duration
                progress = int(ratio * 10)
                progress = max(1, min(9, progress)) # 1〜9分に収める
                
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
                col1.metric("現在のフェーズ", phase_label)
                col2.metric("次の潮汐", f"{next_e['type']} ({next_e['time'].strftime('%H:%M')})")
                
                st.progress(ratio, text=f"潮汐進捗率: {int(ratio*100)}%")
                
            else:
                st.warning("潮汐イベントの境界にいます。")

            # 満干潮スケジュールをテーブル表示
            with st.expander("📅 本日の潮汐スケジュール詳細"):
                st.table([{"時刻": e['time'].strftime('%H:%M'), "状態": e['type']} for e in events])

        else:
            st.error("本日の本渡(HS)データが見つかりませんでした。")

    except Exception as e:
        st.error(f"解析エラー: {e}")
        st.info("データの並びに予期しない値が含まれています。")

if __name__ == "__main__":
    show_matching_page()
