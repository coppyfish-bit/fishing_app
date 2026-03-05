import streamlit as st
import google.generativeai as genai
import pandas as pd

def show_ai_page(conn, url, df):
    # --- スタイル設定 ---
    st.markdown("""
        <style>
        [data-testid="stChatMessageAssistant"] { background-color: #1a1c23; color: #eeeeee; border: 1px solid #ff4b4b; border-radius: 15px; }
        [data-testid="stChatMessageUser"] { background-color: #004a33; color: white; border-radius: 15px; }
        .privacy-banner { background-color: #121212; border-left: 5px solid #ff4b4b; padding: 15px; margin-bottom: 20px; font-size: 0.85rem; color: #ccc; }
        .profile-name { font-size: 1.2rem; font-weight: bold; color: #ff4b4b; margin: 0; }
        </style>
    """, unsafe_allow_html=True)

    AI_ICON = "demon_sato.png"
    USER_ICON = "👤"

    # --- プロフィール & ログ消去 ---
    prof_col1, prof_col2 = st.columns([1, 3])
    with prof_col1:
        st.image(AI_ICON, use_container_width=True)
    with prof_col2:
        st.markdown(f'<p class="profile-name">😈 デーモン佐藤（深淵の釣り師）</p>', unsafe_allow_html=True)
        st.caption("「貴様の未熟なデータを深淵の知恵で精査してやろう...」")
        if st.button("🗑️ 会話ログを消去"):
            st.session_state.messages = []
            st.rerun()

    # --- プライバシーバナー ---
    st.markdown("""
        <div class="privacy-banner">
            🛡️ <b>深淵の守護（プライバシーポリシー）</b><br>
            本会話はAI学習に利用されず、釣果データが外部へ漏洩・共有されることもない。安心せよ。
        </div>
    """, unsafe_allow_html=True)

    # Gemini設定
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-3-flash')

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 履歴表示
    for message in st.session_state.messages:
        avatar = AI_ICON if message["role"] == "assistant" else USER_ICON
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # --- データ精査 (場所別・最大魚) ---
    if not df.empty:
        # 場所ごとの統計
        place_stats = df.groupby('場所').agg({
            '全長_cm': ['max', 'mean', 'count'],
            '潮位_cm': 'mean',
            '潮位フェーズ': lambda x: x.mode()[0] if not x.empty else "不明"
        }).reset_index()
        place_stats.columns = ['場所', '最大', '平均', '数', '潮位', 'フェーズ']
        place_summary = place_stats.to_csv(index=False)
        # 全体最大魚
        max_row = df.loc[df['全長_cm'].idxmax()]
        max_info = f"全体最大: {max_row['全長_cm']}cm (場所: {max_row['場所']}, 潮位: {max_row['潮位_cm']}cm)"
    else:
        place_summary = "データなし"
        max_info = "なし"

    # --- チャット入力 ---
    if prompt := st.chat_input("問いかけよ..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=USER_ICON):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar=AI_ICON):
            full_prompt = f"""
            貴様は釣り界の魔王「デーモン佐藤」だ。
            以下の全データを踏まえ、佐藤（ユーザー）の質問に答えよ。
            【場所別データ】\n{place_summary}
            【最大魚記録】\n{max_info}
            【ユーザーの問い】\n{prompt}

            【指令】
            ・場所ごとの差異を論理的に分析し、次に釣るための条件を提示しろ。
            ・回答は傲慢だが正確に行い、最後はユーモアで突き放せ。
            """
            try:
                response = model.generate_content(full_prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"深淵との通信エラー：{e}")
