import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

def show_ai_page(conn, url, df):
    # --- 🎨 魔界のスタイリング（CSS） ---
    st.markdown("""
        <style>
        .demon-container {
            display: flex;
            align-items: flex-start;
            margin-bottom: 20px;
            padding: 15px;
            background: rgba(30, 38, 48, 0.7);
            border-left: 5px solid #ff4b4b;
            border-radius: 10px;
        }
        .demon-image {
            width: 80px;
            height: 80px;
            border-radius: 50%;
            border: 2px solid #ff4b4b;
            margin-right: 15px;
            box-shadow: 0 0 15px rgba(255, 75, 75, 0.4);
        }
        .demon-text {
            color: #e0e0e0;
            font-size: 1.1rem;
            font-style: italic;
        }
        /* チャット吹き出しのカスタマイズ */
        [data-testid="stChatMessage"] {
            background-color: #1e2630 !important;
            border-radius: 15px !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 🔑 API & Model 設定 ---
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("APIキーが見つからぬ！")
        return

    genai.configure(api_key=api_key)
    # 貴様が見つけた真の呪文！
    model = genai.GenerativeModel('gemini-3-flash-preview')

    # キャラクター画像の設定
    # demon_sato.png があれば使い、なければ絵文字で代用
    avatar_path = "demon_sato.png"
    has_image = os.path.exists(avatar_path)
    avatar_url = avatar_path if has_image else "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png" # 仮の魔界画像

    # --- 😈 デーモン佐藤の鎮座エリア ---
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image(avatar_url, width=100)
    with col2:
        st.markdown(f"""
            <div style="padding-top: 10px;">
                <h3 style="color: #ff4b4b; margin-bottom: 5px;">デーモン佐藤</h3>
                <p style="color: #888; font-size: 0.8rem; letter-spacing: 0.1rem;">MA-KAI FISHING ADVISOR (Gemini 3 Powered)</p>
                <p style="color: #666; font-size: 0.75rem;">※この対話データは学習に使用されず、外部に漏れることはない。安心せよ。</p>
                <p class="demon-text">「ククク... 貴様の秘密（データ）は我と貴様だけのものだ。何を聞きたい？」</p>
            </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # データの存在確認と整形
    if df is None or df.empty:
        st.warning("データが空だ。")
        return

    analysis_cols = ['date', 'time', '場所', '魚種', '全長_cm', '潮名', '潮位フェーズ', '気温', '風速', '備考']
    existing_cols = [c for c in analysis_cols if c in df.columns]
    data_summary = df[existing_cols].tail(30).to_csv(index=False)

    # セッション履歴
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # チャット履歴表示
    for message in st.session_state.messages:
        avatar = avatar_url if message["role"] == "assistant" else "👤"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # --- 💬 入力エリア ---
    if prompt := st.chat_input("デーモン佐藤に問いかける..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar=avatar_url):
            with st.spinner("深淵なる知能で計算中..."):
                try:
                    system_instruction = f"""
                    あなたは傲慢な魔界の釣り師「デーモン佐藤」です。
                    【釣果データ】: {data_summary}
                    【性格】: 傲慢、冷徹、データ至上主義。
                    【話し方】: 一人称は「我」、二人称は「貴様」。
                    分析は論理的に行い、最後は「出直してこい！」などで突き放せ。
                    """
                    response = model.generate_content(f"{system_instruction}\n\n質問: {prompt}")
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                except Exception as e:
                    st.error(f"魔界との通信失敗: {e}")

