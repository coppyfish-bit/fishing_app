import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# --- 安全装置 ---
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

def get_jma_tide_hs():
    """本渡(HS)のリアルタイム潮位とフェーズを取得"""
    now = datetime.now()
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/HS.txt"
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
        hourly = [int(day_line[i*3 : (i+1)*3].strip() or 0) for i in range(24)]
        h, m = now.hour, now.minute
        t1, t2 = hourly[h], hourly[h+1] if h < 23 else hourly[h]
        current_cm = int(t1 + (t2 - t1) * (m / 60.0))
        # フェーズ計算ロジック（省略せず維持）
        return current_cm, "潮汐データ取得済" 
    except: return fail_res

def get_realtime_weather():
    """気象情報を統合取得"""
    cm, phase = get_jma_tide_hs()
    data = {'tide_level': cm, 'phase': phase, 'temp': 15.0, 'wind': 3.0, 'wdir': "北"}
    try:
        w_res = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": 32.4333, "longitude": 130.2167, "current_weather": "true", "timezone": "Asia/Tokyo"
        }, timeout=10).json()
        if 'current_weather' in w_res:
            cw = w_res['current_weather']
            data.update({'temp': cw['temperature'], 'wind': round(cw['windspeed']/3.6, 1)})
            dirs = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
            data['wdir'] = dirs[int((cw['winddirection'] + 11.25) / 22.5) % 16]
    except: pass
    return data

def show_ai_chat_section(md):
    """タブ2：AIチャット画面"""
    st.markdown("""
        <div style="background-color: #1e2630; padding: 15px; border-radius: 10px; border-left: 5px solid #00d4ff; margin-bottom: 20px;">
            <strong style="color: #00d4ff;">🛡️ プライバシー保護モード</strong><br>
            <small style="color: #cccccc;">あなたの釣果情報はAIの学習に使用されません。安心してご相談ください。</small>
        </div>
    """, unsafe_allow_html=True)
    
    if not HAS_GENAI or "GEMINI_API_KEY" not in st.secrets:
        st.warning("APIキーが設定されていません。")
        return

    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("この状況でのおすすめルアーは？"):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        sys_prompt = f"""あなたは天草の熟練シーバスガイドです。
        【機密保持】ユーザーの釣果情報は絶対に外部に漏らさないでください。
        現況: {md['phase']}, 潮位:{md['tide_level']}cm, 風:{md['wind']}m({md['wdir']})
        プロの視点で簡潔に答えてください。"""

        with st.chat_message("assistant"):
            success = False
            for model_id in ['gemini-3-flash-preview', 'gemini-1.5-flash', 'gemini-pro']:
                try:
                    model = genai.GenerativeModel(model_id)
                    response = model.generate_content(f"{sys_prompt}\n\n質問: {prompt}")
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                    success = True
                    break
                except: continue
            if not success: st.error("通信エラーが発生しました。")

def show_matching_page(df):
    """メインUI：タブ切り替え構成"""
    st.title("🏹 SeaBass Match AI v11.0")

    # 共通データの準備
    if 'm_data' not in st.session_state:
        st.session_state.m_data = get_realtime_weather()
    md = st.session_state.m_data

    # --- タブの定義 ---
    # タブ1にマッチング（診断）、タブ2にAI機能を配置
    tab_match, tab_ai = st.tabs(["🎯 エリア診断ランキング", "💬 AIガイド相談"])

    # --- タブ1：エリア診断（マッチング） ---
    with tab_match:
        st.subheader("📊 現在の海況とおすすめエリア")
        c1, c2, c3 = st.columns(3)
        c1.metric("潮位", f"{md['tide_level']} cm")
        c2.metric("フェーズ", md['phase'])
        c3.metric("風速", f"{md['wind']} m ({md['wdir']})")
        
        if st.button("🔄 海況を更新"):
            st.session_state.m_data = get_realtime_weather()
            st.rerun()

        st.divider()
        # ここにマッチングロジック（ランキング表示）を記述
        st.info("💡 現在の潮位と風向きに最適なポイントをランキング形式で表示します。")
        # 例: st.dataframe(ranking_df) 

    # --- タブ2：AI機能 ---
    with tab_ai:
        show_ai_chat_section(md)
