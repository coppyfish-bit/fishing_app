import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import requests

def get_jma_tide_hs():
    """
    気象庁の 136カラム固定長データを解析。
    日付判定を「数値抽出」から「文字列検索」に切り替え、不一致を解消。
    """
    now = datetime.now()
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/HS.txt"
    
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        lines = res.text.splitlines()
        
        # 判定用：今日の「日」を2桁で用意（25日なら '25'）
        day_str = now.strftime('%d').replace('0', ' ') if now.day < 10 else now.strftime('%d')
        month_val = now.month
        
        day_line = None
        for line in lines:
            if len(line) < 100: continue
            
            # 地点コードが HS かつ、76-77桁目が「月」、78-79桁目が「日」であるかを確認
            try:
                l_month = int(line[75:77].strip())
                l_day = int(line[77:79].strip())
                
                if l_month == month_val and l_day == now.day:
                    day_line = line
                    break
            except:
                continue
        
        if not day_line:
            return 150, "行特定失敗"

        # 1. 毎時潮位 (1-72桁)
        hourly = []
        for i in range(24):
            val = day_line[i*3 : (i+1)*3].strip()
            hourly.append(int(val) if val else 0)
        
        t1 = hourly[now.hour]
        t2 = hourly[now.hour+1] if now.hour < 23 else hourly[now.hour]
        current_cm = int(round(t1 + (t2 - t1) * (now.minute / 60.0)))

        # 2. 満潮・干潮イベント
        events = []
        today_str = now.strftime('%Y%m%d')
        for start_pos, e_type in [(80, "満潮"), (108, "干潮")]:
            for i in range(4):
                p = start_pos + (i * 7)
                t_str = day_line[p : p+4].strip()
                if t_str and t_str != "9999":
                    ev_t = datetime.strptime(today_str + t_str.zfill(4), '%Y%m%d%H%M')
                    events.append({"time": ev_t, "type": e_type})
        
        events = sorted(events, key=lambda x: x['time'])
        
        # 3. フェーズ判定
        phase = "判定中"
        prev_ev = next((e for e in reversed(events) if e['time'] <= now), None)
        next_ev = next((e for e in events if e['time'] > now), None)
        
        if prev_ev and next_ev:
            dur = (next_ev['time'] - prev_ev['time']).total_seconds()
            ela = (now - prev_ev['time']).total_seconds()
            p_label = "上げ" if prev_ev['type'] == "干潮" else "下げ"
            step = max(1, min(9, int((ela / dur) * 10)))
            phase = f"{p_label}{step}分"
            if ela/dur < 0.1: phase = prev_ev['type']
            elif ela/dur > 0.9: phase = next_ev['type']
            
        return current_cm, phase
    except Exception as e:
        return 150, f"Error:{str(e)[:5]}"

def get_realtime_weather():
    """気象と潮汐を統合取得"""
    t_level, t_phase = get_jma_tide_hs()
    LAT, LON = 32.4333, 130.2167
    
    w_data = {'temp': 15.0, 'wind': 3.0, 'wdir': "北", 'precip_48h': 0.0}
    try:
        res = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": LAT, "longitude": LON,
                "current_weather": "true", "hourly": "precipitation",
                "past_days": 2, "timezone": "Asia/Tokyo"
            }, timeout=10
        ).json()
        
        if 'current_weather' in res:
            cw = res['current_weather']
            w_data['temp'] = cw['temperature']
            w_data['wind'] = round(cw['windspeed'] / 3.6, 1)
            dirs = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
            w_data['wdir'] = dirs[int((cw['winddirection'] + 11.25) / 22.5) % 16]
            if 'hourly' in res:
                now_h = datetime.now().hour + 48
                precip = res['hourly']['precipitation']
                w_data['precip_48h'] = round(sum(precip[now_h-48 : now_h+1]), 1)
    except:
        pass
    return {**w_data, 'tide_level': t_level, 'phase': t_phase}

def show_matching_page(df):
    """メイン診断UI"""
    st.title("🏹 SeaBass Match AI v6.7")

    if 'm_data' not in st.session_state:
        st.session_state.m_data = get_realtime_weather()

    if st.button("🔄 海況・潮汐データを同期"):
        st.session_state.m_data = get_realtime_weather()
        st.rerun()

    md = st.session_state.m_data

    # UI表示
    st.info(f"現在の本渡瀬戸: 【{md['phase']}】 {md['tide_level']}cm / {md['temp']}℃ / {md['wind']}m ({md['wdir']})")

    with st.expander("条件を微調整して診断", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            level_in = st.number_input("潮位(cm)", value=int(md['tide_level']))
            temp_in = st.number_input("気温(℃)", value=float(md['temp']))
            tide_name_in = st.selectbox("潮名", ["大潮", "中潮", "小潮", "長潮", "若潮"], index=1)
        with c2:
            p_list = ["上げ1分","上げ2分","上げ3分","上げ4分","上げ5分","上げ6分","上げ7分","上げ8分","上げ9分","満潮",
                      "下げ1分","下げ2分","下げ3分","下げ4分","下げ5分","下げ6分","下げ7分","下げ8分","下げ9分","干潮"]
            phase_in = st.selectbox("フェーズ", p_list, index=p_list.index(md['phase']) if md['phase'] in p_list else 4)
            wdir_list = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
            wdir_in = st.selectbox("風向", wdir_list, index=wdir_list.index(md['wdir']) if md['wdir'] in wdir_list else 0)
            wind_in = st.number_input("風速(m)", value=float(md['wind']))
        precip_in = st.number_input("48h降水量(mm)", value=float(md['precip_48h']))

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
