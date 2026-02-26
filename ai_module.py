import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import base64

# 画像をBase64に変換
def get_image_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    except:
        return "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"

def show_ai_page(conn, url, df):
    # --- 🖼️ アイコン設定 ---
    avatar_path = "demon_sato.png"
    if os.path.exists(avatar_path):
        avatar_display_url = get_image_as_base64(avatar_path)
    else:
        avatar_display_url = "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"

    # --- 🎨 CSS（LINE風UI & ボタン装飾） ---
    st.markdown(f"""
        <style>
        .stApp {{ background-color: #0e1117; }}
        .user-bubble {{
            align-self: flex-end; background-color: #0084ff; color: white;
            padding: 10px 15px; border-radius: 18px 18px 2px 18px;
            max-width: 75%; font-size: 1rem; margin-bottom: 10px;
        }}
        .demon-bubble {{
            align-self: flex-start; background-color: #262730; color: #e0e0e0;
            padding: 10px 15px; border-radius: 18px 18px 18px 2px;
            max-width: 80%; font-size: 1rem; border-left: 4px solid #ff4b4b;
            margin-bottom: 10px;
        }}
        .avatar-img {{ width: 45px; height: 45px; border-radius: 50%; margin-right: 10px; object-fit: cover; border: 1px solid #ff4b4b; }}
        .header-container {{
            display: flex; align-items: center; background: rgba(255, 75, 75, 0.1);
            padding: 15px; border-radius: 15px; margin-bottom: 10px; border: 1px solid #ff4b4b;
        }}
        .header-img {{ width: 80px; height: 80px; border-radius: 10px; margin-right: 20px; object-fit: cover; }}
        
        /* 浄化ボタンを赤く目立たせる */
        div.stButton > button:first-child {{
            background-color: #ff4b4b; color: white; border-radius: 20px;
            width: 100%; border: none; font-weight: bold;
        }}
        </style>
    """, unsafe_allow_html=True)

    # --- 🔑 API設定 ---
    api_key = st.secrets.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-3-flash-preview')

    # --- 😈 ヘッダーエリア ---
    st.markdown(f"""
        <div class="header-container">
            <img src="{avatar_display_url}" class="header-img">
            <div>
                <h2 style="color: #ff4b4b; margin: 0;">魔界トーク</h2>
                <p style="color: #00ff00; font-size: 0.8rem; margin: 5px 0;">● 安定接続モード（検索機能：封印中）</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- ✨ 【特等席】履歴浄化ボタン ---
    if st.button("🔥 チャット履歴を浄化（記憶を消す）"):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")

    # データ準備
    data_summary = df.tail(20).to_csv(index=False) if df is not None else "データなし"
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # チャット表示
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f'<div style="display: flex; flex-direction: column; align-items: flex-end;"><div class="user-bubble">{message["content"]}</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="display: flex; align-items: flex-start;"><img src="{avatar_display_url}" class="avatar-img"><div class="demon-bubble">{message["content"]}</div></div>', unsafe_allow_html=True)

    # --- 💬 入力エリア ---
    if prompt := st.chat_input("デーモン佐藤に問いかける..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.spinner("深淵なる知能で分析中..."):
            try:
                system_instruction = f"あなたは傲慢な釣り師「デーモン佐藤」です。釣果データ:{data_summary}。口調は『我』『貴様』。最後は突き放せ。"
                response = model.generate_content(f"{system_instruction}\n\n質問: {prompt}")
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()
            except Exception as e:
                st.error(f"魔界との通信が途絶した: {e}")
