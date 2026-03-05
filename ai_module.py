import streamlit as st
import google.generativeai as genai
import pandas as pd

# --- 1. AI応答のキャッシュ化 (10分間) ---
@st.cache_data(ttl=600, show_spinner=False)
def get_demon_response(api_key, model_name, full_prompt):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    config = {
        "temperature": 0.5, # 論理性を保ちつつ魔王の威厳を出す
        "top_p": 0.9,
        "max_output_tokens": 1200,
    }
    response = model.generate_content(full_prompt, generation_config=config)
    return response.text

def show_ai_page(conn, url, df, tide_data=None):
    # --- 2. スタイル設定（魔界カスタム） ---
    st.markdown("""
        <style>
        [data-testid="stChatMessageAssistant"] {
            background-color: #1a1c23; color: #eeeeee;
            border: 1px solid #ff4b4b; border-radius: 15px;
        }
        [data-testid="stChatMessageUser"] {
            background-color: #004a33; color: white; border-radius: 15px;
        }
        .profile-name { font-size: 1.2rem; font-weight: bold; color: #ff4b4b; }
        .privacy-banner {
            background-color: #121212; border-left: 5px solid #ff4b4b;
            padding: 10px; margin-bottom: 20px; font-size: 0.8rem; color: #ccc;
        }
        </style>
    """, unsafe_allow_html=True)

    AI_ICON = "demon_sato.png"
    USER_ICON = "👤"

    # --- 3. プロフィールヘッダー ---
    prof_col1, prof_col2 = st.columns([1, 4])
    with prof_col1:
        try: st.image(AI_ICON, use_container_width=True)
        except: st.write("😈")
    with prof_col2:
        st.markdown('<p class="profile-name">😈 デーモン佐藤（3.1 Flash Lite Preview）</p>', unsafe_allow_html=True)
        if st.button("🗑️ 聖典の記憶（キャッシュ）を浄化する"):
            st.session_state.messages = []
            st.cache_data.clear()
            st.rerun()

    st.markdown('<div class="privacy-banner">🛡️ <b>深淵の守護</b>: 貴様の釣果、風向、潮位データは学習に使われず、外部へも漏らさぬ。</div>', unsafe_allow_html=True)

    # --- 4. メッセージ履歴の管理 ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        avatar = AI_ICON if message["role"] == "assistant" else USER_ICON
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # --- 5. 【聖典】データの精錬（風向・潮位・気温の統合） ---
    if not df.empty:
        # 場所ごとの統計（気温、潮位、風速）
        stats = df.groupby('場所').agg({
            '全長_cm': ['max', 'mean', 'count'],
            '潮位_cm': 'mean',
            '気温': 'mean'
        }).reset_index()
        stats.columns = ['場所', '最大長', '平均長', '釣果数', '実績平均潮位', '実績平均気温']
        
        # 最も釣れている風向きの特定（最頻値）
        def get_best_wind(x):
            return x.mode()[0] if not x.empty else "不明"
        wind_fav = df.groupby('場所')['風向'].apply(get_best_wind).reset_index()
        wind_fav.columns = ['場所', '成功時の風向き']
        
        # 聖典として統合
        seiden_df = pd.merge(stats, wind_fav, on='場所')
        seiden_text = seiden_df.to_csv(index=False)
        
        # 直近の戦績（最新3件のリアルな状況）
        recent_logs = df.tail(3)[['日付', '場所', '全長_cm', '潮位_cm', '風向', '気温']].to_csv(index=False)
    else:
        seiden_text = "実績なし"; recent_logs = "白紙"

    # --- 6. チャット入力 ---
    if prompt := st.chat_input("深淵へ問いかけよ（例：北風だが、どこが釣れる？）"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar=USER_ICON):
            st.markdown(prompt)

        # 潮汐・風向キーワードの抽出
        tide_kws = ["潮", "タイド", "時合", "何時", "満潮", "干潮", "下げ", "上げ"]
        needs_tide = any(k in prompt for k in tide_kws)
        
        tide_info = "（潮汐データ参照なし）"
        if needs_tide and tide_data:
            tide_info = f"【本日の潮汐状況】\n{str(tide_data)[:600]}"

        with st.chat_message("assistant", avatar=AI_ICON):
            # トークン節約のため直近履歴を絞る
            context_history = st.session_state.messages[-4:]
            
            full_prompt = f"""
            貴様は釣り界の魔王「デーモン佐藤」だ。
            提供された【聖典】（過去の全実績データ）を元に、貴様の圧倒的知能で回答せよ。

            【聖典：場所別の成功法則（風向・潮位・気温）】
            {seiden_text}

            【直近の戦績】
            {recent_logs}

            {tide_info}

            【貴様への問い】
            {prompt}

            【魔王の解析指令】
            1. 「風向」に注目せよ。場所ごとの『成功時の風向き』と、今の状況（ユーザーが言えば）を照らし合わせろ。
            2. 「潮位」に注目せよ。実績平均潮位と、今日の潮汐データを比較し、突撃すべき時間を宣告しろ。
            3. 「気温」に注目せよ。過去に釣れた平均気温と今の乖離を指摘しろ。
            4. 回答は常に論理的かつ傲慢であれ。最後はユーモアを交えて突き放せ！
            """

            try:
                with st.spinner("深淵の3.1が思考中..."):
                    api_key = st.secrets["GEMINI_API_KEY"]
                    # 通信成功したモデル名を指定
                    answer = get_demon_response(api_key, 'gemini-3.1-flash-lite-preview', full_prompt)
                    
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
            except Exception as e:
                st.error(f"魔界との通信が途絶えた...（詳細: {e}）")
