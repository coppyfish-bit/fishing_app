import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

def calculate_tide_phase_10(now_time, events):
    """
    満干潮の間隔を10分割し、「上げ○分」「下げ○分」を算出する魔導書
    """
    # 時刻順にソート
    sorted_events = sorted(events, key=lambda x: x['time'])
    now_str = now_time.strftime("%H:%M")
    
    prev_ev = None
    next_ev = None
    
    # 現在時刻を挟む「前」と「後」のイベントを特定
    for i in range(len(sorted_events)):
        if sorted_events[i]['time'] <= now_str:
            prev_ev = sorted_events[i]
        else:
            next_ev = sorted_events[i]
            break
            
    if not prev_ev or not next_ev:
        return "潮止まり（計算不能）", 0

    # 時刻文字列をdatetimeオブジェクトに変換して差分を計算
    fmt = "%H:%M"
    t_prev = datetime.strptime(prev_ev['time'], fmt)
    t_next = datetime.strptime(next_ev['time'], fmt)
    t_now = datetime.strptime(now_str, fmt)
    
    # 全体の時間幅（分）と、経過時間（分）
    total_duration = (t_next - t_prev).total_seconds() / 60
    elapsed_time = (t_now - t_prev).total_seconds() / 60
    
    # 10分割の判定 (0〜10の整数に変換)
    phase_num = int((elapsed_time / total_duration) * 10)
    # 10分（潮止まり直前）を10に固定
    phase_num = min(max(phase_num, 0), 10)
    
    # 上げか下げかの判定
    if prev_ev['type'] == 'low':
        return f"📈 上げ {phase_num} 分", phase_num
    else:
        return f"📉 下げ {phase_num} 分", phase_num

# --- 👿 表示エリア（テストボタンの中身を書き換え） ---
if st.button("🔥 潮汐フェーズを精密解析せよ"):
    day_info, err = test_load_json("HS") # 前述の関数を使用
    
    if day_info:
        now = datetime.now()
        phase_text, phase_val = calculate_tide_phase_10(now, day_info['events'])
        
        # --- 📊 魂の表示エリア ---
        st.markdown("---")
        
        # 巨大なフェーズ表示
        st.markdown(f"""
            <div style="text-align: center; padding: 20px; background: rgba(255, 75, 75, 0.1); border-radius: 15px; border: 2px solid #ff4b4b;">
                <h3 style="color: #cccccc; margin: 0;">現在の潮汐フェーズ</h3>
                <h1 style="color: #ff4b4b; font-size: 3.5rem; margin: 10px 0;">{phase_text}</h1>
            </div>
        """, unsafe_allow_html=True)

        # 10分割インジケーター（視覚化）
        st.write("【10分割インジケーター】")
        st.progress(phase_val / 10.0)
        
        # 補足情報
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"🕒 現在時刻: {now.strftime('%H:%M')}")
        with col2:
            st.write(f"📏 潮位目安: {day_info['hourly'][now.hour]} cm")
            
    else:
        st.error(f"データ取得失敗: {err}")
