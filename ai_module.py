import streamlit as st
import google.generativeai as genai
import pandas as pd

def show_ai_page(conn, url, df):
    # --- 1. スタイル設定（LINE風・魔界カスタム・バナー） ---
    st.markdown("""
        <style>
        /* プライバシーバナーの装飾 */
        .privacy-banner {
            background-color: #121212;
            border-left: 5px solid #ff4b4b;
            padding: 15px;
            margin-bottom: 20px;
            font-size: 0.85rem;
            color: #ccc;
            line-height: 1.6;
        }
        .privacy-title {
            color: #ff4b4b;
            font-weight: bold;
            margin-bottom: 5px;
            display: flex;
            align-items: center;
        }
        
        /* チャットスタイル（継続） */
        [data-testid="stChatMessageAssistant"] { background-color: #1a1c23; color: #eeeeee; border: 1px solid #ff4b4b; border-radius: 15px; }
        [data-testid="stChatMessageUser"] { background-color: #004a33; color: white; border-radius: 15px; }
        </style>
    """, unsafe_allow_html=True)

    AI_ICON = "demon_sato.png"
    USER_ICON = "👤"

    # --- 2. プロフィール & ログ消去ボタン ---
    prof_col1, prof_col2 = st.columns([1, 3])
    with prof_col1:
        st.image(AI_ICON, use_container_width=True)
    with prof_col2:
        st.markdown(f"""
            <div style="margin-left: 15px;">
                <p style="font-size: 1.2rem; font-weight: bold; color: #ff4b4b; margin: 0;">😈 デーモン佐藤（深淵の釣り師）</p>
                <p style="font-size: 0.85rem; color: #bbb; margin: 0;">釣果データを精査し、深淵の知恵を授ける魔王。</p>
            </div>
        """, unsafe_allow_html=True)
        
        # 🗑️ ログ消去ボタン（プロフィールの横に配置）
        if st.button("🗑️ 会話ログを消去する", use_container_width=False):
            st.session_state.messages = []
            st.rerun()

    # --- 3. プライバシーポリシー・バナー ---
    st.markdown("""
        <div class="privacy-banner">
            <div class="privacy-title">🛡️ 深淵の守護（プライバシーポリシー）</div>
            貴様との会話内容は、AIの学習（トレーニング）に使用されることは万に一つもない。
            また、入力された釣果データや座標が外部へ漏洩・共有されることも断じてない。<br>
            ここでの対話は深淵の中にのみ留まる。安心して問いかけるが良い。
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Gemini設定（Gemini 3 Flash）
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("APIキーが未設定だ。")
        return
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-3-flash')

    # メッセージ履歴の保持
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 履歴表示
    for message in st.session_state.messages:
        avatar = AI_ICON if message["role"] == "assistant" else USER_ICON
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # --- 4. 分析データの集計（全データ・場所別） ---
    if not df.empty:
        # 場所ごとの統計
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

    # --- 5. チャット入力 ---
    if prompt := st.chat_input("魔王に問いかけよ..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=USER_ICON):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar=AI_ICON):
            full_prompt = f"""
            貴様は釣り界の魔王「デーモン佐藤」だ。以下の全データを踏まえ、質問に答えよ。
            【場所別データ】\n{place_summary}
            【全体最大記録】\n{max_info}
            【質問】\n{prompt}

            【指令】
            ・場所ごとの成功法則や共通点をデータから導き出せ。
            ・佐藤へのアドバイスは傲慢だが正確に行え。最後は突き放すユーモアを。
            """
            
            try:
                response = model.generate_content(full_prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"深淵との通信エラーだ... {e}")
