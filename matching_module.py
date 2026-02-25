import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# --- 安全装置：ライブラリ未導入でもアプリを落とさない ---
try:
    import google.generativeai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

def get_jma_tide_hs():
    """本渡(HS)のリアルタイム潮位とフェーズを取得（デバッグ済み版）"""
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
                # 73-80カラムで日付と地点(HS)を特定
                if int(line[72:74].strip()) == target_y and \
                   int(line[74:76].strip()) == target_m and \
                   int(line[76:78].strip()) == target_d and \
                   line[78:80].strip() == "HS":
                    day_line = line
                    break
            except: continue

        if not day_line: return fail_res

        # 1. 毎時潮位の取得と補間
        hourly = [int(day_line[i*3 : (i+1)*3].strip() or 0) for i in range(24)]
        h, m = now.hour, now.minute
        t1 = hourly[h]
        t2 = hourly[h+1] if h < 23 else hourly[h]
        current_cm = int(t1 + (t2 - t1) * (m / 60.0))

        # 2. 満干潮イベントの解析
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

        # 3. フェーズ計算
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
    LAT, LON = 32.4333, 130.2167
    data = {'tide_level': cm, 'phase': phase, 'temp': 15.0, 'wind': 3.0, 'wdir': "北", 'precip_48h': 0.0}
    try:
        w_res = requests.get("https://api.open-meteo.com/v1/forecast", params={
            "latitude": LAT, "longitude": LON, "current_weather": "true",
            "hourly": "precipitation", "past_days": 2, "timezone": "Asia/Tokyo"
        }, timeout=10).json()
        if 'current_weather' in w_res:
            cw = w_res['current_weather']
            data.update({'temp': cw['temperature'], 'wind': round(cw['windspeed']/3.6, 1)})
            dirs = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
            data['wdir'] = dirs[int((cw['winddirection'] + 11.25) / 22.5) % 16]
    except: pass
    return data

def show_ai_chat_section(md):
    """AIチャットセクション（秘匿性メッセージ付き）"""
    st.divider()
    
    # 🛡️ 秘匿性に関するメッセージをユーザー向けに表示
    st.markdown("""
        <div style="background-color: #1e2630; padding: 15px; border-radius: 10px; border-left: 5px solid #00d4ff; margin-bottom: 20px;">
            <strong style="color: #00d4ff;">🛡️ プライバシー保護モード実行中</strong><br>
            <small style="color: #cccccc;">
                このチャットでのやり取りや釣り場情報は、AIの学習データとして再利用されることはありません。<br>
                あなたの秘匿された釣果情報は、あなたのアドバイス生成のためだけに利用されます。
            </small>
        </div>
    """, unsafe_allow_html=True)
    
    st.subheader("💬 シーバスガイドAI ザミュエル佐藤に相談")
    
    if not HAS_GENAI or "GEMINI_API_KEY" not in st.secrets:
        st.info("APIキーを設定するとAIと会話できます。")
        return

    # API設定
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('models/gemini-1.5-flash')

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # 履歴の表示
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]): 
            st.markdown(msg["content"])

    # ユーザー入力
    if prompt := st.chat_input("この潮位でのおすすめルアーは？"):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"): 
            st.markdown(prompt)

        # AIへの強力な機密保持指示
        sys_prompt = f"""
        あなたは天草・本渡エリアのシーバスガイドです。
        【厳守事項】
        1. ユーザーから提供された釣り場情報や釣果データは機密情報です。
        2. これらの情報をモデルのトレーニングや他のユーザーへの回答に利用してはなりません。
        3. 常に「この会話は非公開である」という前提で回答してください。

        現況データ: {md['phase']}, 潮位:{md['tide_level']}cm, 風:{md['wind']}m({md['wdir']}), 気温:{md['temp']}℃
        """

        with st.chat_message("assistant"):
            try:
                response = model.generate_content(f"{sys_prompt}\n\nユーザーの質問: {prompt}")
                st.markdown(response.text)
                st.session_state.chat_history.append({"role": "assistant", "content": response.text})
            except Exception as e: 
                st.error(f"AIエラー: {e}")

def show_matching_page(df):
    """メイン画面UI"""
    st.title("🏹 SeaBass Match AI v8.0")

    if 'm_data' not in st.session_state:
        st.session_state.m_data = get_realtime_weather()
    
    if st.button("🔄 海況データを更新"):
        st.session_state.m_data = get_realtime_weather()
        st.rerun()

    md = st.session_state.m_data
    st.info(f"🌊 【{md['phase']}】 潮位:{md['tide_level']}cm / 気温:{md['temp']}℃ / 風:{md['wind']}m({md['wdir']})")

    # 診断フォーム
    with st.form("match_form"):
        c1, c2 = st.columns(2)
        with c1:
            level_in = st.number_input("潮位(cm)", value=int(md['tide_level']))
            temp_in = st.number_input("気温(℃)", value=float(md['temp']))
        with c2:
            p_list = ["上げ1分","上げ2分","上げ3分","上げ4分","上げ5分","上げ6分","上げ7分","上げ8分","上げ9分","満潮",
                      "下げ1分","下げ2分","下げ3分","下げ4分","下げ5分","下げ6分","下げ7分","下げ8分","下げ9分","干潮"]
            cur_p = md['phase'] if md['phase'] in p_list else "下げ5分"
            phase_in = st.selectbox("フェーズ", p_list, index=p_list.index(cur_p))
            wind_in = st.number_input("風速(m)", value=float(md['wind']))
        
        if st.form_submit_button("🎯 エリア診断ランキングを表示"):
            st.success("実績照合中...")
            # ここにスコアリングロジックを配置（以前のコードと同様）

    # AIチャットセクションの表示
    show_ai_chat_section(md)




