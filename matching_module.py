import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests

def get_jma_tide_hs():
    """
    気象庁の suisan/txt フォーマット(136col)を解析。
    URL: https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/2026/HS.txt
    """
    now = datetime.now()
    station_code = "HS"
    # 2026年の本渡(HS)データURL
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/{station_code}.txt"
    
    # 取得失敗時のデフォルト値
    default_res = (150, "上げ5分")
    
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            return default_res
        
        lines = res.text.splitlines()
        # 73-78カラムの年月日形式 (例: 26 225)
        target_ymd = now.strftime('%y') + f"{now.month:2d}" + f"{now.day:2d}"
        
        day_data = None
        for line in lines:
            if len(line) < 80: continue
            # カラム72:78(年月日)と78:80(地点名)で照合
            if line[72:78] == target_ymd and line[78:80] == station_code:
                day_data = line
                break
        
        if not day_data:
            return default_res

        # 1. 毎時潮位の取得と分単位の線形補間
        hourly = []
        for i in range(24):
            val = day_data[i*3 : (i+1)*3].strip()
            hourly.append(int(val) if val else 0)
        
        t1 = hourly[now.hour]
        t2 = hourly[now.hour+1] if now.hour < 23 else hourly[now.hour]
        current_cm = int(round(t1 + (t2 - t1) * (now.minute / 60.0)))

        # 2. 満潮・干潮時刻の抽出 (81-108, 109-136カラム)
        events = []
        today_str = now.strftime('%Y%m%d')
        # 満潮データ(4回分)
        for i in range(4):
            start = 80 + (i * 7)
            t_part = day_data[start : start+4].strip()
            if t_part and t_part != "9999":
                ev_time = datetime.strptime(today_str + t_part.zfill(4), '%Y%m%d%H%M')
                events.append({"time": ev_time, "type": "満潮"})
        # 干潮データ(4回分)
        for i in range(4):
            start = 108 + (i * 7)
            t_part = day_data[start : start+4].strip()
            if t_part and t_part != "9999":
                ev_time = datetime.strptime(today_str + t_part.zfill(4), '%Y%m%d%H%M')
                events.append({"time": ev_time, "type": "干潮"})
        
        # 時刻順に並べ替え
        events = sorted(events, key=lambda x: x['time'])

        # 3. 潮位フェーズ判定
        phase_text = "不明"
        prev_ev = next((e for e in reversed(events) if e['time'] <= now), None)
        next_ev = next((e for e in events if e['time'] > now), None)

        if prev_ev and next_ev:
            duration = (next_ev['time'] - prev_ev['time']).total_seconds()
            elapsed = (now - prev_ev['time']).total_seconds()
            if duration > 0:
                p_type = "上げ" if prev_ev['type'] == "干潮" else "下げ"
                # 1〜9分で算出
                step = max(1, min(9, int((elapsed / duration) * 10)))
                phase_text = f"{p_type}{step}分"
                
                # 頂点付近(前後10%)の補正
                ratio = elapsed / duration
                if ratio < 0.1: phase_text = prev_ev['type']
                elif ratio > 0.9: phase_text = next_ev['type']

        return current_cm, phase_text

    except Exception:
        return default_res

def get_realtime_weather():
    """Open-Meteo Forecast API を使用して、現況と過去48h降水量を統合取得"""
    # 本渡(HS)の座標
    LAT, LON = 32.4333, 130.2167
    tide_level, phase = get_jma_tide_hs()
    
    # 基本データ（エラー時のバックアップ含む）
    data = {
        'tide_level': tide_level, 
        'phase': phase, 
        'temp': 15.0, 
        'wind': 3.0, 
        'wdir': "北", 
        'precip_48h': 0.0, 
        'tide': "中潮"
    }
    
    try:
        # forecast API を使用（現況 + 過去2日分）
        w_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": LAT,
            "longitude": LON,
            "current_weather": "true",
            "hourly": "precipitation",
            "past_days": 2,
            "timezone": "Asia/Tokyo"
        }
        res = requests.get(w_url, params=params, timeout=10).json()
        
        if 'current_weather' in res:
            cw = res['current_weather']
            data['temp'] = float(cw['temperature'])
            # km/h -> m/s 変換
            data['wind'] = round(float(cw['windspeed']) / 3.6, 1)
            
            # 16方位変換
            dirs = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
            data['wdir'] = dirs[int((cw['winddirection'] + 11.25) / 22.5) % 16]
            
            # 過去48時間の合計降水量
            if 'hourly' in res:
                # インデックス48が現在時刻の目安
                now_idx = 48 + datetime.now().hour
                precip_list = res['hourly']['precipitation']
                data['precip_48h'] = round(sum(precip_list[now_idx-48 : now_idx+1]), 1)
    except Exception:
        pass
        
    return data

