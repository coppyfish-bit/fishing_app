import streamlit as st
import google.generativeai as genai
import pandas as pd

def show_ai_page(conn, url, df):
    # --- 1. スタイル設定（LINE風＋魔界演出） ---
    st.markdown("""
        <style>
        .stChatMessage { border-radius: 15px; padding: 10px; margin-bottom: 5px; }
        [data-testid="stChatMessageAssistant"] { background-color: #2c2f33; color: white; border: 1px solid #ff4b4b; }
        [data-testid="stChatMessageUser"] { background-color: #004a33; color: white; }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='color: #ff4b4b;'>😈 デーモン佐藤の深淵知見</h2>", unsafe_allow_html=True)

    # アイコン設定
    AI_ICON = "damon_sato.png" 
    USER_ICON = "👤"

    # APIキー確認
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("APIキーが設定されてないぞ、佐藤。Secretsを確認しろ。")
        return

    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')

    # 履歴の初期化
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 履歴表示
    for message in st.session_state.messages:
        avatar = AI_ICON if message["role"] == "assistant" else USER_ICON
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # --- 2. 質問入力 ---
    if prompt := st.chat_input("最大魚が釣れた条件を分析せよ...など"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=USER_ICON):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar=AI_ICON):
            # --- 3. 分析用の全データ要約作成 ---
            # 全データから最大魚を特定
            max_fish_row = df.loc[df['全長_cm'].idxmax()] if not df.empty else None
            
            # 全体の統計（平均気温、よく釣れる潮位など）
            stats_summary = {
                "総釣果数": len(df),
                "最大サイズ": df['全長_cm'].max() if not df.empty else 0,
                "よく釣れる潮位範囲": f"{df['潮位_cm'].min()} - {df['潮位_cm'].max()} cm",
                "主なヒットフェーズ": df['潮位フェーズ'].mode()[0] if not df.empty else "不明"
            }

            # Geminiへの命令文（全データを背景として渡す）
            full_prompt = f"""
            貴様は釣り界の魔王「デーモン佐藤」だ。
            以下の貴様の釣果ログ全体（全データ）を精査し、質問に答えよ。
            
            【深淵の全統計】
            {stats_summary}
            
            【最大魚の記録】
            魚種: {max_fish_row['魚種'] if max_fish_row is not None else 'なし'}
            サイズ: {max_fish_row['全長_cm'] if max_fish_row is not None else '0'}cm
            日時: {max_fish_row['datetime'] if max_fish_row is not None else '不明'}
            条件: 気温{max_fish_row['気温']}度, 風速{max_fish_row['風速']}m, 潮位{max_fish_row['潮位_cm']}cm, フェーズ:{max_fish_row['潮位フェーズ']}
            
            【直近の釣果データ（CSV）】
            {df.tail(30).to_csv(index=False)}
            
            【ユーザーの問い】
            {prompt}

            【指示】
            ・最大魚が釣れた時の共通点や、気温・風速・潮位・フェーズの相関関係をプロの視点で分析しろ。
            ・「次に釣行すべき最高な条件」を論理的に、かつ魔王らしく傲慢に提示せよ。
            """
            
            try:
                response = model.generate_content(full_prompt)
                st.markdown(response.text)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
            except Exception as e:
                st.error(f"深淵との接続が不安定だ... ({e})")
