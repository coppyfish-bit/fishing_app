import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import requests

def get_jma_tide_hs():
    """
    気象庁仕様書(1-136カラム)に完全準拠した解析ロジック
    """
    now = datetime.now()
    station_code = "HS"
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/{station_code}.txt"
    
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        lines = res.text.splitlines()
        
        # 仕様書に基づくターゲット文字列の作成
        # 年(73-74), 月(75-76), 日(77-78) + 地点(79-80)
        # ※月日が1桁の場合、気象庁は「先頭を空白」にする傾向があるため数値判定を併用
        target_y = int(now.strftime('%y'))
        target_m = now.month
        target_d = now.day
        
        day_data = None
        for line in lines:
            if len(line) < 136: continue
            
            # 仕様書通りのカラム位置から抽出
            try:
                line_y = int(line[72:74].replace(" ", "0")) # 73-74カラム
                line_m = int(line[74:76].replace(" ", "0")) # 75-76カラム
                line_d = int(line[76:78].replace(" ", "0")) # 77-78カラム
                line_st = line[78:80]                       # 79-80カラム
                
                if line_y == target_y and line_m == target_m and line_d == target_d and line_st == station_code:
                    day_data = line
                    break
            except:
                continue
        
        if not day_data:
            return 150, "データ行未発見"

        # 1. 毎時潮位 (1-72カラム: 3桁×24)
        hourly = []
        for i in range(24):
            val = day_data[i*3 : (i+1)*3].strip()
            hourly.append(int(val) if val else 0)
        
        # 現在時刻の潮位計算（線形補間）
        t1 = hourly[now.hour]
        t2 = hourly[now.hour+1] if now.hour < 23 else hourly[now.hour]
        current_cm = int(round(t1 + (t2 - t1) * (now.minute / 60.0)))

        # 2. 満潮・干潮イベント抽出 (81-108, 109-136カラム)
        events = []
        today_str = now.strftime('%Y%m%d')
        
        # 満潮: 81-108カラム (4桁時刻+3桁潮位)×4
        for i in range(4):
            start = 80 + (i * 7)
            time_part = day_data[start : start+4].strip()
            if time_part and time_part != "9999":
                ev_time = datetime.strptime(today_str + time_part.zfill(4), '%Y%m%d%H%M')
                events.append({"time": ev_time, "type": "満潮"})

        # 干潮: 109-136カラム (4桁時刻+3桁潮位)×4
        for i in range(4):
            start = 108 + (i * 7)
            time_part = day_data[start : start+4].strip()
            if time_part and time_part != "9999":
                ev_time = datetime.strptime(today_str + time_part.zfill(4), '%Y%m%d%H%M')
                events.append({"time": ev_time, "type": "干潮"})
        
        events = sorted(events, key=lambda x: x['time'])

        # 3. 潮位フェーズ判定
        phase_text = "解析中"
        prev_ev = next((e for e in reversed(events) if e['time'] <= now), None)
        next_ev = next((e for e in events if e['time'] > now), None)

        if prev_ev and next_ev:
            duration = (next_ev['time'] - prev_ev['time']).total_seconds()
            elapsed = (now - prev_ev['time']).total_seconds()
            if duration > 0:
                p_label = "上げ" if prev_ev['type'] == "干潮" else "下げ"
                step = max(1, min(9, int((elapsed / duration) * 10)))
                phase_text = f"{p_label}{step}分"
                
                # 潮止まり前後の処理
                ratio = elapsed / duration
                if ratio < 0.1: phase_text = prev_ev['type']
                elif ratio > 0.9: phase_text = next_ev['type']
        
        return current_cm, phase_text

    except Exception as e:
        return 150, f"Error:{str(e)[:5]}"

