import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import base64

# --- 🖼️ 画像をBase64に変換（Streamlit Cloud環境での絶対パス対応） ---
def get_image_as_base64(file_path):
    # ファイルの場所を絶対パスで特定
    current_dir = os.path.dirname(os.path.abspath(__file__))
    absolute_path = os.path.join(current_dir, file_path)
    
    if not os.path.exists(absolute_path):
        # 画像がない場合はフォールバック
        return "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"
    
    try:
        with open(absolute_path, "rb") as f:
            data = f.read()
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    except:
        return "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"

def show_ai_page(conn, url, df, md=None):
    # --- 🖼️ アイコン設定 ---
    avatar_path = "demon_sato.png"
    avatar_display_url = get_image_as_base64(avatar_path)

    # --- 🎨 CSS（LINE風UI & 効率化） ---
    st.markdown(f"""
        <style>
        .stApp {{ background-color: #0e1117; }}
        .user-bubble {{
            align-self: flex-end; background-color: #0084ff; color: white;
            padding: 10px 15px; border-radius: 18px 18px 2px 18px;
            max-width: 75%; font-size: 1rem; margin-bottom: 10px;
        }}
        .demon-bubble {{
            align-self: flex-start; background-color: #262730; color: #e0e0e0;
            padding: 10px 15px; border-radius: 18px 18px 18px 2px;
            max-width: 80%; font-size: 1rem; border-left: 4px solid #ff4b4b;
            margin-bottom: 10px;
        }}
        .avatar-img {{ width: 45px; height: 45px; border-radius: 50%; margin-right: 10px; object-fit: cover; border: 1px solid #ff4b4b; }}
        
        .header-container {{
            display: flex; align-items: center; background: rgba(255, 75, 75, 0.1);
            padding: 15px; border-radius: 15px; margin-bottom: 15px; border: 1px solid #ff4b4b;
        }}
        .header-img {{ width: 60px; height: 60px; border-radius: 10px; margin-right: 20px; object-fit: cover; border: 2px solid #ff4b4b; }}
        
        div.stButton > button:first-child {{
            background-color: #ff4b4b; color: white; border-radius: 20px;
            width: 100%; border: none; font-weight: bold; height: 2.5em;
        }}
        </style>
    """, unsafe_allow_html=True)

    # --- 🔑 API設定（検索機能は含まれない） ---
    api_key = st.secrets.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    # Gemini 3 Flash (軽量・高速版) を使用
    model = genai.GenerativeModel('gemini-3-flash-preview')

    # --- 😈 ヘッダー ---
    st.markdown(f"""
        <div class="header-container">
            <img src="{avatar_display_url}" class="header-img">
            <div>
                <h2 style="color: #ff4b4b; margin: 0; font-size: 1.2rem;">デーモン佐藤</h2>
                <p style="color: #00ff00; font-size: 0.7rem; margin: 0;">● 接続維持：軽量・知能優先モード</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("🔥 記憶を浄化"):
        st.session_state.messages = []
        st.rerun()

    # --- 📊 統計エンジン（トークン節約のため簡略化） ---
    stats_summary = "【データなし】"
    if df is not None and not df.empty:
        try:
            top_lure = df['ルアー'].mode()[0] if 'ルアー' in df.columns else "不明"
            if '場所' in df.columns and '潮位フェーズ' in df.columns:
                place_phase_stats = df.groupby(['場所', '潮位フェーズ']).size().unstack(fill_value=0)
                stats_summary = f"【貴様の傾向】ルアー: {top_lure}\n場所/フェーズ実績:\n{place_phase_stats.to_dict()}"
            else:
                stats_summary = f"全体実績数: {len(df)}件"
        except:
            stats_summary = "統計解析不能"

    # --- 💬 トーク履歴の表示 ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f'<div style="display: flex; flex-direction: column; align-items: flex-end;"><div class="user-bubble">{message["content"]}</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="display: flex; align-items: flex-start; margin-bottom: 10px;"><img src="{avatar_display_url}" class="avatar-img"><div class="demon-bubble">{message["content"]}</div></div>', unsafe_allow_html=True)

    # --- 💬 入力エリア ---
    if prompt := st.chat_input("問いかけよ..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # 現在の気象状況（存在する場合のみ）
        curr = f"{md['phase']}, {md['tide_level']}cm, {md['wind']}m" if md else "不明"

        with st.spinner("思考中..."):
            try:
                # 👿 プロンプトを極限まで軽量化し、検索機能を封印
                system_instruction = f"""
                あなたは天草の傲慢なプロガイド「デーモン佐藤」だ。
                【制約】
                ・Google検索等の外部ツール使用は一切禁止。
                ・提示された統計データと貴様の知識のみで回答せよ。
                ・提示データは「貴様（ユーザー）」の物であり「我」の物ではない。
                【統計】{stats_summary}
                【状況】{curr}
                
                データを元に傲慢かつ論理的に批評せよ。口調は『我』『貴様』。最後は「出直してこい！」で締めろ。
                """
                
                response = model.generate_content(f"{system_instruction}\n\n質問: {prompt}")
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()

            except Exception as e:
                st.error(f"魔界通信事故（429等）: {e}")
