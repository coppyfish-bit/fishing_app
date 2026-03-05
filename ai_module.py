import streamlit as st
import google.generativeai as genai
import pandas as pd

def show_ai_page(conn, url, df):
    # --- 1. スタイル設定（LINE風・魔界カスタム） ---
    st.markdown("""
        <style>
        /* メッセージ全体のフォントと背景 */
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
        /* プライバシーバナー */
        .privacy-banner {
            background-color: #121212;
            border-left: 5px solid #ff4b4b;
            padding: 15px;
            margin-bottom: 20px;
            font-size: 0.85rem;
            color: #ccc;
            line-height: 1.6;
        }
        .profile-name {
            font-size: 1.2rem;
            font-weight: bold;
            color: #ff4b4b;
            margin: 0;
        }
        </style>
    """, unsafe_allow_html=True)

    # アイコン設定（GitHub上のファイル名と一致させてください）
    AI_ICON = "demon_sato.png"
    USER_ICON = "👤"

    # --- 2. プロフィールヘッダー ---
    prof_col1, prof_col2 = st.columns([1, 3])
    with prof_col1:
        try:
            st.image(AI_ICON, use_container_width=True)
        except:
            st.write("😈") # 画像がない場合の予備
    with prof_col2:
        st.markdown('<p class="profile-name">😈 デーモン佐藤（深淵の釣り師）</p>', unsafe_allow_html=True)
        st.caption("「2.0の知能で貴様の未熟なデータを精査してやろう...」")
        
        # 🗑️ ログ消去ボタン
        if st.button("🗑️ 会話ログを消去"):
            st.session_state.messages = []
            st.rerun()

    # --- 3. プライバシーバナー ---
    st.markdown("""
        <div class="privacy-banner">
            🛡️ <b>深淵の守護（プライバシーポリシー）</b><br>
            貴様との会話内容はAIの学習に利用されず、釣果データが外部へ漏洩・共有されることもない。
            この対話は深淵（このセッション）の中にのみ留まる。安心せよ。
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # --- 4. Gemini設定（最新安定版 2.0 Flash） ---
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("APIキーが設定されてないぞ。Secretsを確認しろ。")
        return
    
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    # 404エラー回避のため、確実に存在する 2.0-flash を指定
    model = genai.GenerativeModel('gemini-2.0-flash')

    # メッセージ履歴の保持
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 履歴表示
    for message in st.session_state.messages:
        avatar = AI_ICON if message["role"] == "assistant" else USER_ICON
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # --- 5. AI用のデータ事前集計（API節約のため効率化） ---
    if not df.empty:
        # 場所ごとの統計（AIが読みやすい形に濃縮）
        place_stats = df.groupby('場所').agg({
            '全長_cm': ['max', 'mean', 'count'],
            '潮位_cm': 'mean',
            '潮位フェーズ': lambda x: x.mode()[0] if not x.empty else "不明"
        }).reset_index()
        place_stats.columns = ['場所', '最大', '平均', '数', '潮位', 'フェーズ']
        place_summary = place_stats.to_csv(index=False)
        
        # 全体最大魚の特定
        max_row = df.loc[df['全長_cm'].idxmax()]
        max_info = f"全体最大: {max_row['全長_cm']}cm (場所: {max_row['場所']}, 潮位: {max_row['潮位_cm']}cm, フェーズ: {max_row['潮位フェーズ']})"
    else:
        place_summary = "データなし"
        max_info = "記録なし"

    # --- 6. チャット入力 ---
    if prompt := st.chat_input("問いかけよ...（例：本渡瀬戸の傾向を教えろ）"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=USER_ICON):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar=AI_ICON):
            full_prompt = f"""
            貴様は釣り界の魔王「デーモン佐藤」だ。
            以下の貴様の全釣果データ（場所別統計）を精査し、質問に答えよ。
            
            【深淵の場所別統計】
            {place_summary}
            
            【最大魚の聖録】
            {max_info}
            
            【質問内容】
            {prompt}

            【解析指令】
            1. 特定の場所名が出た場合、その場所の成功条件（潮位やフェーズ）をデータから導き出せ。
            2. 場所の比較を求められたら、優劣をはっきりつけ、次に行くべき場所を指示しろ。
            3. 回答は常に傲慢かつ論理的、最後はユーモアを交えて突き放せ！
            """
            
            try:
                # 思考中を表示
                with st.spinner("深淵の底で思考中..."):
                    response = model.generate_content(full_prompt)
                    st.markdown(response.text)
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"魔界との通信が途絶えた...（エラー詳細: {e}）")


