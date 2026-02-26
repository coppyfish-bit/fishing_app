import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

def show_ai_page(conn, url, df):
    # --- 🎨 魔界LINE風スタイング（CSS） ---
    st.markdown("""
        <style>
        .stApp { background-color: #0e1117; }
        .user-bubble {
            align-self: flex-end; background-color: #0084ff; color: white;
            padding: 10px 15px; border-radius: 18px 18px 2px 18px;
            max-width: 75%; font-size: 1rem; margin-bottom: 10px;
        }
        .demon-bubble {
            align-self: flex-start; background-color: #262730; color: #e0e0e0;
            padding: 10px 15px; border-radius: 18px 18px 18px 2px;
            max-width: 80%; font-size: 1rem; border-left: 4px solid #ff4b4b;
            margin-bottom: 10px;
        }
        .name-label { font-size: 0.7rem; color: #888; margin-bottom: 2px; }
        .avatar-img { width: 40px; height: 40px; border-radius: 50%; margin-right: 10px; }
        .mana-status { font-size: 0.8rem; color: #ff4b4b; font-weight: bold; }
        </style>
    """, unsafe_allow_html=True)

    # --- 🔑 API設定 ---
    api_key = st.secrets.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    # --- 🔮 魔力（リミット）管理システム ---
    if "mana_saving_mode" not in st.session_state:
        st.session_state.mana_saving_mode = False

    # モデルの召喚（モードによって検索ツールを切り替える）
    try:
        if st.session_state.mana_saving_mode:
            # 節約モード：検索封印
            model = genai.GenerativeModel('gemini-3-flash-preview')
            mana_text = "⚠️ 魔力枯渇につき『節約詠唱』中（検索不可）"
        else:
            # 通常モード：検索解禁
            model = genai.GenerativeModel(
                model_name='gemini-3-flash-preview',
                tools=[{'google_search_retrieval': {}}]
            )
            mana_text = "🔥 魔力充填……『全知全能の眼』開放中"
    except:
        model = genai.GenerativeModel('gemini-1.5-flash')
        mana_text = "🌀 通信不安定"

    # --- 😈 ヘッダーエリア ---
    st.title("😈 魔界トーク")
    st.markdown(f"<p class='mana-status'>{mana_text}</p>", unsafe_allow_html=True)
    
    # データ整形
    analysis_cols = ['date', 'time', '場所', '魚種', '全長_cm', '潮名', '潮位フェーズ', '備考']
    existing_cols = [c for c in analysis_cols if c in df.columns]
    data_summary = df[existing_cols].tail(20).to_csv(index=False)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # チャット表示
    chat_placeholder = st.container()
    with chat_placeholder:
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f'<div style="display: flex; flex-direction: column; align-items: flex-end;"><div class="name-label">貴様</div><div class="user-bubble">{message["content"]}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="display: flex; align-items: flex-start;">
                    <img src="https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png" class="avatar-img">
                    <div style="display: flex; flex-direction: column;">
                        <div class="name-label">デーモン佐藤</div>
                        <div class="demon-bubble">{message["content"]}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # --- ⌨️ 入力エリア ---
    if prompt := st.chat_input("メッセージを送信..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.spinner("深淵なる魔力を練り上げ中..."):
            try:
                system_instruction = f"""あなたは傲慢な釣り師「デーモン佐藤」です。釣果データ:{data_summary}。口調は「我」「貴様」。"""
                
                # 回答生成を試みる
                response = model.generate_content(f"{system_instruction}\n\n質問: {prompt}")
                
                # 成功したら（もし節約モード中だったら）魔力回復を宣言
                if st.session_state.mana_saving_mode:
                    st.session_state.mana_saving_mode = False
                    st.toast("ククク... 魔力が満ちたぞ。全知全能の眼を再開する！")

                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()

            except Exception as e:
                # 429エラー（魔力切れ）を検知！
                if "429" in str(e):
                    st.session_state.mana_saving_mode = True
                    error_msg = "ククク……無礼な！魔力が一時的に底を突いたわ！『節約詠唱』に切り替える。数分後にまた問いかけよ。"
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    st.rerun()
                else:
                    st.error(f"魔界通信事故: {e}")

    if st.sidebar.button("チャット履歴を浄化"):
        st.session_state.messages = []
        st.rerun()
