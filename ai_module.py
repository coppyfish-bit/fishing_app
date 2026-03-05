import streamlit as st
import google.generativeai as genai
import pandas as pd

def show_ai_page(conn, url, df):
    # --- 1. スタイル設定（LINE風吹き出しカスタム） ---
    st.markdown("""
        <style>
        /* チャットエリア全体の背景 */
        .stApp { background-color: #0e1117; }
        
        /* 吹き出しの共通設定 */
        .stChatMessage { border-radius: 20px; padding: 15px; margin-bottom: 10px; max-width: 85%; }
        
        /* デーモン佐藤（Assistant）の吹き出し：黒背景に赤枠 */
        [data-testid="stChatMessageAssistant"] {
            background-color: #1a1c23;
            color: #eeeeee;
            border: 2px solid #ff4b4b;
            margin-right: auto;
        }
        
        /* ユーザーの吹き出し：深緑背景 */
        [data-testid="stChatMessageUser"] {
            background-color: #004a33;
            color: white;
            margin-left: auto;
            border: 1px solid #006b4a;
        }

        /* ヘッダー画像の設定 */
        .ai-header {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px;
            background: linear-gradient(180deg, #2c0000 0%, #0e1117 100%);
            border-radius: 20px;
            margin-bottom: 20px;
            border-bottom: 2px solid #ff4b4b;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. 常に表示されるデーモン佐藤の肖像 ---
    AI_ICON = "damon_sato.png"
    USER_ICON = "👤"

    st.markdown(f"""
        <div class="ai-header">
            <img src="app/static/{AI_ICON}" width="150" style="border-radius: 50%; border: 4px solid #ff4b4b; box-shadow: 0 0 20px #ff4b4b;">
            <h2 style="color: #ff4b4b; margin-top: 15px;">😈 デーモン佐藤の深淵知見</h2>
            <p style="color: #cccccc; font-style: italic;">「貴様の釣果、データごと飲み干してやろう...」</p>
        </div>
    """, unsafe_allow_html=True)

    # モデル・設定の準備
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("APIキーが設定されてないぞ、佐藤。")
        return

    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-3-flash') # Gemini 3 Flash を指定

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # チャット履歴表示
    for message in st.session_state.messages:
        avatar = AI_ICON if message["role"] == "assistant" else USER_ICON
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # --- 3. 分析データの準備 ---
    if not df.empty:
        place_stats = df.groupby('場所').agg({
            '全長_cm': ['max', 'mean', 'count'],
            '潮位_cm': 'mean',
            '潮位フェーズ': lambda x: x.mode()[0] if not x.empty else "不明"
        }).reset_index()
        place_stats.columns = ['場所', '最大', '平均', '数', '潮位', 'フェーズ']
        place_summary = place_stats.to_csv(index=False)
        max_row = df.loc[df['全長_cm'].idxmax()]
        max_fish_info = f"場所:{max_row['場所']}, {max_row['全長_cm']}cm, {max_row['潮位フェーズ']}"
    else:
        place_summary = "データなし"
        max_fish_info = "なし"

    # --- 4. チャット入力 ---
    if prompt := st.chat_input("深淵に問いかけよ...（例：本渡瀬戸の最大魚条件は？）"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=USER_ICON):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar=AI_ICON):
            full_prompt = f"""
            貴様は釣り界の魔王「デーモン佐藤」だ。以下の全データを精査し、特に【場所ごとの差異】に注目して分析せよ。
            【場所別データ】\n{place_summary}
            【全体最大魚】\n{max_fish_info}
            【ユーザーの問い】\n{prompt}

            【解析指令】
            1. 特定の場所名が出たら、その場所の成功条件をデータから導き出せ。
            2. 場所の比較を求められたら、優劣をはっきりつけろ。
            3. 回答は常に傲慢かつ論理的、最後はユーモアを交えて突き放せ！
            """
            
            try:
                response = model.generate_content(full_prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"深淵との通信エラーだ... {e}")
