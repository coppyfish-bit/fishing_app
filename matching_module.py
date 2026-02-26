import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

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

        # 直前と次のイベントを特定
        prev_e = next((e for e in reversed(events) if e['time'] <= now), None)
        next_e = next((e for e in events if e['time'] > now), None)
        
        if prev_e and next_e:
            duration = (next_e['time'] - prev_e['time']).total_seconds()
            elapsed = (now - prev_e['time']).total_seconds()
            # 0.0〜1.0の進捗を10段階に変換
            progress = max(1, min(9, int((elapsed / duration) * 10)))
            
            label = "下げ" if prev_e['type'] == "満潮" else "上げ"
            # 潮止まり付近の処理
            if elapsed / duration < 0.1: phase_text = prev_e['type']
            elif elapsed / duration > 0.9: phase_text = next_e['type']
            else: phase_text = f"{label}{progress}分"
        else:
            phase_text = "判定不能"

        return current_cm, phase_text, True
    except Exception as e:
        return 150, f"エラー: {str(e)}", False

# ... get_weather 関数は前回と同じ ...

def show_matching_page(df):
    st.title("🏹 SeaBass Matcher Pro")
    
    # セッション状態の初期設定
    if 'tide_success' not in st.session_state: st.session_state.tide_success = None

    # --- 1. 入力セクション ---
    with st.expander("🌍 海況・気象データの設定", expanded=True):
        if st.button("🔄 リアルタイム情報を取得(本渡瀬戸)"):
            t_cm, t_ph, success = get_jma_tide_hs()
            temp_val, wind_spd, wdir_val, p48_val = get_weather()
            
            st.session_state.tide = t_cm
            st.session_state.phase = t_ph
            st.session_state.tide_success = success # 成功フラグを保存
            # ... 他のsession_state保存 ...
            st.rerun()

        # 取得ステータスの表示
        if st.session_state.tide_success is True:
            st.success(f"✅ 本渡瀬戸のデータを取得しました（取得時刻: {datetime.now().strftime('%H:%M')}）")
        elif st.session_state.tide_success is False:
            st.error("❌ 潮位データの取得に失敗しました。手動で入力してください。")

        # 入力フォーム（フェーズの選択肢を動的に生成）
        c1, c2, c3 = st.columns(3)
        month = c1.selectbox("月", list(range(1, 13)), index=st.session_state.get('month', 1)-1)
        tide_input = c2.number_input("潮位(cm)", 0, 400, value=st.session_state.get('tide', 150))
        
        # 選択肢を「下げ1分〜9分」「上げ1分〜9分」「満潮」「干潮」に広げる
        phase_options = ["満潮"] + [f"下げ{i}分" for i in range(1,10)] + ["干潮"] + [f"上げ{i}分" for i in range(1,10)]
        curr_p = st.session_state.get('phase', "下げ5分")
        # リストにない場合（エラー時など）の安全策
        if curr_p not in phase_options: phase_options.append(curr_p)
        phase_input = c3.selectbox("潮位フェーズ", phase_options, index=phase_options.index(curr_p))

        # ... (以下、気温・風向などの入力とマッチングロジックは前回と同様) ...
def get_weather():
    """天草の現在気象を取得（気温・風・48時間降水量）"""
    try:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=2)
        
        res = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": 32.4333, "longitude": 130.2167, 
            "current_weather": "true",
            "hourly": "precipitation",
            "start_date": start_date.strftime('%Y-%m-%d'),
            "end_date": end_date.strftime('%Y-%m-%d'),
            "timezone": "Asia/Tokyo"
        }, timeout=5).json()
        
        cw = res['current_weather']
        precip_48h = 0.0
        if 'hourly' in res and 'precipitation' in res['hourly']:
            precip_list = res['hourly']['precipitation']
            precip_48h = sum(precip_list[-48:])
        
        dirs = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
        wdir_text = dirs[int((cw['winddirection'] + 22.5) / 45) % 8]
        
        return cw['temperature'], round(cw['windspeed']/3.6, 1), wdir_text, round(precip_48h, 1)
    except:
        return 20.0, 2.0, "北", 0.0

# --- メイン表示関数 ---

