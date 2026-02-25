import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import requests

def get_jma_tide_hs():
    """気象庁フルフォーマット(136col)を解析してHS地点の潮位・フェーズを取得"""
    now = datetime.now()
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/pre/txt/{now.year}/HS.txt"
    
    # フォールバック用
    default_res = (150, "上げ5分")
    
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200: return default_res
        
        lines = res.text.splitlines()
        if len(lines) < now.day: return default_res
        
        line = lines[now.day - 1]
        
        # 1. 毎時潮位の取得 (1-72カラム: 3桁×24)
        hour_tides = [int(line[i*3:i*3+3].strip()) for i in range(24)]
        current_tide = hour_tides[now.hour]
        
        # 2. 満潮・干潮時刻の抽出 (81-108, 109-136カラム)
        high_tides = [] # (時刻, 潮位)
        low_tides = []
        
        for i in range(4):
            # 満潮 (時刻4桁, 潮位3桁)
            h_time = line[80+i*7:84+i*7].strip()
            h_level = line[84+i*7:87+i*7].strip()
            if h_time != "9999":
                high_tides.append(int(h_time))
                
            # 干潮
            l_time = line[108+i*7:112+i*7].strip()
            l_level = line[112+i*7:115+i*7].strip()
            if l_time != "9999":
                low_tides.append(int(l_time))

        # 3. 現在時刻から直近のイベントを探してフェーズ判定
        now_time_int = now.hour * 100 + now.minute
        all_events = sorted([(t, 'high') for t in high_tides] + [(t, 'low') for t in low_tides])
        
        # 直前のイベントと直後のイベントを特定
        prev_ev = all_events[-1] if all_events[0][0] > now_time_int else None
        next_ev = all_events[0] if all_events[-1][0] < now_time_int else None
        
        for i in range(len(all_events)-1):
            if all_events[i][0] <= now_time_int <= all_events[i+1][0]:
                prev_ev, next_ev = all_events[i], all_events[i+1]
                break
        
        if not prev_ev or not next_ev: return current_tide, "上げ5分"

        # 進捗率計算 (0.0 ~ 1.0)
        duration = next_ev[0] - prev_ev[0] # 簡易的な分計算（時分を跨ぐ場合は考慮が必要だが概算には十分）
        # 正確な分換算
        def to_min(t): return (t // 100) * 60 + (t % 100)
        progress = (to_min(now_time_int) - to_min(prev_ev[0])) / (to_min(next_ev[0]) - to_min(prev_ev[0]))
        
        status = "下げ" if prev_ev[1] == 'high' else "上げ"
        p_val = int(progress * 9) + 1
        
        # 満干潮の端っこ判定
        if progress > 0.92: phase = "満潮" if next_ev[1] == 'high' else "干潮"
        elif progress < 0.08: phase = "干潮" if prev_ev[1] == 'low' else "満潮"
        else: phase = f"{status}{min(max(p_val, 1), 9)}分"
        
        return current_tide, phase

    except:
        return default_res

def show_matching_page(df):
    # (スタイル設定は共通のため省略)
    st.title("🏹 SeaBass Match AI v5.0")
    st.caption("気象庁 136カラム・フルデータ解析モード (地点: HS)")

    if 'm_data' not in st.session_state:
        st.session_state.m_data = get_realtime_weather()

    # --- 同期・入力セクション ---
    st.markdown("<div class='input-card'>", unsafe_allow_html=True)
    if st.button("🔄 気象庁136colデータと同期"):
        st.session_state.m_data = get_realtime_weather()
        st.rerun()

    md = st.session_state.m_data
    # (UIの表示部分は前述の通り)
    # 優先順位: 1.フェーズ(35), 2.潮位(25), 3.風向き(15), 4.気温(10), 5.他(15)
