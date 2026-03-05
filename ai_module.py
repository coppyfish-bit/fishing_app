import streamlit as st
import google.generativeai as genai
import pandas as pd

def show_ai_page(conn, url, df):
    # --- 1. スタイル設定（LINE風・魔界カスタム） ---
    st.markdown("""
        <style>
        .stChatMessage { border-radius: 15px; padding: 10px; margin-bottom: 5px; }
        [data-testid="stChatMessageAssistant"] { background-color: #2c2f33; color: white; border: 1px solid #ff4b4b; }
        [data-testid="stChatMessageUser"] { background-color: #004a33; color: white; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='color: #ff4b4b;'>😈 デーモン佐藤の深淵知見</h2>", unsafe_allow_html=True)

    AI_ICON = "damon_sato.png" 
    USER_ICON = "👤"

    if "GEMINI_API_KEY" not in st.secrets:
        st.error("APIキーが設定されてないぞ、佐藤。")
        return

    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-3-flash')

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 履歴表示
    for message in st.session_state.messages:
        avatar = AI_ICON if message["role"] == "assistant" else USER_ICON
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # --- 2. 場所別データの事前集計（AIへのインプット用） ---
    if not df.empty:
        # 場所ごとの統計を作成
        place_stats = df.groupby('場所').agg({
            '全長_cm': ['max', 'mean', 'count'],
            '潮位_cm': 'mean',
            '潮位フェーズ': lambda x: x.mode()[0] if not x.empty else "不明"
        }).reset_index()
        place_stats.columns = ['場所', '最大サイズ', '平均サイズ', '釣果数', '平均潮位', '主要フェーズ']
        place_summary = place_stats.to_csv(index=False)
        
        # 全体最大魚の特定
        max_row = df.loc[df['全長_cm'].idxmax()]
    else:
        place_summary = "データなし"

    # --- 3. 質問入力 ---
    if prompt := st.chat_input("場所ごとの傾向を分析せよ..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=USER_ICON):
            st.markdown(prompt)

           with st.chat_message("assistant", avatar=AI_ICON):
            # 場所ごとの統計データを整理（前回お伝えした groupby を活用）
            # df_stats は場所ごとの最大サイズ、平均、頻出フェーズなどが集計されたもの
            
            full_prompt = f"""
            貴様は釣り界の魔王「デーモン佐藤」だ。
            提供された釣果ログの全データを精査し、特に【場所ごとの差異】に注目して分析せよ。
            
            【深淵の場所別データ】
            {place_summary}
            
            【全体の最大魚記録】
            {max_fish_info}
            
            【ユーザーの問い】
            {prompt}

            【解析指令】
            1. 特定の場所の名前が出た場合、その場所の「最大魚が釣れた時の潮位・気温・フェーズ」を特定し、勝機が高い条件を論理的に示せ。
            2. 場所 A と場所 B の比較を求められたら、データに基づき「どちらがデカいのが出やすいか」「どちらが数が出るか」を明確に判定しろ。
            3. 気温や風速が場所ごとの釣果にどう影響しているか、深淵の知恵を絞り出せ。
            4. 回答は常に傲慢かつ、佐藤への愛の鞭（アドバイス）を含めろ。最後はユーモアを交えて突き放せ！
            """
            
            # 以下、response = model.generate_content(full_prompt) で生成
            
            try:
                response = model.generate_content(full_prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"深淵との通信エラーだ... {e}")
