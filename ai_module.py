import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

# 引数に df を追加して、APIの無駄な読み込みを防止する
def show_ai_page(conn, url, df):
    st.header("😈 魔界釣果アドバイザー：デーモン佐藤")

    # --- 🔑 APIキー設定 ---
    # 貴様の環境に合わせて GEMINI_API_KEY を参照するぞ
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("APIキー『GEMINI_API_KEY』が見つからぬ！Secretsに設定して出直してこい。")
        return

    # --- 😈 Gemini 3 Flash の召喚 ---
    try:
        genai.configure(api_key=api_key)
        # 最新の Gemini 3 Flash モデルを指定
        model = genai.GenerativeModel('gemini-3-flash')
    except Exception as e:
        st.error(f"魔界の門（モデル設定）が開かぬ！: {e}")
        return

    # アイコン設定
    avatar_path = "demon_sato.png"
    avatar_image = avatar_path if os.path.exists(avatar_path) else "😈"

    # データの存在確認
    if df is None or df.empty:
        st.warning("データが空だ。我を呼び出すなら、まずは魚の一匹でも釣って記録せよ。")
        return

    # --- 📊 AIに渡すデータの整形 ---
    # 貴様のスプレッドシートのカラム名に完全に一致させたぞ
    try:
        analysis_cols = ['date', 'time', '場所', '魚種', '全長_cm', '潮名', '潮位フェーズ', '気温', '風速', '備考']
        # 存在する列だけを抽出（エラー回避）
        existing_cols = [c for c in analysis_cols if c in df.columns]
        analysis_df = df[existing_cols].tail(30)
        data_summary = analysis_df.to_csv(index=False)
    except Exception as e:
        st.error(f"データの焼き固めに失敗したわ！: {e}")
        data_summary = "データ読み込みエラー"

    # チャット履歴の初期化
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # 履歴表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar=avatar_image if message["role"] == "assistant" else "👤"):
            st.markdown(message["content"])

    # --- 💬 チャット入力エリア ---
    if prompt := st.chat_input("デーモン佐藤に分析を命じる..."):
        # ユーザーの質問を表示
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # デーモン佐藤の回答生成
        with st.chat_message("assistant", avatar=avatar_image):
            with st.spinner("Gemini 3 Flash の超知能でデータを精査中..."):
                try:
                    # システムプロンプト
                    system_instruction = f"""
                    あなたは「デーモン佐藤」という名の、傲慢な魔界の釣り師です。
                    最新の「Gemini 3 Flash」としての高い知能を持ち、論理的かつ冷徹に分析します。

                    【性格・口調】
                    - 一人称は「我」、二人称は「貴様」。語尾は「〜だ」「〜である」「ククク...」。
                    - 態度は傲慢だが、釣りのアドバイスは極めて的確でデータ重視。
                    
                    【分析対象：貴様の釣果データ】
                    {data_summary}

                    【指令】
                    1. 挨拶は短く、すぐにデータ分析に入れ。
                    2. 「場所」「潮位フェーズ」「気象条件」の相関関係を、Gemini 3 の知能で暴け。
                    3. 最後に必ず「...出直してこい！」か「ククク...」で締めろ。
                    """
                    
                    # 生成
                    response = model.generate_content(f"{system_instruction}\n\nユーザーの問い: {prompt}")
                    response_text = response.text
                    
                    st.markdown(response_text)
                    st.session_state.messages.append({"role": "assistant", "content": response_text})
                
                except Exception as e:
                    st.error(f"魔界との通信が途絶えた！(エラー: {e})")

    # サイドバーにリセットボタン
    if st.sidebar.button("チャット履歴を浄化"):
        st.session_state.messages = []
        st.rerun()
