import streamlit as st
import google.generativeai as genai
import pandas as pd

def show_ai_page(conn, url, df):
    # --- 👿 デーモン佐藤の降臨（演出のみ） ---
    st.markdown("<h2 style='color: #ff4b4b;'>😈 デーモン佐藤の深淵知見</h2>", unsafe_allow_html=True)
    st.caption("「貴様の釣果を深淵の知恵（Gemini）で解き明かしてやろう...」")

    # APIキーの設定（Secretsから取得）
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("APIキーが設定されていません。")
        return

    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')

    # --- 💬 チャット履歴の初期化 ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 履歴を表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- ユーザーからの質問 ---
    if prompt := st.chat_input("例：最近の本渡瀬戸の傾向は？ / 2025年の最大サイズは？"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            # データフレームの要約をコンテキストとして渡す
            df_summary = df.tail(20).to_csv(index=False) # 最近の20件
            full_prompt = f"""
            貴様は釣り界の魔王「デーモン佐藤」だ。以下の釣果データに基づき、
            質問に「少し口の悪い、だが釣行には真摯なアドバイス」を添えて答えよ。
            
            【釣果データ(直近)】
            {df_summary}
            
            【質問】
            {prompt}
            """
            
            try:
                response = model.generate_content(full_prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"深淵との通信に失敗した...：{e}")