def show_matching_page(df):
    st.title("🏹 SeaBass Matcher Pro")
    st.caption("天草・本渡瀬戸の海況に基づいたポイントマッチング")

    # セッション状態の初期化
    if 'tide' not in st.session_state: st.session_state.tide = 150
    if 'phase' not in st.session_state: st.session_state.phase = "下げ"
    if 'wind' not in st.session_state: st.session_state.wind = 2.0
    if 'wdir' not in st.session_state: st.session_state.wdir = "北"
    if 'temp' not in st.session_state: st.session_state.temp = 20.0
    if 'precip_48h' not in st.session_state: st.session_state.precip_48h = 0.0
    if 'month' not in st.session_state: st.session_state.month = datetime.now().month

    # --- 1. 入力セクション ---
    with st.expander("🌍 海況・気象データの設定", expanded=True):
        if st.button("🔄 リアルタイム情報を取得(本渡瀬戸)"):
            t_cm, t_ph = get_jma_tide_hs()
            temp_val, wind_spd, wdir_val, p48_val = get_weather()
            st.session_state.tide = t_cm
            st.session_state.phase = t_ph
            st.session_state.temp = temp_val
            st.session_state.wind = wind_spd
            st.session_state.wdir = wdir_val
            st.session_state.precip_48h = p48_val
            st.session_state.month = datetime.now().month
            st.success("本渡瀬戸の最新潮汐・気象データを同期しました。")
            st.rerun()

        c1, c2, c3 = st.columns(3)
        month = c1.selectbox("月", list(range(1, 13)), index=st.session_state.month - 1)
        tide_input = c2.number_input("潮位(cm)", 0, 400, value=st.session_state.tide)
        phase_options = ["上げ", "下げ", "満潮", "干潮"]
        default_p = st.session_state.phase if st.session_state.phase in phase_options else "下げ"
        phase_input = c3.selectbox("潮位フェーズ", phase_options, index=phase_options.index(default_p))
        
        c4, c5, c6, c7 = st.columns(4)
        temp_input = c4.number_input("気温(℃)", -10.0, 45.0, value=st.session_state.temp)
        precip_input = c5.number_input("48h降水量(mm)", 0.0, 300.0, value=st.session_state.precip_48h)
        wind_input = c6.number_input("風速(m)", 0.0, 20.0, value=st.session_state.wind)
        wdir_options = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
        default_w = st.session_state.wdir if st.session_state.wdir in wdir_options else "北"
        wdir_input = c7.selectbox("風向", wdir_options, index=wdir_options.index(default_w))

    # --- 2. マッチングロジック ---
    st.divider()
    
    def calculate_score(row):
        score = 0
        try:
            # 月 (30点)
            if pd.to_datetime(row['date']).month == month: score += 30
            # 潮位 ±20cm (20点)
            if abs(row['潮位_cm'] - tide_input) <= 20: score += 20
            # フェーズ (15点)
            if str(row.get('潮位フェーズ')) == phase_input: score += 15
            # 風向 (15点)
            if str(row.get('風向')) == wdir_input: score += 15
            # 気温 ±3度 (10点)
            if abs(row['気温'] - temp_input) <= 3: score += 10
            # 48h降水量 ±5mm (10点)
            if abs(row['降水量'] - precip_input) <= 5: score += 10
        except: pass
        return score

    if not df.empty:
        df['マッチ度'] = df.apply(calculate_score, axis=1)
        ranking = df.sort_values('マッチ度', ascending=False).drop_duplicates(subset=['場所']).head(5)

        st.subheader("📍 おすすめポイント（過去の実績から分析）")
        
        for i, row in ranking.iterrows():
            with st.container():
                cols = st.columns([1, 4])
                cols[0].metric("マッチ度", f"{row['マッチ度']}%")
                with cols[1]:
                    st.markdown(f"### {row['場所']}")
                    st.write(f"📏 **過去の釣果:** {row['魚種']} {row['全長_cm']}cm")
                    st.caption(f"🌡️ {row['気温']}℃ | ☔ 48h降水: {row['降水量']}mm | 💨 {row.get('風向')} {row.get('風速')}m")
                    st.write(f"🎣 **使用ルアー:** {row['ルアー']}")
                st.divider()
    else:
        st.warning("データ(df)が空です。Excelファイルが正しく読み込まれているか確認してください。")

