import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- データ取得関数 ---
def get_jma_tide_hs():
    """気象庁HPから本渡の現在の潮位を取得"""
    now = datetime.now()
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/HS.txt"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200: return 150, "下げ"
        lines = res.text.splitlines()
        target_y, target_m, target_d = int(now.strftime('%y')), now.month, now.day
        for line in lines:
            if len(line) < 100: continue
            if int(line[72:74]) == target_y and int(line[74:76]) == target_m and int(line[76:78]) == target_d:
                hourly = [int(line[i*3 : (i+1)*3].strip() or 0) for i in range(24)]
                h, m = now.hour, now.minute
                t1, t2 = hourly[h], hourly[h+1] if h < 23 else hourly[h]
                current_cm = int(t1 + (t2 - t1) * (m / 60.0))
                phase = "上げ" if t2 >= t1 else "下げ"
                return current_cm, phase
    except: pass
    return 150, "下げ"

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

# --- メイン表示関数 ---
def show_matching_page(df):
    st.title("🏹 SeaBass Matcher Pro")
    st.caption("月・潮位・フェーズ・風向から過去の爆釣データを検索")

    # セッション状態の初期化
    if 'tide' not in st.session_state: st.session_state.tide = 150
    if 'phase' not in st.session_state: st.session_state.phase = "下げ"
    if 'wind' not in st.session_state: st.session_state.wind = 2.0
    if 'wdir' not in st.session_state: st.session_state.wdir = "北"
    if 'month' not in st.session_state: st.session_state.month = datetime.now().month

    # --- 1. 入力セクション ---
    with st.expander("🌍 海況データの設定（自動取得または手入力）", expanded=True):
        if st.button("🔄 リアルタイム情報を取得"):
            t_cm, t_ph = get_jma_tide_hs()
            temp, wind_spd, wdir_val = get_weather()
            st.session_state.tide = t_cm
            st.session_state.phase = t_ph
            st.session_state.wind = wind_spd
            st.session_state.wdir = wdir_val
            st.session_state.month = datetime.now().month
            st.rerun()

        c1, c2, c3 = st.columns(3)
        month = c1.selectbox("月", list(range(1, 13)), index=st.session_state.month - 1)
        tide_input = c2.number_input("潮位(cm)", 0, 400, value=st.session_state.tide)
        
        phase_options = ["上げ", "下げ", "満潮", "干潮"]
        default_p = st.session_state.phase if st.session_state.phase in phase_options else "下げ"
        phase_input = c3.selectbox("潮位フェーズ", phase_options, index=phase_options.index(default_p))
        
        c4, c5 = st.columns(2)
        wind_input = c4.number_input("風速(m)", 0.0, 20.0, value=st.session_state.wind)
        wdir_options = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
        default_w = st.session_state.wdir if st.session_state.wdir in wdir_options else "北"
        wdir_input = c5.selectbox("風向", wdir_options, index=wdir_options.index(default_w))

    # --- 2. マッチングロジック ---
    st.divider()
    
    def calculate_score(row):
        score = 0
        # 月の判定
        try:
            if pd.to_datetime(row['date']).month == month: score += 30
        except: pass
        # 潮位判定 (±20cm以内)
        try:
            if abs(row['潮位_cm'] - tide_input) <= 20: score += 30
        except: pass
        # フェーズ判定
        if str(row.get('潮位フェーズ')) == phase_input: score += 20
        # 風向判定
        if str(row.get('風向')) == wdir_input: score += 20
        return score

    if not df.empty:
        df['マッチ度'] = df.apply(calculate_score, axis=1)
        # 同じ場所はスコア最高のものだけ残してランキング化
        ranking = df.sort_values('マッチ度', ascending=False).drop_duplicates(subset=['場所']).head(5)

        st.subheader("📍 おすすめポイント（過去の実績から算出）")
        
        for i, row in ranking.iterrows():
            with st.container():
                cols = st.columns([1, 4])
                cols[0].metric("マッチ度", f"{row['マッチ度']}%")
                with cols[1]:
                    st.markdown(f"### {row['場所']}")
                    st.write(f"📏 **過去の釣果:** {row['魚種']} {row['全長_cm']}cm")
                    st.write(f"🎣 **使用ルアー:** {row['ルアー']}")
                    if pd.notna(row['備考']):
                        st.caption(f"📝 備考: {row['備考']}")
                st.divider()
    else:
        st.warning("データ(df)が空です。Excelファイルを確認してください。")
