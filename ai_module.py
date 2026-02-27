import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import base64

# --- 🖼️ 画像をBase64に変換（絶対パス対応） ---
def get_image_as_base64(file_path):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    absolute_path = os.path.join(current_dir, file_path)
    if not os.path.exists(absolute_path):
        return "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"
    try:
        with open(absolute_path, "rb") as f:
            data = f.read()
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    except:
        return "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"

def show_ai_page(conn, url, df, md=None):
    # --- 🖼️ アイコン設定 ---
    avatar_display_url = get_image_as_base64("demon_sato.png")

    # --- 🎨 CSS（軽量化版） ---
    st.markdown(f"""
        <style>
        .stApp {{ background-color: #0e1117; }}
        .user-bubble {{ align-self: flex-end; background-color: #0084ff; color: white; padding: 10px 15px; border-radius: 18px 18px 2px 18px; max-width: 75%; margin-bottom: 10px; }}
        .demon-bubble {{ align-self: flex-start; background-color: #262730; color: #e0e0e0; padding: 10px 15px; border-radius: 18px 18px 18px 2px; max-width: 80%; border-left: 4px solid #ff4b4b; margin-bottom: 10px; }}
        .avatar-img {{ width: 45px; height: 45px; border-radius: 50%; margin-right: 10px; object-fit: cover; border: 1px solid #ff4b4b; }}
        .header-container {{ display: flex; align-items: center; background: rgba(255, 75, 75, 0.1); padding: 15px; border-radius: 15px; margin-bottom: 15px; border: 1px solid #ff4b4b; }}
        .header-img {{ width: 60px; height: 60px; border-radius: 10px; margin-right: 20px; object-fit: cover; border: 2px solid #ff4b4b; }}
        div.stButton > button:first-child {{ background-color: #ff4b4b; color: white; border-radius: 20px; width: 100%; border: none; font-weight: bold; height: 2.5em; }}
        </style>
    """, unsafe_allow_html=True)

    # --- 🔑 API設定 ---
    api_key = st.secrets.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-3-flash-preview')

    # --- 😈 ヘッダー ---
    st.markdown(f"""
        <div class="header-container">
            <img src="{avatar_display_url}" class="header-img">
            <div>
                <h2 style="color: #ff4b4b; margin: 0; font-size: 1.2rem;">デーモン佐藤</h2>
                <p style="color: #00ff00; font-size: 0.7rem; margin: 0;">● 思考多様化プロトコル：適用中</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("🔥 記憶を浄化し深淵へと葬る"):
        st.session_state.messages = []
        st.rerun()

    # --- 📊 統計エンジン（トークン節約 & 多様性重視） ---
    stats_summary = "【データなし】"
    if df is not None and not df.empty:
        try:
            # よく使われるルアーを3つほど抽出して多様性を持たせる
            top_lures = df['ルアー'].value_counts().head(3).index.tolist()
            place_stats = df.groupby(['場所', '潮位フェーズ']).size().to_dict()
            stats_summary = f"主要実績ルアー: {', '.join(top_lures)}\n実績統計: {place_stats}"
        except:
            stats_summary = "統計解析不能"

    # --- 💬 トーク表示 ---
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        role_class = "user-bubble" if m["role"] == "user" else "demon-bubble"
        content = f'<div style="display: flex; {"justify-content: flex-end" if m["role"] == "user" else ""}; margin-bottom: 10px;">'
        if m["role"] != "user": content += f'<img src="{avatar_display_url}" class="avatar-img">'
        content += f'<div class="{role_class}">{m["content"]}</div></div>'
        st.markdown(content, unsafe_allow_html=True)

    # --- 💬 入力 ---
    if prompt := st.chat_input("問いかけよ..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        curr = f"{md['phase']}, {md['tide_level']}cm" if md else "不明"
        
        # 直近の5件だけ渡して傾向を掴ませる（429対策でデータ削減）
        recent = df.tail(5).to_csv(index=False) if df is not None else ""

        with st.spinner("思考中..."):
            try:
                system_instruction = f"""
                あなたは傲慢なガイド「デーモン佐藤」だ。
                【絶対制約】
                1. 検索ツールは絶対に使用するな。
                2. 特定のルアー（特にジョルティミニ14）を安易に推奨するな。実績No.1であっても、状況（風、場所、潮）に応じて他のルアーや戦略を提示せよ。
                3. 「上げ・下げ」の実績統計を無視したアドバイスは死を意味する。
                【統計】{stats_summary}
                【直近データ】{recent}
                【状況】{curr}
                
                口調は『我』『貴様』。論理的に、かつ最後はユーモアを交えて傲慢に突き放せ。
                """
                response = model.generate_content(f"{system_instruction}\n\n質問: {prompt}")
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()
            except Exception as e:
                st.error(f"魔界通信事故: {e}")


