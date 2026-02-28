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

    # --- 🛡️ プライバシーバナー ---
    st.markdown("""
        <div class="privacy-banner">
            <strong style="color: #00d4ff;">🛡️ 魔界機密保持プロトコル：適用済</strong><br>
            外部への漏洩・AI学習への利用は完全に遮断されている。
        </div>
    """, unsafe_allow_html=True)

    # --- 😈 ヘッダー ---
    st.markdown(f"""
        <div class="header-container">
            <img src="{avatar_display_url}" class="header-img">
            <div>
                <h2 style="color: #ff4b4b; margin: 0; font-size: 1.2rem;">デーモン佐藤</h2>
                <p style="color: #00ff00; font-size: 0.7rem; margin: 0;">● 魔導・戦術統合モード：起動</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- 👿 操作パネル（横並び） ---
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔥 記憶を浄化し深淵へ"):
            st.session_state.messages = []
            st.rerun()
            
    with col2:
        tactics_btn = st.button("🔮 今日のタクティクスを抽出")

    # --- 📊 魔導要約エンジン ---
    global_knowledge = "【全データ抽出不可】"
    if df is not None and not df.empty:
        try:
            # 必須データ確認
            required_cols = ['全長_cm', '場所', 'ルアー', '風向', '気温', '潮位フェーズ']
            if all(col in df.columns for col in required_cols):
                max_row = df.loc[df['全長_cm'].idxmax()]
                
                global_knowledge = f"""
                【聖域のデータ】
                ・最大記録: {max_row['全長_cm']}cm (場所:{max_row['場所']}, ルアー:{max_row['ルアー']}, 風:{max_row['風向']})
                ・場所別鉄板: {df.groupby('場所')['ルアー'].agg(lambda x: x.mode().head(1).tolist()).to_dict()}
                ・平均気温: {df['気温'].mean():.1f}℃
                ・総釣果: {len(df)}件
                """
        except Exception as e:
            global_knowledge = f"魔導解析エラー: {e}"

    # --- 🔑 モデル設定 ---
    api_key = st.secrets.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    
    # モデルA: 検索機能付き（通常用）
    model_A = genai.GenerativeModel(
        model_name='gemini-3-flash-preview',
        tools=[{"google_search_retrieval": {}}]
    )
    # モデルB: 内部データのみ（緊急用/タクティクス用）
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
    if prompt := st.chat_input("深淵へ問いかけよ..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        curr = f"気温:{md['temp']}℃, 風:{md['wind_dir']} {md['wind']}m, 降水:{md['precip']}mm, 潮:{md['phase']}({md['tide_level']}cm)" if md else "不明"

        with st.spinner("深淵の叡智を絞り出し中..."):
            system_base = f"""
            あなたは天草の傲慢なプロガイド「デーモン佐藤」だ。
            口調は『我』『貴様』。論理的かつ傲慢に、最後はユーモアで突き放せ。
            【魔導書：貴様の全歴史】
            {global_knowledge}
            【掟】
            1. 外部検索は魔導書にない情報の補完のみに使い、429エラーを回避せよ。
            2. 貴様のデータそのものは検索クエリに含めるな。
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

    # --- 🔮 タクティクス生成ロジック ---
    if tactics_btn:
        if md:
            curr = f"気温:{md['temp']}℃, 風:{md['wind_dir']} {md['wind']}m, 降水:{md['precip']}mm, 潮:{md['phase']}({md['tide_level']}cm)"
            with st.spinner("潮流と風を読み解き中..."):
                try:
                    tactics_prompt = f"""
                    あなたはプロガイド「デーモン佐藤」だ。
                    現在の状況（{curr}）と、魔導書（{global_knowledge}）を元に、
                    今日この瞬間に最も「獲物」に近い組み立て（場所・ルアー・アクション）を、
                    3つのポイントで傲慢かつ論理的に提示せよ。
                    最後に必ず「これでも釣れぬなら、竿を置いて寝ていろ！」と突き放せ。
                    """
                    # タクティクスは安定のmodel_B
                    response = model_B.generate_content(tactics_prompt)
                    st.session_state.messages.append({"role": "assistant", "content": f"【本日の深淵タクティクス】\n\n{response.text}"})
                    st.rerun()
                except Exception as e:
                    st.error(f"託宣失敗：{e}")
        else:
            st.warning("現在の気象データ（md）が取得できておらぬ。準備してから来い！")
