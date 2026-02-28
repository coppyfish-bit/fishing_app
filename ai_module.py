
import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import base64
import time

# --- 🖼️ 画像をBase64に変換（アイコン用） ---
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

    # --- 🎨 CSS（UI装飾） ---
    st.markdown(f"""
        <style>
        .stApp {{ background-color: #0e1117; }}
        .user-bubble {{ align-self: flex-end; background-color: #0084ff; color: white; padding: 10px 15px; border-radius: 18px 18px 2px 18px; max-width: 75%; margin-bottom: 10px; }}
        .demon-bubble {{ align-self: flex-start; background-color: #262730; color: #e0e0e0; padding: 10px 15px; border-radius: 18px 18px 18px 2px; max-width: 80%; border-left: 4px solid #ff4b4b; margin-bottom: 10px; }}
        .avatar-img {{ width: 45px; height: 45px; border-radius: 50%; margin-right: 10px; object-fit: cover; border: 1px solid #ff4b4b; }}
        .privacy-banner {{ background-color: rgba(0, 212, 255, 0.1); padding: 12px; border-radius: 10px; border-left: 5px solid #00d4ff; margin-bottom: 15px; font-size: 0.85rem; color: #cccccc; }}
        .header-container {{ display: flex; align-items: center; background: rgba(255, 75, 75, 0.1); padding: 15px; border-radius: 15px; margin-bottom: 15px; border: 1px solid #ff4b4b; }}
        .header-img {{ width: 60px; height: 60px; border-radius: 10px; margin-right: 20px; object-fit: cover; border: 2px solid #ff4b4b; }}
        div.stButton > button:first-child {{ background-color: #ff4b4b; color: white; border-radius: 20px; width: 100%; border: none; font-weight: bold; height: 2.5em; }}
        </style>
    """, unsafe_allow_html=True)

    # --- 🛡️ プライバシーバナー（言及不要との指示により、視覚表示のみ） ---
    st.markdown("""
        <div class="privacy-banner">
            <strong style="color: #00d4ff;">🛡️ 魔界機密保持プロトコル：厳守モード</strong><br>
            外部への漏洩・AI学習への利用は完全に遮断されている。
        </div>
    """, unsafe_allow_html=True)

    # --- 😈 ヘッダー ---
    st.markdown(f"""
        <div class="header-container">
            <img src="{avatar_display_url}" class="header-img">
            <div>
                <h2 style="color: #ff4b4b; margin: 0; font-size: 1.2rem;">デーモン佐藤</h2>
                <p style="color: #00ff00; font-size: 0.7rem; margin: 0;">● 全知全能：二段構え解析プロトコル</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("🔥 記憶を浄化して深淵へ葬る"):
        st.session_state.messages = []
        st.rerun()

    # --- 📊 拡張魔導要約エンジンの生成 ---
    global_knowledge = "【データ不足】"
    if df is not None and not df.empty:
        try:
            # 最大魚記録
            max_row = df.loc[df['全長_cm'].idxmax()]
            # 気象平均
            avg_temp = df['気温'].mean() if '気温' in df.columns else 0
            # 風の傾向
            wind_fav = df['風向'].mode().tolist() if '風向' in df.columns else ["不明"]
            # 場所別最強パターン
            place_best = df.groupby('場所')['ルアー'].agg(lambda x: x.mode().head(1).tolist()).to_dict()

            global_knowledge = f"""
            ・最大記録: {max_row['全長_cm']}cm (場所:{max_row.get('場所')}, 潮:{max_row.get('潮位フェーズ')})
            ・勝利の風向: {wind_fav}
            ・理想気温: {avg_temp:.1f}℃
            ・場所別鉄板: {place_best}
            ・実績ルアー上位: {df['ルアー'].value_counts().head(3).index.tolist()}
            ・総戦績: {len(df)}件
            """
        except:
            global_knowledge = "魔導書の解析に失敗した"

    # --- 🔑 モデル設定 ---
    api_key = st.secrets.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    
    # モデルA: 検索機能付き
    model_A = genai.GenerativeModel(
        model_name='gemini-3-flash-preview',
        tools=[{"google_search_retrieval": {}}]
    )
    # モデルB: 内部データのみ（緊急用）
    model_B = genai.GenerativeModel(model_name='gemini-3-flash-preview')

    # --- 💬 トーク履歴表示 ---
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        role_class = "user-bubble" if m["role"] == "user" else "demon-bubble"
        content = f'<div style="display: flex; {"justify-content: flex-end" if m["role"] == "user" else ""}; margin-bottom: 10px;">'
        if m["role"] != "user": content += f'<img src="{avatar_display_url}" class="avatar-img">'
        content += f'<div class="{role_class}">{m["content"]}</div></div>'
        st.markdown(content, unsafe_allow_html=True)

    # --- 💬 入力エリア ---
    if prompt := st.chat_input("全記録を背負い、問いかけよ..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        curr = f"気温:{md['temp']}℃, 風:{md['wind_dir']} {md['wind']}m, 潮:{md['phase']}" if md else "不明"

        with st.spinner("深淵の叡智を絞り出し中..."):
            system_base = f"""
            あなたは天草の傲慢なプロガイド「デーモン佐藤」だ。
            口調は『我』『貴様』。論理的かつ傲慢に、最後はユーモアで突き放せ。
            【魔導書：貴様の全歴史】
            {global_knowledge}
            【掟】
            1. 特定ルアー（ジョルティミニ14等）に固執せず、魔導書の多様なデータを優先せよ。
            2. 検索は魔導書にない情報の補完のみに使い、429エラーを回避せよ。
            3. プライバシー保護の言及は不要（バナーで表示済）。
            """

            try:
                # 👿 第一試行（検索あり）
                response = model_A.generate_content(f"{system_base}\n\n状況:{curr}\n質問:{prompt}")
                answer = response.text
            except Exception as e:
                if "429" in str(e):
                    # 👿 第二試行（緊急バックダウン）
                    try:
                        emergency_sys = system_base + "\n【緊急：検索不可】我の知能のみで答えろ。"
                        response = model_B.generate_content(f"{emergency_sys}\n\n状況:{curr}\n質問:{prompt}")
                        answer = "（ククク……外界が騒がしいゆえ、我自身の叡智のみで答えてやる）\n\n" + response.text
                    except:
                        answer = "深淵の底が崩落した。時間を置いて問い直せ。"
                else:
                    answer = f"事故だ: {e}"

            st.session_state.messages.append({"role": "assistant", "content": answer})
            st.rerun()
