import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

# --- データ取得関数 ---

def get_jma_tide_hs():
    """気象庁HPから本渡の正確な潮汐データを取得し、10段階フェーズを算出"""
    now = datetime.now()
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/HS.txt"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200: return 150, "取得失敗", False
        
        lines = res.text.splitlines()
        target_y, target_m, target_d = int(now.strftime('%y')), now.month, now.day
        day_line = next((l for l in lines if len(l) > 100 and int(l[72:74]) == target_y and int(l[74:76]) == target_m and int(l[76:78]) == target_d), None)
        
        if not day_line: return 150, "取得失敗(日付なし)", False

        # 現在潮位の計算
        hourly = [int(day_line[i*3 : (i+1)*3].strip() or 0) for i in range(24)]
        h, m = now.hour, now.minute
        t1, t2 = hourly[h], hourly[h+1] if h < 23 else hourly[h]
        current_cm = int(t1 + (t2 - t1) * (m / 60.0))

        # --- 10段階フェーズ判定ロジック ---
        events = []
        today_str = now.strftime('%Y%m%d')
        for start, e_type in [(80, "満潮"), (108, "干潮")]:
            for i in range(4):
                pos = start + (i * 7)
                t_str = day_line[pos : pos+4].strip()
                if t_str and t_str != "9999":
                    ev_time = datetime.strptime(today_str + t_str.zfill(4), '%Y%m%d%H%M')
                    events.append({"time": ev_time, "type": e_type})
        
        events.sort(key=lambda x: x['time'])

        prev_e = next((e for e in reversed(events) if e['time'] <= now), None)
        next_e = next((e for e in events if e['time'] > now), None)
        
        if prev_e and next_e:
            duration = (next_e['time'] - prev_e['time']).total_seconds()
            elapsed = (now - prev_e['time']).total_seconds()
            progress = max(1, min(9, int((elapsed / duration) * 10)))
            label = "下げ" if prev_e['type'] == "満潮" else "上げ"
            
            if elapsed / duration < 0.1: phase_text = prev_e['type']
            elif elapsed / duration > 0.9: phase_text = next_e['type']
            else: phase_text = f"{label}{progress}分"
        else:
            phase_text = "下げ5分" # 判定不能時のデフォルト

        return current_cm, phase_text, True
    except:
        return 150, "エラー", False

def get_weather():
    """天草の現在気象を取得（気温・風・48時間降水量）"""
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=2)
        res = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": 32.4333, "longitude": 130.2167, "current_weather": "true",
            "hourly": "precipitation", "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d'), "timezone": "Asia/Tokyo"
        }, timeout=5).json()
        
        cw = res['current_weather']
        precip_48h = sum(res['hourly']['precipitation'][-48:]) if 'hourly' in res else 0.0
        dirs = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
        wdir_text = dirs[int((cw['winddirection'] + 22.5) / 45) % 8]
        return cw['temperature'], round(cw['windspeed']/3.6, 1), wdir_text, round(precip_48h, 1)
    except:
        return 20.0, 2.0, "北", 0.0

# --- メイン表示関数 ---

def show_matching_page(df):
    st.title("🏹 SeaBass Matcher Pro")
    
    # セッション状態の初期化
    if 'tide' not in st.session_state: st.session_state.tide = 150
    if 'phase' not in st.session_state: st.session_state.phase = "下げ5分"
    if 'temp' not in st.session_state: st.session_state.temp = 20.0
    if 'wind' not in st.session_state: st.session_state.wind = 2.0
    if 'wdir' not in st.session_state: st.session_state.wdir = "北"
    if 'precip_48h' not in st.session_state: st.session_state.precip_48h = 0.0
    if 'month' not in st.session_state: st.session_state.month = datetime.now().month
    if 'tide_success' not in st.session_state: st.session_state.tide_success = None

    # --- 1. 入力セクション ---
    with st.expander("🌍 海況・気象データの設定", expanded=True):
        if st.button("🔄 リアルタイム情報を取得(本渡瀬戸)"):
            # 【修正点】戻り値3つを正しく受け取る
            t_cm, t_ph, success = get_jma_tide_hs()
            temp_v, wind_v, wdir_v, p48_v = get_weather()
            
            st.session_state.tide = t_cm
            st.session_state.phase = t_ph
            st.session_state.temp = temp_v
            st.session_state.wind = wind_v
            st.session_state.wdir = wdir_v
            st.session_state.precip_48h = p48_v
            st.session_state.month = datetime.now().month
            st.session_state.tide_success = success
            st.rerun()

        if st.session_state.tide_success is True:
            st.success(f"✅ 本渡瀬戸のデータを取得しました ({datetime.now().strftime('%H:%M')})")
        elif st.session_state.tide_success is False:
            st.error("❌ 潮位データの取得に失敗しました。手動で調整してください。")

        c1, c2, c3 = st.columns(3)
        month_in = c1.selectbox("月", list(range(1, 13)), index=st.session_state.month - 1)
        tide_in = c2.number_input("潮位(cm)", 0, 400, value=st.session_state.tide)
        
        # 10段階フェーズの選択肢
        p_options = ["満潮"] + [f"下げ{i}分" for i in range(1,10)] + ["干潮"] + [f"上げ{i}分" for i in range(1,10)]
        curr_p = st.session_state.phase if st.session_state.phase in p_options else "下げ5分"
        phase_in = c3.selectbox("潮位フェーズ", p_options, index=p_options.index(curr_p))
        
        c4, c5, c6, c7 = st.columns(4)
        temp_in = c4.number_input("気温(℃)", -10.0, 45.0, value=st.session_state.temp)
        precip_in = c5.number_input("48h降水量(mm)", 0.0, 300.0, value=st.session_state.precip_48h)
        wind_in = c6.number_input("風速(m)", 0.0, 20.0, value=st.session_state.wind)
        w_options = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
        curr_w = st.session_state.wdir if st.session_state.wdir in w_options else "北"
        wdir_in = c7.selectbox("風向", w_options, index=w_options.index(curr_w))

    # --- 2. マッチングロジック ---
    st.divider()
    
    def calculate_score(row):
        score = 0
        try:
            if pd.to_datetime(row['date']).month == month_in: score += 30
            if abs(row['潮位_cm'] - tide_in) <= 20: score += 20
            if str(row.get('潮位フェーズ')) == phase_in: score += 15
            if str(row.get('風向')) == wdir_in: score += 15
            if abs(row['気温'] - temp_in) <= 3: score += 10
            if abs(row['降水量'] - precip_in) <= 5: score += 10
        except: pass
        return score

    if not df.empty:
        df['マッチ度'] = df.apply(calculate_score, axis=1)
        ranking = df.sort_values('マッチ度', ascending=False).drop_duplicates(subset=['場所']).head(5)
        st.subheader("📍 おすすめポイント（過去実績より）")
        for i, row in ranking.iterrows():
            with st.container():
                cols = st.columns([1, 4])
                cols[0].metric("マッチ度", f"{row['マッチ度']}%")
                with cols[1]:
                    st.markdown(f"### {row['場所']}")
                    st.write(f"📏 **実績:** {row['魚種']} {row['全長_cm']}cm | 🎣 **ルアー:** {row['ルアー']}")
                    st.caption(f"🌡️ {row['気温']}℃ | ☔ 48h降水: {row['降水量']}mm | 💨 {row.get('風向')} {row.get('風速')}m")
                st.divider()
    else:
        st.warning("データが読み込まれていません。")
