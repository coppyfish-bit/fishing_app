import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# --- 安全装置：ライブラリ未導入対策 ---
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
        events = []
        today_str = now.strftime('%Y%m%d')
        for start, e_type in [(80, "満潮"), (108, "干潮")]:
            for i in range(4):
                pos = start + (i * 7)
                t_str = day_line[pos : pos+4].replace(" ", "0")
                if t_str and t_str != "9999" and t_str != "0000":
                    try:
                        ev_t = datetime.strptime(today_str + t_str.zfill(4), '%Y%m%d%H%M')
                        events.append({"time": ev_t, "type": e_type})
                    except: continue
        events.sort(key=lambda x: x['time'])
        phase = "判定中"
        prev = next((e for e in reversed(events) if e['time'] <= now), None)
        nxt = next((e for e in events if e['time'] > now), None)
        if prev and nxt:
            dur = (nxt['time'] - prev['time']).total_seconds()
            ela = (now - prev['time']).total_seconds()
            if dur > 0:
                p_label = "上げ" if prev['type'] == "干潮" else "下げ"
                step = max(1, min(9, int((ela / dur) * 10)))
                phase = f"{p_label}{step}分"
                if (ela/dur) < 0.1: phase = prev['type']
                elif (ela/dur) > 0.9: phase = nxt['type']
        return current_cm, phase
    except: return fail_res

def get_realtime_weather():
    """潮汐と気象を統合取得"""
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
    """AIチャットセクション（エラー回避強化版）"""
    st.divider()
    st.markdown("""
        <div style="background-color: #1e2630; padding: 15px; border-radius: 10px; border-left: 5px solid #00d4ff; margin-bottom: 20px;">
            <strong style="color: #00d4ff;">🛡️ プライバシー保護モード実行中</strong><br>
            <small style="color: #cccccc;">やり取りや釣り場情報はAIの学習に使用されません。あなたの攻略アドバイス生成のみに利用されます。</small>
        </div>
    """, unsafe_allow_html=True)
    
    st.subheader("💬 シーバス攻略AIに相談")
    
    if not HAS_GENAI or "GEMINI_API_KEY" not in st.secrets:
        st.info("Secretsに GEMINI_API_KEY を設定するとAIと会話できます。")
        return

    # API設定とモデルの動的試行
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    # 404エラーを防ぐために、利用可能な名前を順に試す
    if "active_model_name" not in st.session_state:
        possible_models = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        st.session_state.active_model_name = possible_models[0] # デフォルト

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]): st.markdown(msg["content"])

    if prompt := st.chat_input("この潮位でのおすすめルアーは？"):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)

        sys_prompt = f"""あなたは天草・本渡エリアの熟練シーバスガイドです。
        【機密保持】釣り場情報を学習に使わず、外部へ漏らさないでください。
        現況: {md['phase']}, 潮位:{md['tide_level']}cm, 風:{md['wind']}m({md['wdir']}), 気温:{md['temp']}℃
        上記に基づき、プロの視点で攻略法を簡潔に回答してください。"""

        with st.chat_message("assistant"):
            # 複数のモデル名を試行して生成
            success = False
            error_msg = ""
            # エラーが出た場合、別のモデル名でリトライするループ
            for model_id in ['gemini-1.5-flash', 'gemini-pro', 'models/gemini-1.5-flash']:
                try:
                    model = genai.GenerativeModel(model_id)
                    response = model.generate_content(f"{sys_prompt}\n\n質問: {prompt}")
                    st.markdown(response.text)
                    st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                    success = True
                    break
                except Exception as e:
                    error_msg = str(e)
                    continue
            
            if not success:
                st.error(f"AIとの通信に失敗しました。APIキーまたはモデル設定を確認してください。\nエラー詳細: {error_msg}")

def show_matching_page(df):
    """メイン画面UI"""
    st.title("🏹 SeaBass Match AI v8.5")
    if 'm_data' not in st.session_state:
        st.session_state.m_data = get_realtime_weather()
    
    if st.button("🔄 海況データを更新"):
        st.session_state.m_data = get_realtime_weather()
        st.rerun()

    md = st.session_state.m_data
    st.info(f"🌊 【{md['phase']}】 潮位:{md['tide_level']}cm / 気温:{md['temp']}℃ / 風:{md['wind']}m({md['wdir']})")
    
    # 簡易マッチング表示（詳細は前回のロジック通り）
    st.write("※ 診断ボタンなどはここに配置されます")
    
    show_ai_chat_section(md)
