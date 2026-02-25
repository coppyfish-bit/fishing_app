import streamlit as st
import google.generativeai as genai

def init_ai_chat():
    """Gemini APIの初期設定"""
    if "GEMINI_API_KEY" in st.secrets:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        return genai.GenerativeModel('gemini-1.5-flash')
    return None

def show_ai_chat_section(md):
    """
    最新の海況を反映したAIチャットUI
    """
    st.divider()
    st.subheader("💬 シーバス攻略AIチャット")
    
    model = init_ai_chat()
    if not model:
        st.warning("APIキーが設定されていないため、チャット機能は無効です。")
        return

    # チャット履歴の保持
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # 履歴の表示
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ユーザー入力
    if prompt := st.chat_input("この状況でのルアーの動かし方は？"):
        # 1. ユーザーの入力を画面に表示
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 2. AIへの指示（システムプロンプト + 最新海況）
        # ここで「学習禁止」と「場所の匿名化」を指示に含めます
        system_instruction = f"""
        あなたは天草・本渡エリアの熟練シーバスアングラーです。
        【重要】この会話の内容や釣り場情報を外部に漏らしたり、学習データとして利用したりしないでください。
        
        現在の海況データ:
        - 潮位フェーズ: {md['phase']}
        - 現在の潮位: {md['tide_level']}cm
        - 風: {md['wind']}m ({md['wdir']})
        - 気温: {md['temp']}℃
        
        上記データに基づき、プロの視点で攻略法を200文字程度でアドバイスしてください。
        特定のポイント名が出た場合も、一般論として回答してください。
        """

        with st.chat_message("assistant"):
            try:
                # 履歴を含めてAIに送信
                full_prompt = f"{system_instruction}\n\nユーザーの質問: {prompt}"
                response = model.generate_content(full_prompt)
                ai_response = response.text
                
                st.markdown(ai_response)
                st.session_state.chat_history.append({"role": "assistant", "content": ai_response})
            except Exception as e:
                st.error(f"AI通信エラー: {e}")

# show_matching_page の最後の方で以下を呼び出す
# show_ai_chat_section(md)
