import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

# --- 設定項目 ---
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
        idx = -1 
        temp = h['temperature_2m'][idx]
        wind_speed = round(h['windspeed_10m'][idx] / 3.6, 1)
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
            'temp': 10.0, 'rain': 0.0, 'wind_dir': "北", 'wind_speed': 3.0
        }

    # 3. 自動取得ボタン
    if st.button("🔄 現在の本渡瀬戸の状況を自動取得"):
        with st.spinner('潮汐・気象データを解析中...'):
            temp, w_speed, w_dir, rain48 = get_weather_data_openmeteo(LAT, LON, now)
            
            tide_val, phase_val = 150, "下げ5分"
            try:
                url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/HS.txt"
                res = requests.get(url, timeout=10)
                lines = res.text.splitlines()
                target_y, target_m, target_d = int(now.strftime('%y')), now.month, now.day
                day_line = next((l for l in lines if len(l) > 80 and int(l[72:74]) == target_y and int(l[74:76]) == target_m and int(l[76:78]) == target_d and l[78:80].strip() == "HS"), None)
                if day_line:
                    hourly = [int(day_line[i*3 : (i+1)*3].strip() or 0) for i in range(24)]
                    tide_val = int(hourly[now.hour] + (hourly[now.hour+1 if now.hour<23 else now.hour] - hourly[now.hour]) * (now.minute / 60.0))
                    # 簡易的なフェーズ判定ロジック
                    prev_v = hourly[now.hour-1 if now.hour>0 else 0]
                    phase_val = "下げ" if tide_val < prev_v else "上げ"
                    # ※詳細なフェーズ判定は以前のロジックをここに統合可能
            except: pass

            st.session_state.input_vals.update({
                'month': now.month, 'tide': tide_val, 'phase': phase_val if "分" in phase_val else "下げ5分",
                'temp': temp if temp else 10.0, 'rain': rain48,
                'wind_dir': w_dir, 'wind_speed': w_speed if w_speed else 0.0
            })
            st.success("最新情報を反映しました！")

    # 4. 手入力・微調整フォーム
    with st.expander("📝 フィールド状況の微調整", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            t_month = st.slider("月", 1, 12, st.session_state.input_vals['month'])
            t_temp = st.number_input("気温 (℃)", -5.0, 40.0, float(st.session_state.input_vals['temp']))
        with c2:
            t_tide = st.number_input("潮位 (cm)", 0, 450, st.session_state.input_vals['tide'])
            cur_p = st.session_state.input_vals['phase']
            t_phase = st.selectbox("潮位フェーズ", PHASES, index=PHASES.index(cur_p) if cur_p in PHASES else 5)
        with c3:
            t_rain = st.number_input("48h降水量 (mm)", 0.0, 200.0, float(st.session_state.input_vals['rain']))
            cur_d = st.session_state.input_vals['wind_dir']
            t_wind_dir = st.selectbox("風向", DIRS_16, index=DIRS_16.index(cur_d) if cur_d in DIRS_16 else 14)
            t_wind_speed = st.slider("風速 (m/s)", 0.0, 20.0, float(st.session_state.input_vals['wind_speed']))

# --- 5. マッチング・スコアリング（潮汐重視設定） ---
    if df is not None and not df.empty:
        def calc_score(row):
            s = 0
            try:
                # 1. 潮位フェーズ（最優先：50点）
                # 例：「下げ5分」が一致すれば即座に高得点
                if str(row.get('潮位フェーズ', '')) == t_phase:
                    s += 50
                
                # 2. 潮位(cm)の近さ（重要：30点）
                # ±20cm以内なら満点、±40cm以内なら15点
                tide_diff = abs(row.get('潮位_cm', 0) - t_tide)
                if tide_diff <= 20:
                    s += 30
                elif tide_diff <= 40:
                    s += 15
                
                # 3. 月・シーズンのマッチング（10点）
                row_month = None
                if '月' in row: row_month = row['月']
                elif '日付' in row: row_month = pd.to_datetime(row['日付']).month
                
                if row_month == t_month:
                    s += 10
                
                # 4. 48h降水量のマッチング（10点）
                # 雨後の濁りパターンの再現用
                if abs(row.get('降水量_48h', 0) - t_rain) <= 10:
                    s += 10
                    
            except:
                pass
            return s

        # スコア計算実行
        df['マッチ度'] = df.apply(calc_score, axis=1)
        
        # スコアが高い順に上位5件を表示
        results = df[df['マッチ度'] > 0].sort_values('マッチ度', ascending=False).head(5)

        st.subheader("🎯 潮汐条件に基づく推奨ポイント")
        if not results.empty:
            for _, row in results.iterrows():
                # スコアに応じたバッジ表示
                if row['マッチ度'] >= 80:
                    label = "💎 最適時合"
                elif row['マッチ度'] >= 50:
                    label = "✅ 期待大"
                else:
                    label = "📝 参考実績"
                
                with st.expander(f"{label} (マッチ度: {row['マッチ度']}%) ： {row.get('場所', '不明')}"):
                    c_a, c_b = st.columns(2)
                    with c_a:
                        st.write(f"🐟 **{row.get('魚種','-')}**")
                        st.write(f"📏 **{row.get('全長_cm','-')} cm**")
                    with c_b:
                        st.write(f"🌊 {row.get('潮位フェーズ','-')}")
                        st.write(f"📏 {row.get('潮位_cm','-')} cm")
                    st.progress(row['マッチ度'] / 100)
        else:
            st.warning("現在の潮汐条件に合致する過去実績がありません。")
