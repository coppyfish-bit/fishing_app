import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import base64
import time

# --- 🖼️ 画像をBase64に変換 ---
def get_image_as_base64(file_path):
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        absolute_path = os.path.join(current_dir, file_path)
        with open(absolute_path, "rb") as f:
            data = f.read()
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    except:
        return "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"

# --- 🎨 画面構成 ---
st.set_page_config(page_title="デーモン佐藤・深淵の祭壇", layout="centered")

# --- 🚧 巨大メンテナンス・バナー ---
st.markdown("""
    <style>
    .maint-banner {
        background-color: #800000; 
        color: #ffffff; 
        padding: 20px; 
        text-align: center; 
        border: 5px double #ff0000; 
        border-radius: 15px;
        margin-bottom: 30px;
        animation: blink 2s infinite;
    }
    @keyframes blink {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }
    .stApp { background-color: #0e1117; }
    .user-bubble { align-self: flex-end; background-color: #0084ff; color: white; padding: 10px 15px; border-radius: 18px 18px 2px 18px; max-width: 75%; margin-bottom: 10px; }
    .demon-bubble { align-self: flex-start; background-color: #262730; color: #e0e0e0; padding: 10px 15px; border-radius: 18px 18px 18px 2px; max-width: 80%; border-left: 4px solid #ff4b4b; margin-bottom: 10px; }
    .avatar-img { width: 45px; height: 45px; border-radius: 50%; margin-right: 10px; object-fit: cover; border: 1px solid #ff4b4b; }
    </style>
    <div class="maint-banner">
        <h1 style="margin:0;">⚠️ 🚧 SYSTEM MAINTENANCE 🚧 ⚠️</h1>
        <p style="margin:5px 0 0 0;">現在、全機能を停止し魔界同期中である。立ち入りは推奨されん。</p>
    </div>
""", unsafe_allow_html=True)

# --- 😈 デーモン佐藤の本体（ここからは動く） ---
avatar_url = get_image_as_base64("demon_sato.png")

st.markdown(f"""
    <div style="display: flex; align-items: center; background: rgba(255, 75, 75, 0.1); padding: 15px; border-radius: 15px; border: 1px solid #ff4b4b;">
        <img src="{avatar_url}" style="width:50px; border-radius:10px; margin-right:15px;">
        <div>
            <h3 style="color: #ff4b4b; margin:0;">デーモン佐藤</h3>
            <p style="color: #00ff00; font-size: 0.8rem; margin:0;">● 稼働中：深淵の対話プロトコルのみ有効</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# --- 💬 AI対話ロジック ---
if "messages" not in st.session_state: st.session_state.messages = []

# 履歴表示
for m in st.session_state.messages:
    role_class = "user-bubble" if m["role"] == "user" else "demon-bubble"
    content = f'<div style="display: flex; {"justify-content: flex-end" if m["role"] == "user" else ""}; margin-bottom: 10px;">'
    if m["role"] != "user": content += f'<img src="{avatar_url}" class="avatar-img">'
    content += f'<div class="{role_class}">{m["content"]}</div></div>'
    st.markdown(content, unsafe_allow_html=True)

# 入力
if prompt := st.chat_input("メンテナンスを無視して深淵に問え..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    api_key = st.secrets.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    with st.spinner("デーモン祈祷中..."):
        response = model.generate_content(f"あなたは傲慢なプロガイド、デーモン佐藤だ。質問に答えろ：{prompt}")
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        st.rerun()
