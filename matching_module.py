import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import requests

def get_jma_tide_hs():
    """気象庁フルフォーマット(136col)を解析してHS地点(本渡)の潮位・フェーズを取得"""
    now = datetime.now()
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/pre/txt/{now.year}/HS.txt"
    
    # 失敗時のデフォルト値
    default_res = (150, "上げ5分")
    
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200: return default_res
        
        lines = res.text.splitlines()
        if len(lines) < now.day: return default_res
        
        line = lines[now.day - 1] # 当日の行
        
        # 1. 毎時潮位 (1-72カラム: 3桁×24時間)
        hour_tides = []
        for i in range(24):
            val = line[i*3 : i*3+3].strip()
            hour_tides.append(int(val) if val else 0)
        current_tide = hour_tides[now.hour]
        
        # 2. 満潮・干潮時刻 (81-108, 109-136カラム)
        # 満潮: 81-87, 88-94, 95-101, 102-108
        # 干潮: 109-115, 116-122, 123-129, 130-136
        events = []
        for i in range(4):
            # 満潮
            h_time = line[80+i*7 : 84+i*7].strip()
            if h_time != "9999" and h_time:
                events.append({'time': int(h_time), 'type': 'high'})
            # 干潮
            l_time = line[108+i*7 : 112+i*7].strip()
            if l_time != "9999" and l_time:
                events.append({'time': int(l_time), 'type': 'low'})

        # 時刻順にソート
        events = sorted(events, key=lambda x: x['time'])
        now_time_int = now.hour * 100 + now.minute
        
        # 直前と直後のイベントを特定
        prev_ev = None
        next_ev = None
        
        # 今日の全イベントの中で現在の位置を探す
        for i in range(len(events)):
            if events[i]['time'] <= now_time_int:
                prev_ev = events[i]
            if events[i]['time'] > now_time_int:
                next_ev = events[i]
                break
        
        # イベントが見つからない（日付跨ぎ等）は簡易判定
        if not prev_ev or not next_ev:
            next_h = hour_tides[(now.hour + 1) % 24]
            return current_tide, ("上げ5分" if next_h > current_tide else "下げ5分")

        # 進捗率計算 (分換算)
        def to_min(t): return (t // 100) * 60 + (t % 100)
        p_min = to_min(prev_ev['time'])
        n_min = to_min(next_ev['time'])
        curr_min = to_min(now_time_int)
        
        progress = (curr_min - p_min) / (n_min - p_min) if (n_min - p_min) != 0 else 0.5
        
        status = "下げ" if prev_ev['type'] == 'high' else "上げ"
        p_val = int(progress * 9) + 1
        
        # 端っこ判定 (満干潮の前後15分程度を端とする)
        if progress > 0.90: phase = "満潮" if next_ev['type'] == 'high' else "干潮"
        elif progress < 0.10: phase = "干潮" if prev_ev['type'] == 'low' else "満潮"
        else: phase = f"{status}{min(max(p_val, 1), 9)}分"
        
        return current_tide, phase
    except:
        return default_res

def get_realtime_weather():
    """HS地点の潮汐と気象データを統合"""
    tide_level, phase = get_jma_tide_hs()
    
    LAT, LON = 32.4333, 130.2167
    now = datetime.now()
    data = {
        'tide': "中潮", 'temp': 15.0, 'wind': 3.0, 'wdir': "北", 
        'tide_level': tide_level, 'phase': phase, 'precip_48h': 0.0
    }
    
    try:
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current_weather=true&hourly=precipitation&past_days=2&timezone=Asia%2FTokyo"
        w_res = requests.get(w_url, timeout=5).json()
        if 'current_weather' in w_res:
            cw = w_res['current_weather']
            data['temp'] = float(cw.get('temperature', 15.0))
            data['wind'] = float(cw.get('windspeed', 3.0))
            directions = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
            data['wdir'] = directions[int((cw.get('winddirection', 0) + 22.5) / 45) % 8]
            
            if 'hourly' in w_res:
                h_idx = 48 + now.hour
                p_list = w_res['hourly'].get('precipitation', [0.0]*72)
                data['precip_48h'] = round(sum(p_list[h_idx-48:h_idx+1]), 1)
    except: pass
    return data

def show_matching_page(df):
    st.markdown("""
        <style>
        .stButton>button { background-color: #ff4b6c; color: white; border-radius: 25px; border: none; padding: 12px; font-weight: bold; width: 100%; }
        .input-card { background-color: #1e1e1e; padding: 20px; border-radius: 15px; border: 1px solid #333; margin-bottom: 20px; }
        .recommend-card { background: linear-gradient(135deg, #2c3e50 0%, #000000 100%); padding: 20px; border-radius: 15px; border-left: 5px solid #ff4b6c; margin-bottom: 15px; color: white; position: relative; }
        .score-badge { position: absolute; top: 20px; right: 20px; font-size: 1.8rem; font-weight: bold; color: #ff4b6c; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🏹 SeaBass Match AI v5.1")
    st.caption("気象庁(HS本渡) 136カラム解析 & 独自優先順位アルゴリズム")

    if 'm_data' not in st.session_state:
        st.session_state.m_data = get_realtime_weather()

    st.markdown("<div class='input-card'>", unsafe_allow_html=True)
    if st.button("🔄 本渡(HS)の最新データを同期"):
        st.session_state.m_data = get_realtime_weather()
        st.rerun()

    md = st.session_state.m_data
    c1, c2 = st.columns(2)
    with c1:
        tide_in = st.selectbox("潮名", ["大潮", "中潮", "小潮", "長潮", "若潮"], index=1)
        level_in = st.number_input("潮位 (cm)", value=int(md.get('tide_level', 150)))
        temp_in = st.number_input("気温 (℃)", value=float(md.get('temp', 15.0)))
    with c2:
        p_list = ["上げ1分","上げ3分","上げ5分","上げ7分","上げ9分","満潮","下げ1分","下げ3分","下げ5分","下げ7分","下げ9分","干潮"]
        cur_p = md.get('phase', '上げ5分')
        p_idx = p_list.index(cur_p) if cur_p in p_list else 2
        phase_in = st.selectbox("潮位フェーズ", p_list, index=p_idx)
        wdir_in = st.selectbox("風向", ["北", "北東", "東", "南東", "南", "南西", "西", "北西"], 
                               index=["北", "北東", "東", "南東", "南", "南西", "西", "北西"].index(md.get('wdir', '北')))
        wind_in = st.number_input("風速 (m/s)", value=float(md.get('wind', 3.0)))
    
    precip_in = st.number_input("48h降水量合計 (mm)", value=float(md.get('precip_48h', 0.0)))
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("🎯 エリア診断ランキング表示"):
        if df is not None and not df.empty:
            df['is_bouzu'] = df['魚種'].astype(str).str.contains('ボウズ', na=False)
            results = []
            for place in df['場所'].unique():
                p_df = df[df['場所'] == place]
                success_df = p_df[~p_df['is_bouzu']]
                if not success_df.empty:
                    # スコア配点: フェーズ(35), 潮位(25), 風向(15), 気温(10), 他(15)
                    s_phase = 35 if not success_df[success_df['潮位フェーズ'] == phase_in].empty else 0
                    s_level = 25 if not success_df[abs(success_df.get('潮位_cm', 0) - level_in) <= 15].empty else 0
                    s_wdir = 15 if not success_df[success_df['風向'] == wdir_in].empty else 0
                    s_temp = 10 if not success_df[abs(success_df['気温'] - temp_in) <= 3].empty else 0
                    s_others = (5 if not success_df[success_df['潮名'] == tide_in].empty else 0) + \
                               (5 if not success_df[abs(success_df['風速'] - wind_in) <= 2].empty else 0) + \
                               (5 if '48時間降水量' in success_df.columns and not success_df[abs(success_df['48時間降水量'] - precip_in) <= 10].empty else 0)
                    
                    total = min(s_phase + s_level + s_wdir + s_temp + s_others, 99)
                    lure_mode = success_df['ルアー'].dropna().mode()
                    results.append({'place': place, 'score': total, 'hits': len(success_df), 'lure': lure_mode[0] if not lure_mode.empty else "未登録"})
            
            results = sorted(results, key=lambda x: x['score'], reverse=True)
            for i, res in enumerate(results):
                st.markdown(f"<div class='recommend-card'><div class='score-badge'>{res['score']}%</div><b>{i+1}位: {res['place']}</b><br>実績: {res['hits']}件 / 推奨: {res['lure']}</div>", unsafe_allow_html=True)
