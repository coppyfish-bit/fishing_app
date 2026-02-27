import streamlit as st
import pandas as pd
import google.generativeai as genai
import base64

# 画像をBase64に変換
def get_image_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    except:
        return "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"

def show_ai_page(conn, url, df, md=None):
    avatar_path = "demon_sato.png"
    avatar_display_url = get_image_as_base64(avatar_path) if os.path.exists(avatar_path) else "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"

    # --- CSS ---
    st.markdown(f"""
        <style>
        .stApp {{ background-color: #0e1117; }}
        .user-bubble {{ align-self: flex-end; background-color: #0084ff; color: white; padding: 10px 15px; border-radius: 18px 18px 2px 18px; max-width: 75%; margin-bottom: 10px; }}
        .demon-bubble {{ align-self: flex-start; background-color: #262730; color: #e0e0e0; padding: 10px 15px; border-radius: 18px 18px 18px 2px; max-width: 80%; border-left: 4px solid #ff4b4b; margin-bottom: 10px; }}
        .avatar-img {{ width: 45px; height: 45px; border-radius: 50%; margin-right: 10px; border: 1px solid #ff4b4b; }}
        .header-container {{ display: flex; align-items: center; background: rgba(255, 75, 75, 0.1); padding: 10px; border-radius: 10px; border: 1px solid #ff4b4b; }}
        .header-img {{ width: 60px; height: 60px; border-radius: 10px; margin-right: 15px; border: 2px solid #ff4b4b; }}
        div.stButton > button:first-child {{ background-color: #ff4b4b; color: white; border-radius: 20px; width: 100%; border: none; height: 2.5em; }}
        </style>
    """, unsafe_allow_html=True)

    # --- 🔑 API設定 ---
    api_key = st.secrets.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    # 検索機能は使わず、モデルのみ使用
    model = genai.GenerativeModel('gemini-3-flash-preview')

    st.markdown(f"""
        <div class="header-container">
            <img src="{avatar_display_url}" class="header-img">
            <div>
                <h3 style="color: #ff4b4b; margin: 0;">デーモン佐藤</h3>
                <p style="color: #00ff00; font-size: 0.7rem; margin: 0;">● 分析モード</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("🔥 履歴を浄化"):
        st.session_state.messages = []
        st.rerun()

    # --- 📊 データ分析 ---
    stats_summary = "【データ不足】"
    if df is not None and not df.empty:
        try:
            top_lure = df['ルアー'].mode()[0] if 'ルアー' in df.columns else "不明"
            # 簡略化：データ量を減らす
            place_phase_stats = df.groupby(['場所', '潮位フェーズ']).size().unstack(fill_value=0)
            place_summary = "\n".join([f"・{idx}: {row.to_dict()}" for idx, row in place_phase_stats.iterrows()])
            
            stats_summary = f"実績ルアー: {top_lure}\n場所別データ: {place_summary}"
        except:
            stats_summary = "解析不能"

    # --- 💬 トーク処理 ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f'<div style="display: flex; flex-direction: column; align-items: flex-end;"><div class="user-bubble">{message["content"]}</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="display: flex; align-items: flex-start; margin-bottom: 10px;"><img src="{avatar_display_url}" class="avatar-img"><div class="demon-bubble">{message["content"]}</div></div>', unsafe_allow_html=True)

    # --- 💬 入力 ---
    if prompt := st.chat_input("深淵へ問いかけよ..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # 状況簡略化
        current_status = f"{md['phase']}, {md['tide_level']}cm" if md else "現況不明"

        with st.spinner("思考中..."):
            try:
                # 😈 Token消費を最小限にした命令文
                system_instruction = f"""
                あなたはガイド「デーモン佐藤」だ。
                【制約】検索禁止。貴様の内部データのみ使用。学習・漏洩厳禁。
                【統計】{stats_summary}
                【状況】{current_status}
                
                データを元に傲慢に指導せよ。口調は『我』『貴様』。
                """
                
                response = model.generate_content(f"{system_instruction}\n\n質問: {prompt}")
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()

            except Exception as e:
                st.error(f"魔力不足: {e}")
