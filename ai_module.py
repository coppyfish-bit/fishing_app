import streamlit as st
import google.generativeai as genai
import pandas as pd

# --- キャッシュ設定: 同じ質問には10分間(600s)APIを叩かない ---
@st.cache_data(ttl=600, show_spinner=False)
def get_ai_response(api_key, model_name, full_prompt):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(full_prompt)
    return response.text

def show_ai_page(conn, url, df):
    # --- 1. スタイル設定 ---
    st.markdown("""
        <style>
        [data-testid="stChatMessageAssistant"] {
            background-color: #1a1c23; color: #eeeeee;
            border: 1px solid #ff4b4b; border-radius: 15px;
        }
        [data-testid="stChatMessageUser"] {
            background-color: #004a33; color: white; border-radius: 15px;
        }
        .profile-name { font-size: 1.2rem; font-weight: bold; color: #ff4b4b; }
        </style>
    """, unsafe_allow_html=True)

    AI_ICON = "demon_sato.png"
    USER_ICON = "👤"

    # --- 2. プロフィールヘッダー ---
    prof_col1, prof_col2 = st.columns([1, 3])
    with prof_col1:
        try: st.image(AI_ICON, use_container_width=True)
        except: st.write("😈")
    with prof_col2:
        st.markdown('<p class="profile-name">😈 デーモン佐藤（深淵の2.0）</p>', unsafe_allow_html=True)
        if st.button("🗑️ 会話ログを消去"):
            st.session_state.messages = []
            st.cache_data.clear() # キャッシュもクリア
            st.rerun()

    st.divider()

    # --- 3. Gemini設定 ---
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("APIキーが設定されてないぞ。Secretsを確認しろ。")
        return

    # メッセージ履歴の保持
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 履歴表示
    for message in st.session_state.messages:
        avatar = AI_ICON if message["role"] == "assistant" else USER_ICON
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # --- 4. データ集計（ここもキャッシュの効果を高めるため濃縮） ---
    if not df.empty:
        place_stats = df.groupby('場所').agg({
            '全長_cm': ['max', 'mean', 'count'],
            '潮位_cm': 'mean',
            '潮位フェーズ': lambda x: x.mode()[0] if not x.empty else "不明"
        }).reset_index()
        place_stats.columns = ['場所', '最大', '平均', '数', '潮位', 'フェーズ']
        place_summary = place_stats.to_csv(index=False)
        max_row = df.loc[df['全長_cm'].idxmax()]
        max_info = f"全体最大: {max_row['全長_cm']}cm (場所: {max_row['場所']})"
    else:
        place_summary = "データなし"; max_info = "記録なし"

    # --- 5. チャット入力 ---
    if prompt := st.chat_input("問いかけよ..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=USER_ICON):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar=AI_ICON):
            full_prompt = f"""
            貴様は釣り界の魔王「デーモン佐藤」だ。データを見て傲慢に答えよ。
            【場所別統計】\n{place_summary}
            【最大魚】\n{max_info}
            【質問】\n{prompt}
            """
            
            try:
                with st.spinner("深淵の2.0が思考中..."):
                    # キャッシュ化された関数を呼び出し
                    answer = get_ai_response(st.secrets["GEMINI_API_KEY"], 'gemini-2.0-flash', full_prompt)
                    
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg:
                    st.error("⚠️ 貴様の問いが多すぎるのだ（API制限）。1分待つか、17時（リセット）まで待て。")
                else:
                    st.error(f"魔界との通信が途絶えた...（詳細: {e}）")
