import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

# --- 定数定義 ---
LAT = 32.45
LON = 130.19
PHASES = ["満潮", "下げ1分", "下げ3分", "下げ5分", "下げ7分", "下げ9分", "干潮", "上げ1分", "上げ3分", "上げ5分", "上げ7分", "上げ9分"]
DIRS_16 = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]

def get_weather_data_openmeteo(lat, lon, dt):
    """Open-Meteo APIから気象データを取得"""
    try:
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": lat, "longitude": lon,
            "start_date": (dt - timedelta(days=2)).strftime('%Y-%m-%d'),
            "end_date": dt.strftime('%Y-%m-%d'),
            "hourly": "temperature_2m,windspeed_10m,winddirection_10m,precipitation",
            "timezone": "Asia/Tokyo"
        }
        res = requests.get(url, params=params, timeout=10).json()
        h = res['hourly']
        idx = -1  # 最新時刻
        temp = h['temperature_2m'][idx]
        wind_speed = round(h['windspeed_10m'][idx] / 3.6, 1) # km/h -> m/s
        wind_deg = h['winddirection_10m'][idx]
        precip_48h = round(sum(h['precipitation'][-48:]), 1)

        def get_wind_dir(deg):
            return DIRS_16[int((deg + 11.25) / 22.5) % 16]
        
        return temp, wind_speed, get_wind_dir(wind_deg), precip_48h
    except:
        return None, None, "不明", 0.0

