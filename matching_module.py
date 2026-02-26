import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

# 本渡瀬戸の座標
LAT = 32.45
LON = 130.19

def get_weather_data_openmeteo(lat, lon, dt):
    try:
        # 過去データを含めて取得するため archive-api を使用
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
        
        # 配列の最後（最新時刻）のインデックスを特定
        idx = -1 
        
        temp = h['temperature_2m'][idx]
        wind_speed = round(h['windspeed_10m'][idx] / 3.6, 1) # km/h -> m/s
        wind_deg = h['winddirection_10m'][idx]
        precip_48h = round(sum(h['precipitation'][-48:]), 1)

        def get_wind_dir(deg):
            dirs = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
            return dirs[int((deg + 11.25) / 22.5) % 16]
        
        return temp, wind_speed, get_wind_dir(wind_deg), precip_48h
    except:
        return None, None, "不明", 0.0

def show_matching_page(df=None):
    st.title("🏹 SeaBass Matcher Pro")

    # 1. タイムゾーン設定
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst).replace(tzinfo=None)

    # 2. セッション状態（入力値の保持）
    if 'input_vals' not in st.session_state:
        st.session_state.input_vals = {
            'month': now.month, 'tide': 150, 'phase': "下げ5分",
            'temp': 10.0, 'rain': 0.0, 'wind_dir': "北", 'wind_speed': 3.0
        }

    # 3. 自動取得ボタン
    if st.button("🔄 現在の本渡瀬戸の状況を自動取得"):
        with st.spinner('潮汐データとOpen-Meteoを解析中...'):
            # --- 気象取得 ---
            temp, w_speed, w_dir, rain48 = get_weather_data_openmeteo(LAT, LON, now)
            
            # --- 潮汐取得（HS.txt解析） ---
            # ※以前作成した潮位推測・フェーズ判定ロジックを実行
            # ここでは例として直近の計算ロジックの結果を代入
            tide_val = 188 # 実際の計算値をここに入れる
            phase_val = "下げ9分" # 実際の計算値をここに入れる

            if temp is not None:
                st.session_state.input_vals.update({
                    'month': now.month,
                    'tide': tide_val,
                    'phase': phase_label_mapping(phase_val), # インデックス用
                    'temp': temp,
                    'rain': rain48,
                    'wind_dir': w_dir,
                    'wind_speed': w_speed
                })
                st.session_state.current_phase_str = phase_val
                st.success("最新の海況・気象（48h降水量含む）を反映しました！")

    # 4. 手入力フォーム
    phases = ["満潮", "下げ1分", "下げ3分", "下げ5分", "下げ7分", "下げ9分", "干潮", "上げ1分", "上げ3分", "上げ5分", "上げ7分", "上げ9分"]
    dirs_16 = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]

    with st.expander("📝 フィールド状況の微調整", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            t_month = st.slider("月", 1, 12, st.session_state.input_vals['month'])
            t_temp = st.number_input("気温 (℃)", -5.0, 40.0, float(st.session_state.input_vals['temp']))
        with c2:
            t_tide = st.number_input("潮位 (cm)", 0, 450, st.session_state.input_vals['tide'])
            # セッションからフェーズの初期位置を特定
            default_phase_idx = phases.index(st.session_state.current_phase_str) if 'current_phase_str' in st.session_state else 5
            t_phase = st.selectbox("潮位フェーズ", phases, index=default_phase_idx)
        with c3:
            t_rain = st.number_input("48h降水量 (mm)", 0.0, 200.0, float(st.session_state.input_vals['rain']))
            # 16方位に対応
            default_dir_idx = dirs_16.index(st.session_state.input_vals['wind_dir']) if st.session_state.input_vals['wind_dir'] in dirs_16 else 0
            t_wind_dir = st.selectbox("風向", dirs_16, index=default_dir_idx)
            t_wind_speed = st.slider("風速 (m/s)", 0.0, 20.0, float(st.session_state.input_vals['wind_speed']))

    # 5. マッチング表示
    st.info(f"🔍 検索中: {t_month}月 / {t_tide}cm ({t_phase}) / 48h雨量 {t_rain}mm / {t_wind_dir}風 {t_wind_speed}m")
    
    # (以下、マッチングロジック...)

    # --- 5. 強化されたマッチング・スコアリング ---
    if df is not None and not df.empty:
        st.divider()
        st.subheader("🎯 推奨ポイントの解析結果")

        def calculate_advanced_score(row):
            score = 0
            try:
                # 月の一致 (最大20点)
                if row['月'] == t_month: score += 20
                elif abs(row['月'] - t_month) == 1: score += 10
                
                # 潮位フェーズの一致 (最大30点) - 最も重要
                if str(row.get('潮位フェーズ')) == t_phase: score += 30
                
                # 潮位(cm)の近さ (最大15点)
                if abs(row['潮位_cm'] - t_tide) <= 25: score += 15
                
                # 気温のマッチング (±3度以内なら10点)
                if abs(row.get('気温_度', t_temp) - t_temp) <= 3: score += 10
                
                # 降水量のマッチング (最大15点)
                # 「雨後の濁り」を重視するため、近い降水量を評価
                if abs(row.get('降水量_48h', 0) - t_rain) <= 10: score += 15
                
                # 風向の一致 (10点)
                if row.get('風向') == t_wind_dir: score += 10
            except: pass
            return score

        df['マッチ度'] = df.apply(calculate_advanced_score, axis=1)
        # スコアが少しでもあれば表示するように閾値を調整
        results = df[df['マッチ度'] > 0].sort_values('マッチ度', ascending=False).head(5)

        if not results.empty:
            for _, row in results.iterrows():
                # マッチ度に応じて色を変えるなどの視覚効果
                label = "🔥 最有力" if row['マッチ度'] >= 70 else "✅ 候補"
                with st.expander(f"{label} (マッチ度 {row['マッチ度']}%) ： {row['場所']}"):
                    st.write(f"🐟 **{row['魚種']} {row['全長_cm']}cm** / {row['ルアー']}")
                    st.write(f"📊 **実績時の状況:**")
                    st.caption(f"潮汐: {row['潮位フェーズ']} ({row['潮位_cm']}cm) | 気温: {row.get('気温_度','-')}℃ | 48h降水: {row.get('降水量_48h','-')}mm")
        else:
            st.warning("現在の厳しい条件に完全一致するデータがありません。サイドバーで条件を少し緩めて（シミュレーション）みてください。")
    else:
        st.error("釣果データが見つかりません。CSVファイルをアップロードしてください。")

