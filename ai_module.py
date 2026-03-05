import streamlit as st
import google.generativeai as genai
import pandas as pd

def show_ai_page(conn, url, df):
    # --- 1. スタイル設定（吹き出しとヘッダーの装飾） ---
    st.markdown("""
        <style>
        /* デーモン佐藤（Assistant）の吹き出し：黒背景に赤枠 */
        [data-testid="stChatMessageAssistant"] {
            background-color: #1a1c23;
            color: #eeeeee;
            border: 2px solid #ff4b4b;
            border-radius: 15px;
        }
        /* ユーザーの吹き出し：深緑 */
        [data-testid="stChatMessageUser"] {
            background-color: #004a33;
            color: white;
            border-radius: 15px;
        }
        /* ヘッダーエリアの調整 */
        .ai-header-container {
            text-align: center;
            padding: 20px;
            background: linear-gradient(180deg, #330000 0%, #0e1117 100%);
            border-radius: 15px;
            border-bottom: 2px solid #ff4b4b;
            margin-bottom: 30px;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. デーモン佐藤の肖像（ヘッダー） ---
    AI_ICON = "damon_sato.png"
    USER_ICON = "👤"

    # 画面上部に対話相手としてのアイコンを表示
    header_col1, header_col2, header_col3 = st.columns([1, 2, 1])
    with header_col2:
        st.markdown('<div class="ai-header-container">', unsafe_allow_html=True)
        try:
            st.image(AI_ICON, width=150)
        except:
            st.warning("⚠️ damon_sato.png が見つからんぞ、佐藤。")
        st.markdown("""
            <h2 style="color: #ff4b4b; margin-bottom: 0;">😈 デーモン佐藤</h2>
            <p style="color: #888; font-style: italic;">「深淵のデータから貴様の未熟さを暴いてやろう...」</p>
            </div>
        """, unsafe_allow_html=True)

    # API設定
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("APIキーが未設定だ。")
        return
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-3-flash') # 最新モデル

    # 履歴管理
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 履歴表示（ここでも吹き出しの横にアイコンを出す）
    for message in st.session_state.messages:
        avatar = AI_ICON if message["role"] == "assistant" else USER_ICON
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # --- 3. 分析データの事前準備 ---
    if not df.empty:
        # 場所ごとの統計
        place_stats = df.groupby('場所').agg({
            '全長_cm': ['max', 'mean', 'count'],
            '潮位_cm': 'mean',
            '潮位フェーズ': lambda x: x.mode()[0] if not x.empty else "不明"
        }).reset_index()
        place_stats.columns = ['場所', '最大', '平均', '数', '潮位', 'フェーズ']
        place_summary = place_stats.to_csv(index=False)
        # 最大魚の情報
        max_row = df.loc[df['全長_cm'].idxmax()]
        max_info = f"場所:{max_row['場所']}, {max_row['全長_cm']}cm, 潮位:{max_row['潮位_cm']}cm, フェーズ:{max_row['潮位フェーズ']}"
    else:
        place_summary = "データなし"
        max_info = "なし"

    # --- 4. チャット入力 ---
    if prompt := st.chat_input("場所ごとの傾向を分析せよ..."):
        # ユーザー発言
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=USER_ICON):
            st.markdown(prompt)

        # デーモン佐藤の回答
        with st.chat_message("assistant", avatar=AI_ICON):
            full_prompt = f"""
            貴様は釣り界の魔王「デーモン佐藤」だ。以下の全データを精査し、特に【場所ごとの差異】に注目して分析せよ。
            【全場所統計】\n{place_summary}
            【最大魚記録】\n{max_info}
            【ユーザーの問い】\n{prompt}

            【解析指令】
            1. 特定の場所名が出たら、その場所の成功条件をデータから導き出せ。
            2. どの場所が「大物狙い」で、どの場所が「数釣り」に向くか判定しろ。
            3. 回答は常に傲慢かつ論理的、最後はユーモアを交えて突き放せ！
            """
            
            try:
                response = model.generate_content(full_prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"深淵との通信エラーだ... {e}")
