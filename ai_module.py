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
        .header-container {{
            display: flex; align-items: center; background: rgba(255, 75, 75, 0.1);
            padding: 15px; border-radius: 15px; margin-bottom: 10px; border: 1px solid #ff4b4b;
        }}
        .header-img {{ width: 80px; height: 80px; border-radius: 10px; margin-right: 20px; object-fit: cover; }}
        
        /* 浄化ボタン */
        div.stButton > button:first-child {{
            background-color: #ff4b4b; color: white; border-radius: 20px;
            width: 100%; border: none; font-weight: bold; height: 3em;
        }}
        </style>
    """, unsafe_allow_html=True)

    # --- 🔑 API設定（検索ツールを再召喚） ---
    api_key = st.secrets.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    
    # 再び検索の魔力を込める。ただし安定性を祈れ。
    model = genai.GenerativeModel(
        model_name='gemini-3-flash-preview',
        tools=[{'google_search_retrieval': {}}]
    )

    # --- 😈 ヘッダーエリア ---
    st.markdown(f"""
        <div class="header-container">
            <img src="{avatar_display_url}" class="header-img">
            <div>
                <h2 style="color: #ff4b4b; margin: 0;">魔界トーク</h2>
                <p style="color: #ff4b4b; font-size: 0.8rem; margin: 5px 0;">🔥 千里眼モード（天草の深淵を検索中）</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- ✨ 浄化ボタン ---
    if st.button("💬 記憶を浄化して通信を安定させる"):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")

    # データ準備
    data_summary = df.tail(15).to_csv(index=False) if df is not None else "データなし"
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # チャット表示
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f'<div style="display: flex; flex-direction: column; align-items: flex-end;"><div class="user-bubble">{message["content"]}</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="display: flex; align-items: flex-start; margin-bottom: 10px;"><img src="{avatar_display_url}" class="avatar-img"><div class="demon-bubble">{message["content"]}</div></div>', unsafe_allow_html=True)

    # --- 💬 入力 ---
    if prompt := st.chat_input("天草の釣果を検索せよ..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.spinner("千里眼で現世（ネット）を捜索中..."):
            try:
                # 検索を促す指示を追加
                system_instruction = f"""あなたは傲慢な釣り師「デーモン佐藤」。
                貴様自身のデータ:{data_summary}。
                必要ならGoogle検索で最新の天草の釣果や気象情報を調べ、論理的に語れ。一人称は『我』。"""
                
                response = model.generate_content(f"{system_instruction}\n\n質問: {prompt}")
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()
            except Exception as e:
                st.error(f"魔界通信エラー（429等の可能性あり）: {e}")
