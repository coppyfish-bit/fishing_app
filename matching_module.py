import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import requests

def get_jma_tide_hs():
    """
    気象庁の 136カラム固定長データを精密に解析します。
    app.py で動作していたロジックをモジュール用に完全同期。
    """
    now = datetime.now()
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/HS.txt"
    
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        lines = res.text.splitlines()
        
        day_line = None
        # 今日の日付を文字列として作成（気象庁フォーマット準拠）
        target_y = now.strftime('%y')
        target_m = now.month
        target_d = now.day
        
        for line in lines:
            if len(line) < 80: continue
            # 73-75:年, 76-77:月, 78-79:日 を数値で比較（確実な判定）
            try:
                line_y = int(line[72:75].strip())
                line_m = int(line[75:77].strip())
                line_d = int(line[77:79].strip())
                
                if line_y == int(target_y) and line_m == target_m and line_d == target_d:
                    day_line = line
                    break
            except:
                continue
        
        if not day_line:
            return 150, "取得失敗"

        # 1. 毎時潮位の取得 (3文字ずつ24時間分)
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
        # 満潮(80-107カラム), 干潮(108-135カラム)
        for start_pos, e_type in [(80, "満潮"), (108, "干潮")]:
            for i in range(4):
                p = start_pos + (i * 7)
                t_str = day_line[p : p+4].strip()
                if t_str and t_str != "9999":
                    ev_t = datetime.strptime(today_str + t_str.zfill(4), '%Y%m%d%H%M')
                    events.append({"time": ev_t, "type": e_type})
        
        events = sorted(events, key=lambda x: x['time'])
        
        # 3. フェーズ判定
        phase = "判定不能"
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
    except:
        return 150, "通信エラー"

def get_realtime_weather():
    """気象と潮汐を統合取得"""
    t_level, t_phase = get_jma_tide_hs()
    LAT, LON = 32.4333, 130.2167 # 本渡(HS)
    
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
            w_data['wind'] = round(cw['windspeed'] / 3.6, 1) # m/s
            dirs = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
            w_data['wdir'] = dirs[int((cw['winddirection'] + 11.25) / 22.5) % 16]
            
            if 'hourly' in res:
                # 過去48時間の合計降水量
                now_h = datetime.now().hour + 48 # past_days=2なので48時間分オフセット
                precip = res['hourly']['precipitation']
                w_data['precip_48h'] = round(sum(precip[now_h-48 : now_h+1]), 1)
    except:
        pass
        
    return {**w_data, 'tide_level': t_level, 'phase': t_phase}

def show_matching_page(df):
    """メイン表示・診断UI"""
    st.markdown("""
        <style>
        .stButton>button { background-color: #ff4b6c; color: white; border-radius: 25px; border: none; padding: 12px; font-weight: bold; width: 100%; }
        .info-box { background-color: #1e1e1e; padding: 15px; border-radius: 10px; border: 1px solid #333; margin-bottom: 20px; }
        .recommend-card { background: linear-gradient(135deg, #2c3e50 0%, #000000 100%); padding: 20px; border-radius: 15px; border-left: 5px solid #ff4b6c; margin-bottom: 15px; color: white; position: relative; }
        .score-badge { position: absolute; top: 20px; right: 20px; font-size: 1.8rem; font-weight: bold; color: #ff4b6c; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🏹 SeaBass Match AI v6.5")

    # セッション状態の管理
    if 'm_data' not in st.session_state:
        st.session_state.m_data = get_realtime_weather()

    # データ更新ボタン
    if st.button("🔄 海況・潮汐データを同期"):
        st.session_state.m_data = get_realtime_weather()
        st.rerun()

    md = st.session_state.m_data

    # 現況表示パネル
    st.markdown(f"""
    <div class='info-box'>
        <b>現在の本渡瀬戸(HS)</b><br>
        🌊 潮汐：{md['phase']} ({md['tide_level']}cm)<br>
        🌡️ 気象：{md['temp']}℃ / {md['wind']}m ({md['wdir']}) / 48h降水 {md['precip_48h']}mm
    </div>
    """, unsafe_allow_html=True)

    # 入力フォーム
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
                    # スコア計算 (app.pyと同ロジック)
                    s_phase = 35 if not success_df[success_df['潮位フェーズ'] == phase_in].empty else 0
                    s_level = 25 if not success_df[abs(success_df.get('潮位_cm', 0) - level_in) <= 15].empty else 0
                    s_wdir = 15 if not success_df[success_df['風向'] == wdir_in].empty else 0
                    s_temp = 10 if not success_df[abs(success_df['気温'] - temp_in) <= 3].empty else 0
                    s_others = (5 if not success_df[success_df['潮名'] == tide_name_in].empty else 0) + \
                               (5 if not success_df[abs(success_df['風速'] - wind_in) <= 2].empty else 0) + \
                               (5 if '降水量' in success_df.columns and not success_df[abs(success_df['降水量'] - precip_in) <= 10].empty else 0)
                    
                    total = min(s_phase + s_level + s_wdir + s_temp + s_others, 99)
                    lure_mode = success_df['ルアー'].dropna().mode()
                    results.append({'place': place, 'score': total, 'hits': len(success_df), 'lure': lure_mode[0] if not lure_mode.empty else "不明"})
            
            results = sorted(results, key=lambda x: x['score'], reverse=True)
            for i, res in enumerate(results):
                st.markdown(f"""
                <div class='recommend-card'>
                    <div class='score-badge'>{res['score']}%</div>
                    <b>{i+1}位: {res['place']}</b><br>
                    実績: {res['hits']}件 / 推奨: {res['lure']}
                </div>
                """, unsafe_allow_html=True)
