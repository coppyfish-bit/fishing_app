import streamlit as st
import pandas as pd
import requests
from datetime import datetime

def get_jma_tide_hs():
    """気象庁HPから本渡の現在の潮位を取得"""
    now = datetime.now()
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/HS.txt"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200: return 150
        lines = res.text.splitlines()
        target_y, target_m, target_d = int(now.strftime('%y')), now.month, now.day
        for line in lines:
            if len(line) < 100: continue
            if int(line[72:74]) == target_y and int(line[74:76]) == target_m and int(line[76:78]) == target_d:
                hourly = [int(line[i*3 : (i+1)*3].strip() or 0) for i in range(24)]
                h, m = now.hour, now.minute
                t1, t2 = hourly[h], hourly[h+1] if h < 23 else hourly[h]
                return int(t1 + (t2 - t1) * (m / 60.0))
    except: pass
    return 150 # 取得失敗時のデフォルト

def get_weather():
    """Open-Meteoから天草の現在気象を取得"""
    try:
        res = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": 32.4333, "longitude": 130.2167, "current_weather": "true"
        }, timeout=5).json()
        cw = res['current_weather']
        return cw['temperature'], round(cw['windspeed']/3.6, 1), cw['winddirection']
    except:
        return 20.0, 2.0, 0 # デフォルト値

def show_matching_page(df):
    st.title("🏹 SeaBass Matcher Pro")
    st.caption("月・潮位・風向から最適なエリアを導き出します")

    # --- 1. 入力セクション ---
    with st.expander("🌍 海況データの設定", expanded=True):
        col_auto, col_manual = st.columns([1, 2])
        
        # 自動取得ボタン
        if col_auto.button("🔄 リアルタイム情報を取得"):
            tide_val = get_jma_tide_hs()
            temp_val, wind_val, deg_val = get_weather()
            st.session_state.tide = tide_val
            st.session_state.wind = wind_val
            st.session_state.month = datetime.now().month
            # 風向き角度を文字に変換
            dirs = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
            st.session_state.wdir = dirs[int((deg_val + 22.5) / 45) % 8]
            st.success("最新のデータを読み込みました！")

        # 手入力フォーム
        c1, c2, c3, c4 = st.columns(4)
        month = c1.selectbox("月", list(range(1, 13)), index=st.session_state.get('month', datetime.now().month-1))
        tide = c2.number_input("潮位(cm)", 0, 400, value=st.session_state.get('tide', 150))
        wind = c3.number_input("風速(m)", 0.0, 20.0, value=st.session_state.get('wind', 2.0))
        wdir = c4.selectbox("風向", ["北", "北東", "東", "南東", "南", "南西", "西", "北西"], 
                            index=["北", "北東", "東", "南東", "南", "南西", "西", "北西"].index(st.session_state.get('wdir', "北")))

    # --- 2. マッチングロジック ---
    st.divider()
    st.subheader(f"📍 {month}月・潮位{tide}cm・{wdir}の風 での最適エリア")

    # スコアリングロジック（簡易版：ここをExcelの条件に合わせる）
    def calculate_score(row):
        score = 0
        # 月（シーズン）の考慮
        if str(month) in str(row.get('推奨月', '')): score += 30
        
        # 潮位の考慮
        min_t = row.get('最低潮位', 0)
        max_t = row.get('最高潮位', 400)
        if min_t <= tide <= max_t: score += 40
        
        # 風向の考慮（向かい風や背負える風など、場所ごとの特性を想定）
        if wdir in str(row.get('得意風向', '')): score += 30
        
        return score

    if not df.empty:
        df['マッチ度'] = df.apply(calculate_score, axis=1)
        ranking = df.sort_values('マッチ度', ascending=False).head(5)

        # 結果表示
        for i, row in ranking.iterrows():
            with st.container():
                cols = st.columns([1, 4])
                cols[0].metric("マッチ度", f"{row['マッチ度']}%")
                with cols[1]:
                    st.markdown(f"### {row['エリア名']}")
                    st.write(f"**特徴:** {row.get('特徴', '情報なし')} | **推奨ルアー:** {row.get('ルアー', '情報なし')}")
                st.divider()
    else:
        st.warning("ポイントデータ(Excel)を読み込んでください。")