def get_realtime_weather():
    """気象と潮汐を統合"""
    t_level, t_phase = get_jma_tide_hs()
    LAT, LON = 32.4333, 130.2167 # 天草本渡
    w_data = {'temp': 15.0, 'wind': 3.0, 'wdir': "北", 'precip_48h': 0.0}
    try:
        res = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={"latitude": LAT, "longitude": LON, "current_weather": "true", "hourly": "precipitation", "past_days": 2, "timezone": "Asia/Tokyo"},
            timeout=10
        ).json()
        if 'current_weather' in res:
            cw = res['current_weather']
            w_data.update({'temp': cw['temperature'], 'wind': round(cw['windspeed']/3.6, 1)})
            dirs = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
            w_data['wdir'] = dirs[int((cw['winddirection'] + 11.25) / 22.5) % 16]
            if 'hourly' in res:
                now_h = datetime.now().hour + 48
                w_data['precip_48h'] = round(sum(res['hourly']['precipitation'][now_h-48 : now_h+1]), 1)
    except: pass
    return {**w_data, 'tide_level': t_level, 'phase': t_phase}

def show_matching_page(df):
    """診断UI"""
    st.title("🏹 SeaBass Match AI v7.0")
    if 'm_data' not in st.session_state:
        st.session_state.m_data = get_realtime_weather()

    if st.button("🔄 海況データを更新"):
        st.session_state.m_data = get_realtime_weather()
        st.rerun()

    md = st.session_state.m_data
    st.info(f"現在の本渡瀬戸: 【{md['phase']}】 {md['tide_level']}cm / {md['temp']}℃ / {md['wind']}m ({md['wdir']})")

    with st.form("main_form"):
        c1, c2 = st.columns(2)
        with c1:
            level_in = st.number_input("潮位(cm)", value=int(md['tide_level']))
            temp_in = st.number_input("気温(℃)", value=float(md['temp']))
            tide_name_in = st.selectbox("潮名", ["大潮", "中潮", "小潮", "長潮", "若潮"], index=1)
        with c2:
            p_list = ["上げ1分","上げ2分","上げ3分","上げ4分","上げ5分","上げ6分","上げ7分","上げ8分","上げ9分","満潮",
                      "下げ1分","下げ2分","下げ3分","下げ4分","下げ5分","下げ6分","下げ7分","下げ8分","下げ9分","干潮"]
            cur_p = md['phase'] if md['phase'] in p_list else "上げ5分"
            phase_in = st.selectbox("フェーズ", p_list, index=p_list.index(cur_p))
            wdir_list = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
            wdir_in = st.selectbox("風向", wdir_list, index=wdir_list.index(md['wdir']) if md['wdir'] in wdir_list else 0)
            wind_in = st.number_input("風速(m)", value=float(md['wind']))
        if st.form_submit_button("🎯 エリア診断ランキングを表示"):
            st.success("最新実績とのマッチングを開始します...")
            # ここにランキング表示処理を追加['wind']))

    if st.button("🎯 エリア診断ランキング表示"):
        if df is not None and not df.empty:
            df['is_bouzu'] = df['魚種'].astype(str).str.contains('ボウズ', na=False)
            results = []
            for place in df['場所'].unique():
                p_df = df[df['場所'] == place]
                success_df = p_df[~p_df['is_bouzu']]
                if not success_df.empty:
                    s_phase = 35 if not success_df[success_df['潮位フェーズ'] == phase_in].empty else 0
                    s_level = 25 if not success_df[abs(success_df.get('潮位_cm', 0) - level_in) <= 15].empty else 0
                    s_wdir = 15 if not success_df[success_df['風向'] == wdir_in].empty else 0
                    s_temp = 10 if not success_df[abs(success_df['気温'] - temp_in) <= 3].empty else 0
                    total = min(s_phase + s_level + s_wdir + s_temp, 99)
                    lure_mode = success_df['ルアー'].dropna().mode()
                    results.append({'place': place, 'score': total, 'hits': len(success_df), 'lure': lure_mode[0] if not lure_mode.empty else "不明"})
            
            results = sorted(results, key=lambda x: x['score'], reverse=True)
            for i, res in enumerate(results):
                st.write(f"**{i+1}位: {res['place']}** (マッチ度: {res['score']}%) / 推奨: {res['lure']}")



