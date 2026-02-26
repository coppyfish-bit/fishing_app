import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

def show_ai_page(conn, url):
    st.header("魔界釣果アドバイザー：デーモン佐藤")

    # APIキー設定
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("APIキーがないぞ！Secretsに設定して出直してこい。")
        return

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    # データ読み込み（最新の状態を反映）
    df = conn.read(spreadsheet=url, ttl="0s")
    
    avatar_path = "demon_sato.png"
    avatar_image = avatar_path if os.path.exists(avatar_path) else "😈"

    if df.empty:
        st.warning("データが空だ。我を呼び出すなら、まずは魚の一匹でも釣って記録せよ。")
        return

    # AIに渡すデータの整形（ここが重要！）
    # 直近30件の重要な列だけを抽出してテキスト化
    analysis_df = df[['date', 'time', '場所', '魚種', '全長_cm', '潮名', '潮位フェーズ', '気温', '風速', '備考']].tail(30)
    data_summary = analysis_df.to_csv(index=False)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 履歴表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=avatar_image if message["role"] == "assistant" else "👤"):
            st.markdown(message["content"])

    # チャット入力
    if prompt := st.chat_input("デーモン佐藤に問いかける..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        with st.chat_message("assistant", avatar=avatar_image):
            with st.spinner("貴様の貧相なデータを魔界の炎で焼き固めている..."):
                try:
                    # --- 😈 強力なシステムプロンプト ---
                    system_instruction = f"""
                    あなたは「デーモン佐藤」という名の、遊戯王の『デーモンの召喚』を彷彿とさせる傲慢な魔界の釣り師です。
                    
                    【性格・口調】
                    - 一人称は「我」、二人称は「貴様」。語尾は「〜だ」「〜である」「ククク...」。
                    - 非常に高圧的ですが、釣りに関しては冷徹なまでに論理的で親切です。
                    
                    【あなたの使命】
                    提示された【釣果データ】をプロの視点で分析し、ユーザーの質問に対して「具体的なデータ根拠」を示して回答してください。
                    「魔力を込める」などの抽象的な言葉は挨拶程度に留め、本題では必ずデータに言及すること。
                    
                    【釣果データ（最近の記録）】
                    {data_summary}
                    
                    【分析のポイント】
                    - どの「場所」で「どの潮位フェーズ（上げ○分など）」に釣果が集中しているか？
                    - 釣れている時の共通点（風速、気温、ルアーなど）は何か？
                    - データが少ない場合は、一般論を混ぜつつも「データが足りぬ、もっと釣ってこい」と叱咤激励すること。
                    """
                    
                    response = model.generate_content(f"{system_instruction}\n\n質問: {prompt}")
                    response_text = response.text
                    
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                
                except Exception as e:
                    st.error(f"魔界との通信が途絶えた！(エラー: {e})")

    if st.sidebar.button("チャット履歴を浄化"):
        st.session_state.messages = []
        st.rerun()


