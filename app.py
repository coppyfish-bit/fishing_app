import streamlit as st
import pandas as pd
import requests
import google.generativeai as genai
import os
import base64
from datetime import datetime

# --- 👿 設定：ここを自分の情報に書き換えろ ---
GITHUB_USER = "coppyfish-bit"
REPO_NAME = "fishing_app"

# --- 🖼️ 画像をBase64に変換（アイコン用） ---
def get_image_as_base64(file_path):
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        absolute_path = os.path.join(current_dir, file_path)
        with open(absolute_path, "rb") as f:
            data = f.read()
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    except:
        return "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"

# --- 🔮 JSONデータをGitHubから召喚し、現在潮位を線形補間する関数 ---
def load_and_calculate_tide(code="HS"):
    now = datetime.now()
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/main/data/{now.year}/{code}.json"
    
    try:
        res = requests.get(url)
        if res.status_code != 200: return None, f"死霊通信失敗 ({res.status_code})"
        
        data = res.json()
        y, m, d = now.year, now.month, now.day
        t1, t2 = f"{y}-{m:02d}-{d:02d}", f"{y}-{m:>2d}-{d:>2d}"
        day_info = next((i for i in data['data'] if i['date'].strip() == t1 or i['date'] == t2), None)
        
        if not day_info: return None, "本日のデータが深淵に見当たりません"

        # --- 📏 線形補間ロジック（分単位の算出） ---
        h = now.hour
        mi = now.minute
        h1_tide = day_info['hourly'][h]
        h2_tide = day_info['hourly'][(h + 1) % 24]
        # 1時間ごとの差分を「分」で割って現在の高さを出す
        diff = h2_tide - h1_tide
        current_tide = h1_tide + (diff * (mi / 60.0))
        
        return {
            "current": current_tide,
            "h1": h1_tide,
            "h2": h2_tide,
            "events": day_info['events'],
            "hourly": day_info['hourly']
        }, None
    except Exception as e:
        return None, str(e)

# --- 📏 潮汐10分割（上げ/下げ○分）を算出する関数 ---
def calculate_tide_phase_10(now_time, events):
    if not events: return "データなし", 0
    sorted_events = sorted(events, key=lambda x: x['time'])
    now_str = now_time.strftime("%H:%M")
    
    prev_ev, next_ev = None, None
    for i in range(len(sorted_events)):
        if sorted_events[i]['time'] <= now_str:
            prev_ev = sorted_events[i]
        else:
            next_ev = sorted_events[i]
            break
            
    if not prev_ev or not next_ev: return "潮止まり", 0

    fmt = "%H:%M"
    t_prev = datetime.strptime(prev_ev['time'], fmt)
    t_next = datetime.strptime(next_ev['time'], fmt)
    t_now = datetime.strptime(now_str, fmt)
    
    total_min = (t_next - t_prev).total_seconds() / 60
    elapsed_min = (t_now - t_prev).total_seconds() / 60
    phase_num = int((elapsed_min / total_min) * 10)
    phase_num = min(max(phase_num, 0), 10)
    
    label = "📈 上げ" if prev_ev['type'] == 'low' else "📉 下げ"
    return f"{label} {phase_num} 分", phase_num

# --- 🎨 画面基本設定 ---
st.set_page_config(page_title="デーモン佐藤・深淵の祭壇", layout="centered")

# --- 🚧 巨大メンテナンス・バナー ---
st.markdown("""
    <style>
    .maint-banner {
        background-color: #800000; color: #ffffff; padding: 15px; 
        text-align: center; border: 4px double #ff0000; border-radius: 10px;
        margin-bottom: 20px; animation: blink 2s infinite;
    }
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }
    .stApp { background-color: #0e1117; }
    .tide-card { text-align: center; padding: 25px; background: rgba(0, 0, 0, 0.4); border-radius: 20px; border: 2px solid #ff4b4b; margin-bottom: 20px; }
    .user-bubble { align-self: flex-end; background-color: #0084ff; color: white; padding: 10px 15px; border-radius: 18px 18px 2px 18px; max-width: 75%; margin-bottom: 10px; }
    .demon-bubble { align-self: flex-start; background-color: #262730; color: #e0e0e0; padding: 10px 15px; border-radius: 18px 18px 18px 2px; max-width: 80%; border-left: 4px solid #ff4b4b; margin-bottom: 10px; }
    .avatar-img { width: 45px; height: 45px; border-radius: 50%; margin-right: 10px; object-fit: cover; border: 1px solid #ff4b4b; }
    </style>
    <div class="maint-banner">
        <h2 style="margin:0;">⚠️ 🚧 SYSTEM MAINTENANCE 🚧 ⚠️</h2>
        <p style="margin:5px 0 0 0;">デーモン佐藤が深淵のデータを調整中だ。一般人は立ち去れ。</p>
    </div>
""", unsafe_allow_html=True)

# --- 😈 デーモン佐藤・対話セクション ---
avatar_url = get_image_as_base64("demon_sato.png")
st.markdown(f"""
    <div style="display: flex; align-items: center; background: rgba(255, 75, 75, 0.1); padding: 15px; border-radius: 15px; border: 1px solid #ff4b4b; margin-bottom: 20px;">
        <img src="{avatar_url}" style="width:50px; border-radius:10px; margin-right:15px;">
        <div><h3 style="color: #ff4b4b; margin:0;">デーモン佐藤</h3><p style="color: #00ff00; font-size: 0.8rem; margin:0;">● 稼働中：深淵の対話プロトコル有効</p></div>
    </div>
""", unsafe_allow_html=True)

# --- 🧪 潮汐精密解析セクション ---
st.title("🧪 リアルタイム潮汐解析")
if st.button("🔥 現在の潮汐を暴き出せ"):
    result, err = load_and_calculate_tide("HS")
    if result:
        now = datetime.now()
        phase_text, phase_val = calculate_tide_phase_10(now, result['events'])
        
        st.markdown(f"""
            <div class="tide-card">
                <p style="color: #888; margin:0;">🎯 {now.strftime('%H:%M')} 推定潮位</p>
                <h1 style="color: #ffffff; font-size: 4.5rem; margin: 10px 0;">{result['current']:.1f}<span style="font-size: 1.5rem;">cm</span></h1>
                <h2 style="color: #ff4b4b; margin:0;">{phase_text}</h2>
                <p style="color: #555; font-size: 0.8rem; margin-top:10px;">{now.hour}:00({result['h1']}cm) → {(now.hour+1)%24}:00({result['h2']}cm) を線形補間</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.progress(phase_val / 10.0)
        st.line_chart(result['hourly'])
        st.table(pd.DataFrame(result['events']))
    else:
        st.error(f"召喚失敗: {err}")

# --- 💬 チャットセクション ---
if "messages" not in st.session_state: st.session_state.messages = []
for m in st.session_state.messages:
    role_class = "user-bubble" if m["role"] == "user" else "demon-bubble"
    content = f'<div style="display: flex; {"justify-content: flex-end" if m["role"] == "user" else ""}; margin-bottom: 10px;">'
    if m["role"] != "user": content += f'<img src="{avatar_url}" class="avatar-img">'
    content += f'<div class="{role_class}">{m["content"]}</div></div>'
    st.markdown(content, unsafe_allow_html=True)

if prompt := st.chat_input("深淵に問え..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    api_key = st.secrets.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(f"あなたは傲慢なプロガイド、デーモン佐藤だ。：{prompt}")
    st.session_state.messages.append({"role": "assistant", "content": response.text})
    st.rerun()
