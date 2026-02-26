import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

def show_ai_page(conn, url, df):
    # --- 🎨 魔界LINE風スタイング（CSS） ---
    st.markdown("""
        <style>
        /* 背景色とフォント */
        .stApp {
            background-color: #0e1117;
        }
        
        /* チャット全体のコンテナ */
        .chat-container {
            display: flex;
            flex-direction: column;
            gap: 15px;
            padding: 10px;
        }

        /* ユーザーの吹き出し（右側） */
        .user-bubble {
            align-self: flex-end;
            background-color: #0084ff;
            color: white;
            padding: 10px 15px;
            border-radius: 18px 18px 2px 18px;
            max-width: 70%;
            font-size: 1rem;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
        }

        /* デーモン佐藤の吹き出し（左側） */
        .demon-bubble {
            align-self: flex-start;
            background-color: #262730;
            color: #e0e0e0;
            padding: 10px 15px;
            border-radius: 18px 18px 18px 2px;
            max-width: 75%;
            font-size: 1rem;
            border-left: 4px solid #ff4b4b;
            box-shadow: -2px 2px 5px rgba(0,0,0,0.3);
        }

        /* 名前ラベル */
        .name-label {
            font-size: 0.7rem;
            color: #888;
            margin-bottom: 2px;
        }
        
        /* アバター画像 */
        .avatar-img {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            margin-right: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 🔑 モデル設定 ---
    api_key = st.secrets.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name='gemini-3-flash-preview',
        tools=[{'google_search_retrieval': {}}] 
    )

    # --- 😈 ヘッダーエリア ---
    st.title("😈 魔界トーク")
    st.caption("デーモン佐藤との密談（学習・漏洩なし）")

    # データの整形
    analysis_cols = ['date', 'time', '場所', '魚種', '全長_cm', '潮名', '潮位フェーズ', '気温', '風速', '備考']
    existing_cols = [c for c in analysis_cols if c in df.columns]
    data_summary = df[existing_cols].tail(30).to_csv(index=False)

    # チャット履歴の初期化
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # --- 💬 チャット表示エリア ---
    chat_placeholder = st.container()
    
    with chat_placeholder:
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f'<div style="display: flex; flex-direction: column; align-items: flex-end;"><div class="name-label">貴様</div><div class="user-bubble">{message["content"]}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="display: flex; align-items: flex-start;">
                    <div style="flex-shrink: 0;">
                        <img src="https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png" class="avatar-img">
                    </div>
                    <div style="display: flex; flex-direction: column;">
                        <div class="name-label">デーモン佐藤</div>
                        <div class="demon-bubble">{message["content"]}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

    # --- ⌨️ 入力エリア ---
    if prompt := st.chat_input("メッセージを送信..."):
        # 履歴に追加
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # 佐藤の回答
        try:
            system_instruction = f"""あなたは傲慢な釣り師「デーモン佐藤」です。釣果データ:{data_summary}。傲慢かつ論理的に回答し、最後は突き放せ。"""
            response = model.generate_content(f"{system_instruction}\n\n質問: {prompt}")
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            st.rerun()
        except Exception as e:
            st.error(f"魔界通信エラー: {e}")
