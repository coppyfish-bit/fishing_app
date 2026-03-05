import streamlit as st
import google.generativeai as genai
import pandas as pd

def show_ai_page(conn, url, df):
    # --- 1. スタイル設定（LINE公式アカウント風） ---
    st.markdown("""
        <style>
        /* 吹き出し設定 */
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
        /* プロフィールエリア */
        .profile-container {
            display: flex;
            align-items: center;
            padding: 15px;
            background-color: #1a1c23;
            border-radius: 15px;
            border: 1px solid #333;
            margin-bottom: 25px;
        }
        .profile-text {
            margin-left: 15px;
        }
        .profile-name {
            font-size: 1.2rem;
            font-weight: bold;
            color: #ff4b4b;
            margin: 0;
        }
        .profile-bio {
            font-size: 0.85rem;
            color: #bbb;
            margin: 0;
        }
        </style>
    """, unsafe_allow_html=True)

    AI_ICON = "demon_sato.png"
    USER_ICON = "👤"

    # --- 2. 画面上部のプロフィール表示 ---
    # st.columnsで画像とテキストを並べる
    prof_col1, prof_col2 = st.columns([1, 3])
    with prof_col1:
        st.image(AI_ICON, use_container_width=True)
    with prof_col2:
        st.markdown(f"""
            <div class="profile-text">
                <p class="profile-name">😈 デーモン佐藤（深淵の釣り師）</p>
                <p class="profile-bio">
                    天草の海を統べる魔王。貴様の釣果データを精査し、
                    「いつ、どこで、なぜ釣れたのか」を冷酷に分析する。<br>
                    得意技：下げ三面の説教、爆風時のポイント選定
                </p>
            </div>
        """, unsafe_allow_html=True)
    
    st.divider() # 区切り線

    # Gemini設定（Gemini 3 Flash）
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("APIキーが未設定だぞ。")
        return
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-3-flash')

    # チャット履歴管理
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 履歴表示
    for message in st.session_state.messages:
        avatar = AI_ICON if message["role"] == "assistant" else USER_ICON
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # --- 3. 分析データの集計（場所別） ---
    if not df.empty:
        place_stats = df.groupby('場所').agg({
            '全長_cm': ['max', 'mean', 'count'],
            '潮位_cm': 'mean',
            '潮位フェーズ': lambda x: x.mode()[0] if not x.empty else "不明"
        }).reset_index()
        place_stats.columns = ['場所', '最大', '平均', '数', '潮位', 'フェーズ']
        place_summary = place_stats.to_csv(index=False)
        max_row = df.loc[df['全長_cm'].idxmax()]
        max_info = f"最大魚: {max_row['全長_cm']}cm ({max_row['場所']})"
    else:
        place_summary = "データなし"
        max_info = "記録なし"

    # --- 4. チャット入力 ---
    if prompt := st.chat_input("魔王に場所別の傾向を問いかけよ..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=USER_ICON):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar=AI_ICON):
            full_prompt = f"""
            貴様は釣り界の魔王「デーモン佐藤」だ。以下の場所別データと全データを踏まえ、質問に答えよ。
            【場所別データ】\n{place_summary}
            【全体最大記録】\n{max_info}
            【質問】\n{prompt}

            【指令】
            ・場所名が出たら、その場所の成功法則を論理的に解説しろ。
            ・佐藤へのアドバイスは傲慢だが正確に行え。最後は突き放すユーモアを。
            """
            
            try:
                response = model.generate_content(full_prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"深淵との通信エラーだ... {e}")
