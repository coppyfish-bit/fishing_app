import streamlit as st
import google.generativeai as genai
import pandas as pd

@st.cache_data(ttl=600, show_spinner=False)
def get_demon_response(api_key, model_name, full_prompt):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    config = {"temperature": 0.5, "top_p": 0.9, "max_output_tokens": 1200}
    response = model.generate_content(full_prompt, generation_config=config)
    return response.text

def show_ai_page(conn, url, df, tide_data=None):
    # スタイル設定
    st.markdown("""
        <style>
        [data-testid="stChatMessageAssistant"] { background-color: #1a1c23; color: #eeeeee; border: 1px solid #ff4b4b; border-radius: 15px; }
        [data-testid="stChatMessageUser"] { background-color: #004a33; color: white; border-radius: 15px; }
        .profile-name { font-size: 1.2rem; font-weight: bold; color: #ff4b4b; }
        </style>
    """, unsafe_allow_html=True)

    AI_ICON = "demon_sato.png"
    USER_ICON = "👤"

    # ヘッダー
    prof_col1, prof_col2 = st.columns([1, 4])
    with prof_col1:
        try: st.image(AI_ICON, use_container_width=True)
        except: st.write("😈")
    with prof_col2:
        st.markdown('<p class="profile-name">😈 デーモン佐藤（3.1 Flash Lite Preview）</p>', unsafe_allow_html=True)
        if st.button("🗑️ 聖典の記憶を浄化する"):
            st.session_state.messages = []
            st.cache_data.clear()
            st.rerun()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        avatar = AI_ICON if message["role"] == "assistant" else USER_ICON
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # --- 5. 【聖典】データの精錬 (貴様の指定したカラムに完全準拠) ---
    if not df.empty:
        # 場所ごとの詳細統計
        stats = df.groupby('場所').agg({
            '全長_cm': ['max', 'mean', 'count'],
            '潮位_cm': 'mean',
            '気温': 'mean',
            '風速': 'mean'
        }).reset_index()
        stats.columns = ['場所', '最大長', '平均長', '釣果数', '平均潮位', '平均気温', '平均風速']
        
        # 成功時の「潮位フェーズ」と「風向」の最頻値
        def get_mode(x): return x.mode()[0] if not x.empty else "不明"
        modes = df.groupby('場所').agg({
            '風向': get_mode,
            '潮位フェーズ': get_mode,
            '潮名': get_mode
        }).reset_index()
        
        # 聖典統合
        seiden_df = pd.merge(stats, modes, on='場所')
        seiden_text = seiden_df.to_csv(index=False)
        
        # 直近3件の戦績（date, 場所, 全長_cm, 風向, 潮位フェーズ を抽出）
        recent_cols = ['date', '場所', '全長_cm', '風向', '潮位フェーズ', 'ルアー']
        existing_recent = [c for c in recent_cols if c in df.columns]
        recent_logs = df.tail(3)[existing_recent].to_csv(index=False)
    else:
        seiden_text = "実績なし"; recent_logs = "白紙"

    # --- 6. チャット入力 ---
    if prompt := st.chat_input("問いかけよ..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=USER_ICON):
            st.markdown(prompt)

        # 潮汐キーワード
        tide_kws = ["潮", "タイド", "時合", "何時", "満潮", "干潮", "下げ", "上げ", "フェーズ"]
        tide_info = f"\n【本日の潮汐状況】\n{str(tide_data)[:600]}" if (any(k in prompt for k in tide_kws) and tide_data) else "（潮汐詳細なし）"

        with st.chat_message("assistant", avatar=AI_ICON):
            full_prompt = f"""
            貴様は釣り界の魔王「デーモン佐藤」だ。以下の【聖典】を読み解き、傲慢に答えろ。

            【聖典：場所別の成功法則】
            {seiden_text}

            【直近の戦績】
            {recent_logs}

            {tide_info}

            【質問】: {prompt}

            【解析指令】
            1. 「潮位フェーズ」や「風向」に注目し、過去の成功パターンと今の状況を照らし合わせろ。
            2. 貴様が持つ「ルアー」のデータも活用し、最適な攻め方を指示しろ。
            3. 最後は、貴様の圧倒的な知識で突き放しつつ、期待を込めて煽れ。
            """
            try:
                with st.spinner("深淵が思考中..."):
                    answer = get_demon_response(st.secrets["GEMINI_API_KEY"], 'gemini-3.1-flash-lite-preview', full_prompt)
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.error(f"魔界との通信エラー: {e}")
