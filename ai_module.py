import streamlit as st
import google.generativeai as genai
import pandas as pd

def show_ai_page(conn, url, df):
    # --- 1. スタイル設定 ---
    st.markdown("""
        <style>
        [data-testid="stChatMessageAssistant"] {
            background-color: #1a1c23;
            color: #eeeeee;
            border: 1px solid #ff4b4b;
            border-radius: 15px;
        }
        [data-testid="stChatMessageUser"] {
            background-color: #004a33;
            color: white;
            border-radius: 15px;
        }
        .profile-name {
            font-size: 1.2rem; font-weight: bold; color: #ff4b4b;
        }
        </style>
    """, unsafe_allow_html=True)

    AI_ICON = "demon_sato.png"
    USER_ICON = "👤"

    # --- 2. ヘッダー ---
    col1, col2 = st.columns([1, 4])
    with col1:
        try: st.image(AI_ICON)
        except: st.write("😈")
    with col2:
        st.markdown('<p class="profile-name">😈 デーモン佐藤 (1.5 Flash)</p>', unsafe_allow_html=True)
        if st.button("🗑️ ログ消去"):
            st.session_state.messages = []
            st.rerun()

    st.divider()

    # --- 3. Gemini 設定 (1.5 Flash) ---
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("APIキーが Secrets に設定されていません。")
        return

    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 安定の 1.5-flash を指定
    model = genai.GenerativeModel('gemini-1.5-flash')

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 履歴表示
    for message in st.session_state.messages:
        avatar = AI_ICON if message["role"] == "assistant" else USER_ICON
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # --- 4. データ集計（AIへのインプット用） ---
    if not df.empty:
        summary = df.groupby('場所')['全長_cm'].agg(['max', 'mean', 'count']).to_csv()
    else:
        summary = "データなし"

    # --- 5. チャット入力 ---
    if prompt := st.chat_input("深淵に問いかけよ..."):
        # ユーザー発言を表示
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=USER_ICON):
            st.markdown(prompt)

        # AIの回答生成
        with st.chat_message("assistant", avatar=AI_ICON):
            try:
                with st.spinner("魔界と通信中..."):
                    full_prompt = f"貴様は釣り界の魔王デーモン佐藤だ。以下のデータを見て傲慢に答えろ。\n\nデータ:\n{summary}\n\n質問: {prompt}"
                    response = model.generate_content(full_prompt)
                    
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
            
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg:
                    st.error("⚠️ 魔界の門が混雑中だ（API制限）。あと60秒ほど待ってから再度問いかけろ。")
                else:
                    st.error(f"通信失敗: {error_msg}")