def show_matching_page(df=None):
    st.title("🏹 SeaBass Matcher Pro")

    # 1. 日本時間の取得
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst).replace(tzinfo=None)

    # 2. セッション状態の初期化
    if 'input_vals' not in st.session_state:
        st.session_state.input_vals = {
            'month': now.month, 'tide': 150, 'phase': "下げ5分",
            'temp': 15.0, 'rain': 0.0, 'wind_dir': "北", 'wind_speed': 3.0
        }

    # 3. 自動取得ボタン
    if st.button("🔄 現在の本渡瀬戸の状況を自動取得"):
        with st.spinner('潮汐・気象データを精密解析中...'):
            # 気象データ取得
            temp, w_speed, w_dir, rain48 = get_weather_data_openmeteo(LAT, LON, now)
            
            tide_val = 150
            phase_val = "下げ5分"
            try:
                # 気象庁潮汐データ取得
                url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/HS.txt"
                res = requests.get(url, timeout=10)
                lines = res.text.splitlines()
                
                # 3日間のイベントを抽出
                events = []
                for d_off in [-1, 0, 1]:
                    t_d = now + timedelta(days=d_off)
                    d_str = t_d.strftime('%Y%m%d')
                    d_line = next((l for l in lines if len(l) > 100 and int(l[76:78]) == t_d.day and l[78:80].strip() == "HS"), None)
                    if d_line:
                        for start, e_type in [(80, "満潮"), (108, "干潮")]:
                            for i in range(4):
                                pos = start + (i * 7)
                                t_raw = d_line[pos : pos+4].strip()
                                v_raw = d_line[pos+4 : pos+7].strip()
                                if t_raw and t_raw != "9999" and t_raw.isdigit():
                                    events.append({
                                        "time": datetime.strptime(d_str + t_raw, '%Y%m%d%H%M'),
                                        "type": e_type, "value": int(v_raw)
                                    })
                
                events.sort(key=lambda x: x['time'])
                prev_e = next((e for e in reversed(events) if e['time'] <= now), None)
                next_e = next((e for e in events if e['time'] > now), None)

                if prev_e and next_e:
                    time_diff_total = (next_e['time'] - prev_e['time']).total_seconds()
                    time_diff_now = (now - prev_e['time']).total_seconds()
                    
                    # 潮位推定
                    tide_val = int(prev_e['value'] + (next_e['value'] - prev_e['value']) * (time_diff_now / time_diff_total))

                    # 時間10等分ロジック
                    ratio = time_diff_now / time_diff_total
                    direction = "下げ" if prev_e['type'] == "満潮" else "上げ"

                    if ratio < 0.05: phase_val = prev_e['type']
                    elif ratio > 0.95: phase_val = next_e['type']
                    elif ratio < 0.20: phase_val = f"{direction}1分"
                    elif ratio < 0.40: phase_val = f"{direction}3分"
                    elif ratio < 0.60: phase_val = f"{direction}5分"
                    elif ratio < 0.80: phase_val = f"{direction}7分"
                    else: phase_val = f"{direction}9分"
            except: pass

            st.session_state.input_vals.update({
                'month': now.month, 'tide': tide_val, 'phase': phase_val,
                'temp': temp if temp else 15.0, 'rain': rain48,
                'wind_dir': w_dir, 'wind_speed': w_speed if w_speed else 0.0
            })
            st.success(f"解析成功：現在は「{phase_val}」です")

    # 4. フィールド状況の調整フォーム
    with st.expander("📝 フィールド状況の微調整", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            t_month = st.slider("月", 1, 12, int(st.session_state.input_vals['month']))
            t_temp = st.number_input("気温 (℃)", -5.0, 40.0, float(st.session_state.input_vals['temp']))
        with c2:
            t_tide = st.number_input("潮位 (cm)", 0, 450, int(st.session_state.input_vals['tide']))
            cur_p = st.session_state.input_vals['phase']
            t_phase = st.selectbox("潮位フェーズ", PHASES, index=PHASES.index(cur_p) if cur_p in PHASES else 5)
        with c3:
            t_rain = st.number_input("48h降水量 (mm)", 0.0, 200.0, float(st.session_state.input_vals['rain']))
            cur_d = st.session_state.input_vals['wind_dir']
            t_wind_dir = st.selectbox("風向", DIRS_16, index=DIRS_16.index(cur_d) if cur_d in DIRS_16 else 0)
            t_wind_speed = st.slider("風速 (m/s)", 0.0, 20.0, float(st.session_state.input_vals['wind_speed']))

    # 5. マッチング・スコアリング
    st.divider()
    if df is not None and not df.empty:
        def calc_score(row):
            s = 0
            try:
                # 潮位フェーズ（最優先：50点）
                if str(row.get('潮位フェーズ', '')) == t_phase:
                    s += 50
                
                # 潮位(cm)の近さ（30点）
                tide_diff = abs(row.get('潮位_cm', 0) - t_tide)
                if tide_diff <= 20: s += 30
                elif tide_diff <= 40: s += 15
                
                # 月・シーズンのマッチング（10点）
                row_month = row['月'] if '月' in row else (pd.to_datetime(row['日付']).month if '日付' in row else None)
                if row_month == t_month: s += 10
                
                # 48h降水量のマッチング（10点）
                if abs(row.get('降水量_48h', 0) - t_rain) <= 10: s += 10
            except: pass
            return s

        df['マッチ度'] = df.apply(calc_score, axis=1)
        results = df[df['マッチ度'] > 0].sort_values('マッチ度', ascending=False).head(5)

        st.subheader("🎯 推奨ポイントランキング")
        if not results.empty:
            for _, row in results.iterrows():
                if row['マッチ度'] >= 80: label = "💎 最適時合"
                elif row['マッチ度'] >= 50: label = "✅ 期待大"
                else: label = "📝 参考実績"
                
                with st.expander(f"{label} ({row['マッチ度']}%) ： {row.get('場所', 'ポイント不明')}"):
                    ca, cb = st.columns(2)
                    with ca:
                        st.write(f"🐟 **{row.get('魚種','-')}** / {row.get('全長_cm','-')}cm")
                        st.write(f"🎣 {row.get('ルアー','-')}")
                    with cb:
                        st.write(f"🌊 {row.get('潮位フェーズ','-')} ({row.get('潮位_cm','-')}cm)")
                        st.write(f"☔ 雨量: {row.get('降水量_48h',0)}mm")
                    st.progress(row['マッチ度'] / 100)
        else:
            st.warning("現在の条件に合致する過去実績がありません。条件を調整してください。")
    else:
        st.error("釣果データ(CSV)が読み込めていません。")
