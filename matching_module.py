import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import requests

def get_jma_tide_hs():
    """本渡瀬戸(HS)の潮位とフェーズを取得"""
    station_code = "HS"
    now = datetime.now()
    
    # 取得失敗時のデフォルト
    default_res = (150, "取得失敗")
    
    try:
        # 1. データの取得
        url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/{station_code}.txt"
        res = requests.get(url, timeout=10)
        if res.status_code != 200: return default_res
        
        lines = res.text.splitlines()
        day_data = None
        
        # 2. 該当する日の行を特定 (数値変換で比較するのが最も確実)
        target_y = int(now.strftime('%y'))
        target_m = now.month
        target_d = now.day
        
        for line in lines:
            if len(line) < 80: continue
            try:
                line_y = int(line[72:75].strip())
                line_m = int(line[75:77].strip())
                line_d = int(line[77:79].strip())
                if line_y == target_y and line_m == target_m and line_d == target_d:
                    day_data = line
                    break
            except:
                continue
        
        if not day_data: return default_res

        # 3. 毎時潮位の取得と現在潮位の計算
        hourly = []
        for i in range(24):
            val = day_data[i*3 : (i+1)*3].strip()
            hourly.append(int(val) if val else 0)
        
        t1 = hourly[now.hour]
        t2 = hourly[now.hour+1] if now.hour < 23 else hourly[now.hour]
        current_cm = int(round(t1 + (t2 - t1) * (now.minute / 60.0)))

        # 4. 満潮・干潮イベントの抽出
        event_times = []
        today_ymd = now.strftime('%Y%m%d')

        # 満潮抽出
        for i in range(4):
            start = 80 + (i * 7)
            t_part = day_data[start : start+4].strip()
            if t_part and t_part.isdigit() and t_part != "9999":
                ev_time = datetime.strptime(today_ymd + t_part.zfill(4), '%Y%m%d%H%M')
                event_times.append({"time": ev_time, "type": "満潮"})

        # 干潮抽出
        for i in range(4):
            start = 108 + (i * 7)
            t_part = day_data[start : start+4].strip()
            if t_part and t_part.isdigit() and t_part != "9999":
                ev_time = datetime.strptime(today_ymd + t_part.zfill(4), '%Y%m%d%H%M')
                event_times.append({"time": ev_time, "type": "干潮"})

        event_times = sorted(event_times, key=lambda x: x['time'])

        # 5. フェーズ計算 (ここが以前は return のせいで動いていませんでした)
        phase_text = "潮止まり"
        prev_ev = next((e for e in reversed(event_times) if e['time'] <= now), None)
        next_ev = next((e for e in event_times if e['time'] > now), None)

        if prev_ev and next_ev:
            duration = (next_ev['time'] - prev_ev['time']).total_seconds()
            elapsed = (now - prev_ev['time']).total_seconds()
            if duration > 0:
                step = max(1, min(9, int((elapsed / duration) * 10)))
                p_label = "上げ" if prev_ev['type'] == "干潮" else "下げ"
                phase_text = f"{p_label}{step}分"
                
                # 潮止まり前後の微調整
                ratio = elapsed / duration
                if ratio < 0.1: phase_text = prev_ev['type']
                elif ratio > 0.9: phase_text = next_ev['type']
        
        return current_cm, phase_text

    except Exception as e:
        st.error(f"潮位解析内部エラー: {e}")
        return default_res

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
    except: pass
    return {**w_data, 'tide_level': t_level, 'phase': t_phase}

def show_matching_page(df):
    """メイン診断UI表示"""
    st.title("🏹 SeaBass Match AI v6.8")

    if 'm_data' not in st.session_state:
        st.session_state.m_data = get_realtime_weather()

    if st.button("🔄 データを最新に更新"):
        st.session_state.m_data = get_realtime_weather()
        st.rerun()

    md = st.session_state.m_data
    st.info(f"現在の本渡瀬戸: 【{md['phase']}】 {md['tide_level']}cm / {md['temp']}℃ / {md['wind']}m ({md['wdir']})")
    
    # --- 以下、診断フォーム (省略せず実装してください) ---
    with st.expander("条件を微調整して診断", expanded=True):
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

