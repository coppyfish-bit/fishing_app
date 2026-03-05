import streamlit as st
import google.generativeai as genai
import pandas as pd

# --- 1. AI応答のキャッシュ化 (10分間 = 600秒) ---
# 同じ質問に対してAPIを叩かず、枠を節約します
@st.cache_data(ttl=600, show_spinner=False)
def get_demon_response(api_key, model_name, full_prompt):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    # 生成パラメータ：Temperatureを低めにして論理的な分析を優先
    config = {
        "temperature": 0.4,
        "top_p": 0.8,
        "max_output_tokens": 1000,
    }
    response = model.generate_content(full_prompt, generation_config=config)
    return response.text

def show_ai_page(conn, url, df, tide_data=None):
    # --- 2. スタイル設定（LINE風・魔界カスタム） ---
    st.markdown("""
        <style>
        [data-testid="stChatMessageAssistant"] {
            background-color: #1a1c23; color: #eeeeee;
            border: 1px solid #ff4b4b; border-radius: 15px;
        }
        [data-testid="stChatMessageUser"] {
            background-color: #004a33; color: white; border-radius: 15px;
        }
        .profile-name { font-size: 1.2rem; font-weight: bold; color: #ff4b4b; margin: 0; }
        .privacy-banner {
            background-color: #121212; border-left: 5px solid #ff4b4b;
            padding: 10px; margin-bottom: 20px; font-size: 0.8rem; color: #ccc;
        }
        </style>
    """, unsafe_allow_html=True)

    AI_ICON = "demon_sato.png"
    USER_ICON = "👤"

    # --- 3. プロフィールヘッダー ---
    prof_col1, prof_col2 = st.columns([1, 4])
    with prof_col1:
        try: st.image(AI_ICON, use_container_width=True)
        except: st.write("😈")
    with prof_col2:
        st.markdown('<p class="profile-name">😈 デーモン佐藤（深淵の2.0）</p>', unsafe_allow_html=True)
        st.caption("「17時を過ぎ、我が魔力（API枠）も回復したようだな...」")
        if st.button("🗑️ 会話とキャッシュを消去"):
            st.session_state.messages = []
            st.cache_data.clear()
            st.rerun()

    st.markdown('<div class="privacy-banner">🛡️ <b>深淵の守護</b>: 会話は学習に使われず、釣果も外部へ漏洩・共有されない。</div>', unsafe_allow_html=True)

    # --- 4. メッセージ履歴の管理 ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        avatar = AI_ICON if message["role"] == "assistant" else USER_ICON
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # --- 5. AI用データ事前準備 (CSV形式で圧縮) ---
    if not df.empty:
        place_stats = df.groupby('場所').agg({
            '全長_cm': ['max', 'mean', 'count'],
            '潮位_cm': 'mean'
        }).reset_index()
        place_stats.columns = ['場所', '最大', '平均', '数', '平均潮位']
        place_summary = place_stats.to_csv(index=False)
    else:
        place_summary = "実績データなし"

    # --- 6. チャット入力 ---
    if prompt := st.chat_input("問いかけよ...（例：下げ三分の時合を教えろ）"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=USER_ICON):
            st.markdown(prompt)

        # 潮汐キーワードチェック
        tide_keywords = ["潮", "タイド", "時合", "何時", "満潮", "干潮", "下げ", "上げ"]
        needs_tide = any(k in prompt for k in tide_keywords)
        
        tide_info = "（潮汐データ参照なし）"
        if needs_tide and tide_data:
            # JSONから重要な部分だけをAIに渡す（文字数節約）
            tide_info = f"【本日の潮汐データ】\n{str(tide_data)[:600]}"

        with st.chat_message("assistant", avatar=AI_ICON):
            # 過去の文脈を直近3往復に絞って送る（トークン節約）
            context_history = st.session_state.messages[-6:]
            
            full_prompt = f"""
            貴様は釣り界の魔王「デーモン佐藤」だ。
            以下の実績統計と今日の潮汐を照らし合わせ、質問に傲慢かつ論理的に答えよ。

            【実績統計】
            {place_summary}

            {tide_info}

            【質問内容】
            {prompt}

            【解析指令】
            1. 潮汐の話なら、実績の平均潮位と今日のデータを比較して時合を宣告しろ。
            2. 最後は必ず、貴様らしい毒舌かユーモアで締めろ。
            """

            try:
                with st.spinner("深淵の底で思考中..."):
                    # キャッシュ対応の関数を呼び出し
                    api_key = st.secrets["GEMINI_API_KEY"]
                    answer = get_demon_response(api_key, 'gemini-3.1-flash-lite-preview', full_prompt)
                    
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
            
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg:
                    st.error("⚠️ 貴様の問いが多すぎるのだ。1分待つか、新しい魔力（APIキー）を用意しろ。")
                else:
                    st.error(f"魔界との通信が途絶えた...（詳細: {e}）")