def show_matching_page(df):
    """マッチング画面のUIとランキングロジック"""
    st.markdown("""
        <style>
        .stButton>button { background-color: #ff4b6c; color: white; border-radius: 25px; border: none; padding: 12px; font-weight: bold; width: 100%; }
        .input-card { background-color: #1e1e1e; padding: 20px; border-radius: 15px; border: 1px solid #333; margin-bottom: 20px; }
        .recommend-card { background: linear-gradient(135deg, #2c3e50 0%, #000000 100%); padding: 20px; border-radius: 15px; border-left: 5px solid #ff4b6c; margin-bottom: 15px; color: white; position: relative; }
        .score-badge { position: absolute; top: 20px; right: 20px; font-size: 1.8rem; font-weight: bold; color: #ff4b6c; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🏹 SeaBass Match AI v6.1")
    st.caption("JMA 水産潮位データ(HS) & Open-Meteo リアルタイム同期")

    # セッションに気象データを保持
    if 'm_data' not in st.session_state:
        st.session_state.m_data = get_realtime_weather()

    st.markdown("<div class='input-card'>", unsafe_allow_html=True)
    if st.button("🔄 HS(本渡)の最新海況を同期"):
        st.session_state.m_data = get_realtime_weather()
        st.rerun()

    md = st.session_state.m_data
    
    # ユーザー入力・確認エリア
    c1, c2 = st.columns(2)
    with c1:
        tide_name_in = st.selectbox("潮名", ["大潮", "中潮", "小潮", "長潮", "若潮"], index=1)
        level_in = st.number_input("潮位 (cm)", value=int(md.get('tide_level', 150)))
        temp_in = st.number_input("気温 (℃)", value=float(md.get('temp', 15.0)))
    with c2:
        p_list = ["上げ1分","上げ2分","上げ3分","上げ4分","上げ5分","上げ6分","上げ7分","上げ8分","上げ9分","満潮",
                  "下げ1分","下げ2分","下げ3分","下げ4分","下げ5分","下げ6分","下げ7分","下げ8分","下げ9分","干潮"]
        cur_p = md.get('phase', '上げ5分')
        p_idx = p_list.index(cur_p) if cur_p in p_list else 4
        phase_in = st.selectbox("潮位フェーズ", p_list, index=p_idx)
        
        wdir_list = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
        cur_wdir = md.get('wdir', '北')
        wdir_in = st.selectbox("風向", wdir_list, index=wdir_list.index(cur_wdir) if cur_wdir in wdir_list else 0)
        wind_in = st.number_input("風速 (m/s)", value=float(md.get('wind', 3.0)))
    
    precip_in = st.number_input("48h降水量合計 (mm)", value=float(md.get('precip_48h', 0.0)))
    st.markdown("</div>", unsafe_allow_html=True)

    # ランキング診断実行
    if st.button("🎯 過去実績からエリア診断開始"):
        if df is not None and not df.empty:
            # ボウズデータを除外して分析
            df['is_bouzu'] = df['魚種'].astype(str).str.contains('ボウズ', na=False)
            results = []
            
            for place in df['場所'].unique():
                p_df = df[df['場所'] == place]
                success_df = p_df[~p_df['is_bouzu']]
                
                if not success_df.empty:
                    # 【優先順位スコアリング】
                    # 1. 潮位フェーズ (35点)
                    s_phase = 35 if not success_df[success_df['潮位フェーズ'] == phase_in].empty else 0
                    # 2. 潮位 (25点) - 誤差±15cm以内
                    s_level = 25 if not success_df[abs(success_df.get('潮位_cm', 0) - level_in) <= 15].empty else 0
                    # 3. 風向き (15点)
                    s_wdir = 15 if not success_df[success_df['風向'] == wdir_in].empty else 0
                    # 4. 気温 (10点) - 誤差±3度以内
                    s_temp = 10 if not success_df[abs(success_df['気温'] - temp_in) <= 3].empty else 0
                    # 5. その他 (15点: 潮名5, 風速5, 降水5)
                    s_others = (5 if not success_df[success_df['潮名'] == tide_name_in].empty else 0) + \
                               (5 if not success_df[abs(success_df['風速'] - wind_in) <= 2].empty else 0) + \
                               (5 if '降水量' in success_df.columns and not success_df[abs(success_df['降水量'] - precip_in) <= 10].empty else 0)
                    
                    total_score = min(s_phase + s_level + s_wdir + s_temp + s_others, 99)
                    
                    # 推奨ルアー（その場所での最多ヒットルアー）
                    lure_mode = success_df['ルアー'].dropna().mode()
                    rec_lure = lure_mode[0] if not lure_mode.empty else "データ不足"
                    
                    results.append({
                        'place': place, 
                        'score': total_score, 
                        'hits': len(success_df), 
                        'lure': rec_lure
                    })
            
            # スコア順にソートして表示
            results = sorted(results, key=lambda x: x['score'], reverse=True)
            
            if results:
                for i, res in enumerate(results):
                    st.markdown(f"""
                        <div class='recommend-card'>
                            <div class='score-badge'>{res['score']}%</div>
