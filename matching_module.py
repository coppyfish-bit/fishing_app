import streamlit as st
import requests
import pandas as pd
from datetime import datetime

def get_jma_tide_hs():
    """本渡(HS)のリアルタイム潮位とフェーズを取得"""
    now = datetime.now()
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/HS.txt"
    
    # 失敗時のバックアップ
    fail_res = (150, "下げ5分")
    
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200: return fail_res
        
        lines = res.text.splitlines()
        target_y, target_m, target_d = int(now.strftime('%y')), now.month, now.day
        
        day_line = None
        for line in lines:
            if len(line) < 130: continue
            try:
                if int(line[72:74].strip()) == target_y and \
                   int(line[74:76].strip()) == target_m and \
                   int(line[76:78].strip()) == target_d and \
                   line[78:80].strip() == "HS":
                    day_line = line
                    break
            except: continue

        if not day_line: return fail_res

        # 1. 毎時潮位の取得
        hourly = [int(day_line[i*3 : (i+1)*3].strip() or 0) for i in range(24)]
        h, m = now.hour, now.minute
        t1 = hourly[h]
        t2 = hourly[h+1] if h < 23 else hourly[h]
        current_cm = int(t1 + (t2 - t1) * (m / 60.0))

        # 2. 満干潮時刻の抽出
        events = []
        today_str = now.strftime('%Y%m%d')
        for start, e_type in [(80, "満潮"), (108, "干潮")]:
            for i in range(4):
                pos = start + (i * 7)
                t_str = day_line[pos : pos+4].replace(" ", "0")
                if t_str and t_str != "9999" and t_str != "0000":
                    try:
                        ev_t = datetime.strptime(today_str + t_str.zfill(4), '%Y%m%d%H%M')
                        events.append({"time": ev_t, "type": e_type})
                    except: continue
        
        events.sort(key=lambda x: x['time'])

        # 3. フェーズ判定
        phase = "判定中"
        prev = next((e for e in reversed(events) if e['time'] <= now), None)
        nxt = next((e for e in events if e['time'] > now), None)

        if prev and nxt:
            dur = (nxt['time'] - prev['time']).total_seconds()
            ela = (now - prev['time']).total_seconds()
            if dur > 0:
                p_label = "上げ" if prev['type'] == "干潮" else "下げ"
                step = max(1, min(9, int((ela / dur) * 10)))
                phase = f"{p_label}{step}分"
                # 潮止まり前後の丸め
                if (ela/dur) < 0.1: phase = prev['type']
                elif (ela/dur) > 0.9: phase = nxt['type']

        return current_cm, phase
    except:
        return fail_res

def get_realtime_weather():
    """潮汐と気象（Open-Meteo）を統合"""
    cm, phase = get_jma_tide_hs()
    LAT, LON = 32.4333, 130.2167 # 天草本渡
    
    data = {'tide_level': cm, 'phase': phase, 'temp': 15.0, 'wind': 3.0, 'wdir': "北", 'precip_48h': 0.0}
    try:
        w_res = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": LAT, "longitude": LON, "current_weather": "true",
            "hourly": "precipitation", "past_days": 2, "timezone": "Asia/Tokyo"
        }, timeout=10).json()
        
        if 'current_weather' in w_res:
            cw = w_res['current_weather']
            data['temp'] = cw['temperature']
            data['wind'] = round(cw['windspeed'] / 3.6, 1)
            dirs = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
            data['wdir'] = dirs[int((cw['winddirection'] + 11.25) / 22.5) % 16]
            if 'hourly' in w_res:
                now_h = datetime.now().hour + 48
                data['precip_48h'] = round(sum(w_res['hourly']['precipitation'][now_h-48 : now_h+1]), 1)
    except: pass
    return data

def show_matching_page(df):
    """マッチング診断UI"""
    st.title("🏹 SeaBass Match AI v7.5")

    # 初回または更新ボタンでデータ取得
    if 'm_data' not in st.session_state or st.button("🔄 最新の海況を同期"):
        with st.spinner("潮汐・気象データを取得中..."):
            st.session_state.m_data = get_realtime_weather()
        st.rerun()

    md = st.session_state.m_data
    
    # リアルタイム現況表示
    st.success(f"🌊 現在の状況: 【{md['phase']}】 潮位 {md['tide_level']}cm / 風 {md['wind']}m ({md['wdir']})")

    # 診断条件入力フォーム
    with st.form("match_form"):
        st.markdown("### 🎯 診断条件の確認")
        c1, c2 = st.columns(2)
        with c1:
            level_in = st.number_input("潮位(cm)", value=int(md['tide_level']))
            temp_in = st.number_input("気温(℃)", value=float(md['temp']))
            tide_name_in = st.selectbox("潮名", ["大潮", "中潮", "小潮", "長潮", "若潮"], index=1)
        with c2:
            p_list = ["上げ1分","上げ2分","上げ3分","上げ4分","上げ5分","上げ6分","上げ7分","上げ8分","上げ9分","満潮",
                      "下げ1分","下げ2分","下げ3分","下げ4分","下げ5分","下げ6分","下げ7分","下げ8分","下げ9分","干潮"]
            cur_p = md['phase'] if md['phase'] in p_list else "下げ5分"
            phase_in = st.selectbox("潮位フェーズ", p_list, index=p_list.index(cur_p))
            wdir_list = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
            wdir_in = st.selectbox("現在の風向", wdir_list, index=wdir_list.index(md['wdir']) if md['wdir'] in wdir_list else 0)
            wind_in = st.number_input("現在の風速(m)", value=float(md['wind']))
        
        submitted = st.form_submit_button("エリア診断ランキングを表示")

    if submitted:
        if df is not None and not df.empty:
            # --- マッチング計算ロジック ---
            df_hit = df[df['魚種'].astype(str).str.contains('シーバス|スズキ|ヒラスズキ', na=False)].copy()
            results = []
            
            for place in df_hit['場所'].unique():
                p_df = df_hit[df_hit['場所'] == place]
                # スコア加点方式
                score = 0
                if not p_df[p_df['潮位フェーズ'] == phase_in].empty: score += 40
                if not p_df[abs(p_df['潮位_cm'] - level_in) < 20].empty: score += 30
                if not p_df[p_df['風向'] == wdir_in].empty: score += 20
                if not p_df[abs(p_df['気温'] - temp_in) < 3].empty: score += 10
                
                score = min(score, 98) # 最大98%
                lure = p_df['ルアー'].mode().iloc[0] if not p_df['ルアー'].mode().empty else "実績データ不足"
                
                results.append({'place': place, 'score': score, 'lure': lure, 'count': len(p_df)})
            
            # スコア順に表示
            results = sorted(results, key=lambda x: x['score'], reverse=True)
            for res in results:
                st.markdown(f"""
                <div style="padding:15px; border-radius:10px; border-left:5px solid #ff4b4b; background-color:#1e1e1e; margin-bottom:10px;">
                    <span style="font-size:1.2rem; font-weight:bold;">{res['place']}</span> 
                    <span style="color:#ff4b4b; margin-left:15px;">期待度: {res['score']}%</span><br>
                    <small>推奨ルアー: {res['lure']} / 過去実績: {res['count']}件</small>
                </div>
                """, unsafe_allow_html=True)
