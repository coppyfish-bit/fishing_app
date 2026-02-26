import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import base64

# 画像をBase64に変換してCSSで使いやすくする魔術
def get_image_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    except:
        return "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"

def show_ai_page(conn, url, df):
    # --- 🖼️ アイコンパスの確定 ---
    avatar_path = "demon_sato.png"
    # ローカル画像があればBase64化、なければ仮のURL
    if os.path.exists(avatar_path):
        avatar_display_url = get_image_as_base64(avatar_path)
    else:
        avatar_display_url = "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"

    # --- 🎨 魔界LINE風スタイリング（CSS） ---
    st.markdown(f"""
        <style>
        .stApp {{ background-color: #0e1117; }}
        
        /* ユーザーの吹き出し（右側） */
        .user-bubble {{
            align-self: flex-end; background-color: #0084ff; color: white;
            padding: 10px 15px; border-radius: 18px 18px 2px 18px;
            max-width: 75%; font-size: 1rem; margin-bottom: 10px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.3);
        }}
        
        /* デーモン佐藤の吹き出し（左側） */
        .demon-bubble {{
            align-self: flex-start; background-color: #262730; color: #e0e0e0;
            padding: 10px 15px; border-radius: 18px 18px 18px 2px;
            max-width: 80%; font-size: 1rem; border-left: 4px solid #ff4b4b;
            margin-bottom: 10px; box-shadow: -2px 2px 5px rgba(0,0,0,0.3);
        }}
        
        .name-label {{ font-size: 0.7rem; color: #888; margin-bottom: 2px; }}
        .avatar-img {{ width: 45px; height: 45px; border-radius: 50%; margin-right: 10px; border: 1px solid #ff4b4b; object-fit: cover; }}
        .mana-status {{ font-size: 0.8rem; color: #ff4b4b; font-weight: bold; margin-bottom: 10px; }}
        
        /* ヘッダーのデーモン画像 */
        .header-container {{
            display: flex; align-items: center; background: rgba(255, 75, 75, 0.1);
            padding: 15px; border-radius: 15px; margin-bottom: 20px; border: 1px solid #ff4b4b;
        }}
        .header-img {{ width: 80px; height: 80px; border-radius: 10px; margin-right: 20px; object-fit: cover; border: 2px solid #ff4b4b; }}
        </style>
    """, unsafe_allow_html=True)

    # --- 🔑 API設定 ---
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("APIキーが見つからぬ！")
        return
    genai.configure(api_key=api_key)

    # --- 🔮 魔力（リミット）管理 ---
    if "mana_saving_mode" not in st.session_state:
        st.session_state.mana_saving_mode = False

    try:
        if st.session_state.mana_saving_mode:
            model = genai.GenerativeModel('gemini-3-flash-preview')
            mana_text = "⚠️ 魔力枯渇につき『節約詠唱』中（検索不可）"
        else:
            model = genai.GenerativeModel(
                model_name='gemini-3-flash-preview',
                tools=[{'google_search_retrieval': {}}]
            )
            mana_text = "🔥 魔力充填……『全知全能の眼』開放中"
    except:
        model = genai.GenerativeModel('gemini-1.5-flash')
        mana_text = "🌀 通信不安定"

    # --- 😈 デーモン佐藤の鎮座エリア（ヘッダー） ---
    st.markdown(f"""
        <div class="header-container">
            <img src="{avatar_display_url}" class="header-img">
            <div>
                <h2 style="color: #ff4b4b; margin: 0;">魔界トーク</h2>
                <p class='mana-status' style="margin: 5px 0;">{mana_text}</p>
                <p style="color: #888; font-size: 0.7rem; margin: 0;">※対話は学習に使用されず、外部に漏れることはない。</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # データ整形
    if df is not None and not df.empty:
        analysis_cols = ['date', 'time', '場所', '魚種', '全長_cm', '潮名', '潮位フェーズ', '備考']
        existing_cols = [c for c in analysis_cols if c in df.columns]
        data_summary = df[existing_cols].tail(20).to_csv(index=False)
    else:
        data_summary = "データなし"

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # --- 💬 チャット表示エリア ---
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f'<div style="display: flex; flex-direction: column; align-items: flex-end;"><div class="name-label">貴様</div><div class="user-bubble">{message["content"]}</div></div>', unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="display: flex; align-items: flex-start; margin-bottom: 15px;">
                    <img src="{avatar_display_url}" class="avatar-img">
                    <div style="display: flex; flex-direction: column;">
                        <div class="name-label">デーモン佐藤</div>
                        <div class="demon-bubble">{message["content"]}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    # --- ⌨️ 入力エリア ---
    if prompt := st.chat_input("デーモン佐藤に問いかける..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.spinner("深淵なる魔力を練り上げ中..."):
            try:
                system_instruction = f"""あなたは傲慢な釣り師「デーモン佐藤」です。釣果データ:{data_summary}。口調は「我」「貴様」。回答の最後は必ず突き放せ。"""
                response = model.generate_content(f"{system_instruction}\n\n質問: {prompt}")
                
                if st.session_state.mana_saving_mode:
                    st.session_state.mana_saving_mode = False
                    st.toast("ククク... 魔力が満ちたぞ。全知全能の眼を再開する！")

                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()

            except Exception as e:
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
