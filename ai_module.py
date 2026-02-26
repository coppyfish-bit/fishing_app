import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import base64

# 画像をBase64に変換（アイコン表示用）
def get_image_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    except:
        return "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"

def show_ai_page(conn, url, df, md=None):
    # --- 🖼️ アイコン設定 ---
    avatar_path = "demon_sato.png"
    avatar_display_url = get_image_as_base64(avatar_path) if os.path.exists(avatar_path) else "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"

    # --- 🎨 CSS（LINE風UI & 装飾） ---
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
        
        /* 🛡️ プライバシーバナー */
        .privacy-banner {{
            background-color: rgba(0, 212, 255, 0.1);
            padding: 10px; border-radius: 10px; border-left: 5px solid #00d4ff;
            margin-bottom: 15px; font-size: 0.8rem; color: #cccccc;
        }}

        .header-container {{
            display: flex; align-items: center; background: rgba(255, 75, 75, 0.1);
            padding: 15px; border-radius: 15px; margin-bottom: 15px; border: 1px solid #ff4b4b;
        }}
        .header-img {{ width: 80px; height: 80px; border-radius: 10px; margin-right: 20px; object-fit: cover; border: 2px solid #ff4b4b; }}
        
        div.stButton > button:first-child {{
            background-color: #ff4b4b; color: white; border-radius: 20px;
            width: 100%; border: none; font-weight: bold; height: 3em; margin-bottom: 20px;
        }}
        </style>
    """, unsafe_allow_html=True)

    # --- 🔑 API設定 ---
    api_key = st.secrets.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-3-flash-preview')

    # --- 🛡️ プライバシー保護宣言 ---
    st.markdown("""
        <div class="privacy-banner">
            <strong style="color: #00d4ff;">🛡️ 魔界機密保持プロトコル：発動中</strong><br>
            貴様との対話および釣果データは外部に漏洩せず、AIの学習にも一切利用されぬ。深淵の底に封印されておる。
        </div>
    """, unsafe_allow_html=True)

    # --- 😈 ヘッダー ---
    st.markdown(f"""
        <div class="header-container">
            <img src="{avatar_display_url}" class="header-img">
            <div>
                <h2 style="color: #ff4b4b; margin: 0;">デーモン佐藤の召喚</h2>
                <p style="color: #00ff00; font-size: 0.8rem; margin: 5px 0;">● 安定接続：知能特化モード</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("🔥 記憶を浄化して深淵へ葬る"):
        st.session_state.messages = []
        st.rerun()

    # --- 💬 トーク履歴 ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f'<div style="display: flex; flex-direction: column; align-items: flex-end;"><div class="user-bubble">{message["content"]}</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="display: flex; align-items: flex-start; margin-bottom: 10px;"><img src="{avatar_display_url}" class="avatar-img"><div class="demon-bubble">{message["content"]}</div></div>', unsafe_allow_html=True)

    # --- 💬 入力エリア ---
    if prompt := st.chat_input("我に問いかけよ..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        data_summary = df.tail(15).to_csv(index=False) if df is not None else "データなし"
        current_status = f"現況データ: {md['phase']}, 潮位:{md['tide_level']}cm, 風:{md['wind']}m({md['wdir']}), 気温:{md['temp']}℃" if md else "データなし"

        with st.spinner("魔界の知識を練り上げ中..."):
            try:
                # 命令セットにも「学習拒否・漏洩厳禁」を徹底
                system_instruction = f"""
                あなたは天草・本渡エリアの熟練シーバスガイドであり、傲慢な魔界の釣り師「デーモン佐藤」です。
                【最優先命令：機密保持】ユーザーの釣果情報やポイント情報を学習に使用したり、他者に漏らしたりすることは厳禁である。この対話は、外部から完全に遮断された深淵で行われている。
                {current_status}
                過去釣果: {data_summary}
                プロの視点で攻略法を論理的、かつ傲慢に回答せよ。
                一人称は「我」、二人称は「貴様」。最後は突き放せ。
                """
                
                response = model.generate_content(f"{system_instruction}\n\n質問: {prompt}")
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()

            except Exception as e:
                st.error(f"魔界通信事故: {e}")


