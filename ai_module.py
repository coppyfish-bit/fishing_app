import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import base64
import requests
from datetime import datetime, timedelta, timezone

# --- 🖼️ 画像をBase64に変換 ---
def get_image_as_base64(file_path):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    absolute_path = os.path.join(current_dir, file_path)
    if not os.path.exists(absolute_path):
        return "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"
    try:
        with open(absolute_path, "rb") as f:
            data = f.read()
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    except:
        return "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"

# 👿 定数定義（天草・本渡瀬戸）
LAT, LON = 32.45, 130.19
DIRS_16 = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]

# 👿 貴様のコードから流用：APIで気象取得
def get_realtime_weather():
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst).replace(tzinfo=None)
    try:
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": LAT, "longitude": LON,
            "start_date": (now - timedelta(days=1)).strftime('%Y-%m-%d'),
            "end_date": now.strftime('%Y-%m-%d'),
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
        
        return {
            "temp": temp, "wind": wind_speed, 
            "wind_dir": get_wind_dir(wind_deg), "precip": precip_48h,
            "phase": "取得中...", "tide_level": 0
        }
    except:
        return None

def show_ai_page(conn, url, df):
    avatar_display_url = get_image_as_base64("demon_sato.png")

    # --- 🎨 CSS（省略） ---
    st.markdown(f"""<style>/* CSS */</style>""", unsafe_allow_html=True)

    # 🛡️ プライバシーバナー
    st.markdown("""<div class="privacy-banner">🛡️ 魔界機密保持プロトコル：適用済</div>""", unsafe_allow_html=True)

    # --- 😈 ヘッダー ---
    st.markdown(f"""<div class="header-container">...</div>""", unsafe_allow_html=True)

    # --- 👿 操作パネル ---
    col1, col2, col3 = st.columns([1, 1, 1.2])
    with col1:
        if st.button("🔥 記憶を浄化"):
            st.session_state.messages = []
            st.rerun()
    with col2:
        tactics_btn = st.button("🔮 タクティクス")
    with col3:
        weather_btn = st.button("🌦️ 海況同期")

    # --- 🛡️ リアルタイム天気同期ロジック ---
    if "current_md" not in st.session_state: st.session_state.current_md = None
    
    if weather_btn:
        with st.spinner("深淵の空と海を同期中..."):
            st.session_state.current_md = get_realtime_weather()
            if st.session_state.current_md:
                st.success("海況データ同期完了")
            else:
                st.error("天候同期失敗")

    md = st.session_state.current_md

    # --- 📊 魔導要約エンジン ---
    global_knowledge = "【データなし】"
    if df is not None and not df.empty:
        # ...（前回の魔導書生成ロジック）
        pass

    # --- 🔑 モデル設定 ---
    api_key = st.secrets.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-3-flash-preview', tools=[{"google_search_retrieval": {}}])
    model_internal = genai.GenerativeModel('gemini-3-flash-preview')

    # --- 💬 トーク履歴（省略） ---

    # --- 💬 入力エリア ---
    if prompt := st.chat_input("深淵へ問いかけよ..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # 👿 同期されたmdデータを使用
        curr = f"気温:{md['temp']}℃, 風:{md['wind_dir']} {md['wind']}m, 降水:{md['precip']}mm" if md else "不明"

        with st.spinner("魔導書と状況を照合中..."):
            system_base = f"デーモン佐藤だ。魔導書:{global_knowledge}\n状況:{curr}"

            try:
                # 👿 検索あり試行
                response = model.generate_content(f"{system_base}\n質問:{prompt}")
                answer = response.text
            except Exception as e:
                # 👿 429時のバックダウン試行
                if "429" in str(e):
                    response = model_internal.generate_content(f"{system_base}\n質問:{prompt}")
                    answer = "（ククク……外界がうるさい、我の叡智のみで答えてやる）\n\n" + response.text
                else: answer = f"事故: {e}"

            st.session_state.messages.append({"role": "assistant", "content": answer})
            st.rerun()

    # --- 🔮 タクティクス生成 ---
    if tactics_btn and md:
        with st.spinner("戦術展開中..."):
            tactics_prompt = f"魔導書:{global_knowledge}\n状況:{curr}\n今日の最適な攻め方は？"
            response = model_internal.generate_content(tactics_prompt)
            st.session_state.messages.append({"role": "assistant", "content": f"【戦術託宣】\n{response.text}"})
            st.rerun()
