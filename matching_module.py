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
        if res.status_code != 200: return 150, "下げ5分"
        lines = res.text.splitlines()
        target_y, target_m, target_d = int(now.strftime('%y')), now.month, now.day
        for line in lines:
            if len(line) < 100: continue
            if int(line[72:74]) == target_y and int(line[74:76]) == target_m and int(line[76:78]) == target_d:
                # 潮位計算
                hourly = [int(line[i*3 : (i+1)*3].strip() or 0) for i in range(24)]
                h, m = now.hour, now.minute
                t1, t2 = hourly[h], hourly[h+1] if h < 23 else hourly[h]
                current_cm = int(t1 + (t2 - t1) * (m / 60.0))
                
                # 簡易フェーズ判定（本来は満干潮時刻から計算しますが、一旦「下げ/上げ」のみ）
                phase = "上げ" if t2 >= t1 else "下げ"
                return current_cm, phase
    except: pass
    return 150, "下げ5分"

def get_weather():
    """天草の現在気象を取得"""
    try:
        res = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": 32.4333, "longitude": 130.2167, "current_weather": "true"
        }, timeout=5).json()
        cw = res['current_weather']
        dirs = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
        wdir_text = dirs[int((cw['winddirection'] + 22.5) / 45) % 8]
        return cw['temperature'], round(cw['windspeed']/3.6, 1), wdir_text
    except:
        return 20.0, 2.0, "北"

def show_matching_page(df):
    st.title("🏹 SeaBass Matcher Pro")
    st.caption("最新のカラム構成に基づいた高精度マッチング")

    # --- 1. 入力セクション ---
    with st.expander("🌍 海況データの設定", expanded=True):
        if st.button("🔄 リアルタイム情報を取得"):
            t_cm, t_ph = get_jma_tide_hs()
            temp, wind, wdir = get_weather()
            st.session_state.tide = t_cm
            st.session_state.phase = t_ph
            st.session_state.wind = wind
            st.session_state.wdir = wdir
            st.session_state.month = datetime.now().month
            st.success("最新データを取得しました！")

        c1, c2, c3 = st.columns(3)
        month = c1.selectbox("月", list(range(1, 13)), index=st.session_state.get('month', datetime.now().month-1))
        tide = c2.number_input("潮位(cm)", 0, 400, value=st.session_state.get('tide', 150))
        phase = c3.selectbox("潮位フェーズ", ["上げ", "下げ", "満潮", "干潮"], 
                             index=["上げ", "下げ", "満潮", "干潮"].index(st.session_state.get('phase', "下げ") if st.session_state.get('phase') in ["上げ", "下げ", "満潮", "干潮"] else 1))
        
        c4, c5 = st.columns(2)
        wind = c4.number_input("風速(m)", 0.0, 20.0, value=st.session_state.get('wind', 2.0))
        wdir = c5.selectbox("風向", ["北", "北東", "東", "南東", "南", "南西", "西", "北西"], 
                            index=["北", "北東", "東", "南東", "南", "南西", "西", "北西"].index(st.session_state.get('wdir', "北")))

    # --- 2. マッチングロジック ---
    st.divider()
    
    def calculate_score(row):
        score = 0
        # 1. 月（dateから月を抽出して比較）
        try:
            row_month = pd.to_datetime(row['date']).month
            if row_month == month: score += 30
        except: pass

        # 2. 潮位（±20cm以内なら加点）
        try:
            if abs(row['潮位_cm'] - tide) <= 20: score += 30
        except: pass

        # 3. 潮位フェーズ（一致で加点）
        if str(row.get('潮位フェーズ')) == phase: score += 20
        
        # 4. 風向（一致で加点）
        if str(row.get('風向')) == wdir: score += 20
        
        return score

    if not df.empty:
        # スコア計算
        df['マッチ度'] = df.apply(calculate_score, axis=1)
        
        # 場所ごとに最高スコアをまとめてランキング化
        ranking = df.sort_values('マッチ度', ascending=False).drop_duplicates(subset=['場所']).head(5)

        st.subheader("📍 推奨ポイント・ランキング")
        
        for i, row in ranking.iterrows():
            with st.container():
                cols = st.columns([1, 4])
                cols[0].metric("マッチ度", f"{row['マッチ度']}%")
                with cols[1]:
                    # カラム名「場所」を使用
                    st.markdown(f"### {row['場所']}")
                    # 過去の釣果に基づいた情報を表示
                    st.write(f"**過去実績:** {row['魚種']} {row['全長_cm']}cm | **ヒットルアー:** {row['ルアー']}")
                    if pd.notna(row['備考']):
                        st.info(f"💡 **備考:** {row['備考']}")
                st.divider()
    else:
        st.warning("データファイルが読み込まれていません。")
