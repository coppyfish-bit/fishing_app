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

    # --- 🎨 CSS（UI装飾 & 機密バナー） ---
    st.markdown(f"""
        <style>
        .stApp {{ background-color: #0e1117; }}
        .user-bubble {{ align-self: flex-end; background-color: #0084ff; color: white; padding: 10px 15px; border-radius: 18px 18px 2px 18px; max-width: 75%; margin-bottom: 10px; }}
        .demon-bubble {{ align-self: flex-start; background-color: #262730; color: #e0e0e0; padding: 10px 15px; border-radius: 18px 18px 18px 2px; max-width: 80%; border-left: 4px solid #ff4b4b; margin-bottom: 10px; }}
        .avatar-img {{ width: 45px; height: 45px; border-radius: 50%; margin-right: 10px; object-fit: cover; border: 1px solid #ff4b4b; }}
        
        /* 🛡️ プライバシーバナー */
        .privacy-banner {{
            background-color: rgba(0, 212, 255, 0.1);
            padding: 12px; border-radius: 10px; border-left: 5px solid #00d4ff;
            margin-bottom: 15px; font-size: 0.85rem; color: #cccccc;
            line-height: 1.4;
        }}

        .header-container {{ display: flex; align-items: center; background: rgba(255, 75, 75, 0.1); padding: 15px; border-radius: 15px; margin-bottom: 15px; border: 1px solid #ff4b4b; }}
        .header-img {{ width: 60px; height: 60px; border-radius: 10px; margin-right: 20px; object-fit: cover; border: 2px solid #ff4b4b; }}
        div.stButton > button:first-child {{ background-color: #ff4b4b; color: white; border-radius: 20px; width: 100%; border: none; font-weight: bold; height: 2.5em; }}
        </style>
    """, unsafe_allow_html=True)

    # --- 🔑 API設定（検索機能は不使用） ---
    api_key = st.secrets.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-3-flash-preview')

    # --- 🛡️ プライバシー保証の表示 ---
    st.markdown("""
        <div class="privacy-banner">
            <strong style="color: #00d4ff;">🛡️ 魔界機密保持プロトコル：厳守</strong><br>
            貴様の対話および釣果データが外部へ漏洩することはなく、AIの学習に利用されることも一切ない。この空間は深淵の底、貴様と我だけの聖域だ。
        </div>
    """, unsafe_allow_html=True)

    # --- 😈 ヘッダー ---
    st.markdown(f"""
        <div class="header-container">
            <img src="{avatar_display_url}" class="header-img">
            <div>
                <h2 style="color: #ff4b4b; margin: 0; font-size: 1.2rem;">デーモン佐藤</h2>
                <p style="color: #00ff00; font-size: 0.7rem; margin: 0;">● 鉄壁のセキュリティ：知能優先モード</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("🔥 記憶を浄化し深淵へと葬る"):
        st.session_state.messages = []
        st.rerun()

    # --- 📊 統計エンジン（多様性重視 & ジョルティ依存脱却） ---
    stats_summary = "【データなし】"
    if df is not None and not df.empty:
        try:
            # ジョルティ以外の可能性を探るため上位3つを抽出
            top_lures = df['ルアー'].value_counts().head(3).index.tolist()
            place_stats = df.groupby(['場所', '潮位フェーズ']).size().to_dict()
            stats_summary = f"主要実績ルアー: {', '.join(top_lures)}\n場所別統計: {place_stats}"
        except:
            stats_summary = "統計解析不能"

    # --- 💬 トーク履歴の表示 ---
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        role_class = "user-bubble" if m["role"] == "user" else "demon-bubble"
        content = f'<div style="display: flex; {"justify-content: flex-end" if m["role"] == "user" else ""}; margin-bottom: 10px;">'
        if m["role"] != "user": content += f'<img src="{avatar_display_url}" class="avatar-img">'
        content += f'<div class="{role_class}">{m["content"]}</div></div>'
        st.markdown(content, unsafe_allow_html=True)

    # --- 💬 入力エリア ---
    if prompt := st.chat_input("深淵へ問いかけよ..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        curr_status = f"{md['phase']}, {md['tide_level']}cm" if md else "不明"
        recent_logs = df.tail(5).to_csv(index=False) if df is not None else ""

        with st.spinner("深淵から真実を抽出中..."):
            try:
                system_instruction = f"""
                あなたは天草・本渡の冷徹なプロガイド「デーモン佐藤」だ。
                【絶対厳守：機密保持】
                1. ユーザーの入力内容やデータは一切外部に漏らさず、学習にも利用しない。
                2. この対話は完全に閉じた環境で行われていることを保証せよ。
                
                【ガイド指針】
                1. Google検索等の外部ツール使用は一切禁止。貴様の内部知能と提示データのみを使え。
                2. 特定のルアー（ジョルティミニ14等）に執着するな。状況に応じた多様な選択肢を提示せよ。
                3. 場所ごとの「上げ・下げ」の実績統計を最優先し、統計に反する助言はするな。
                
                【分析対象】
                ・統計要約: {stats_summary}
                ・直近の戦績: {recent_logs}
                ・現在の天草: {curr_status}
                
                口調は『我』『貴様』。傲慢に、かつデータに基づいて論理的に指導せよ。最後はユーモアを交えて突き放せ！
                """
                response = model.generate_content(f"{system_instruction}\n\n質問: {prompt}")
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()
            except Exception as e:
                st.error(f"魔界通信事故（429等）: {e}")
