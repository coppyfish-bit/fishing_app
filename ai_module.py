import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import base64

# 画像をBase64に変換（アイコン表示用）
def get_image_as_base64(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    except:
        return "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"

def show_ai_page(conn, url, df, md=None):
    # --- 🖼️ アイコン設定 ---
    avatar_path = "demon_sato.png"
    avatar_display_url = get_image_as_base64(avatar_path) if os.path.exists(avatar_path) else "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"

    # --- 🎨 CSS（LINE風UI & 装飾） ---
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
        
        .privacy-banner {{
            background-color: rgba(0, 212, 255, 0.1);
            padding: 10px; border-radius: 10px; border-left: 5px solid #00d4ff;
            margin-bottom: 15px; font-size: 0.8rem; color: #cccccc;
        }}

        .header-container {{
            display: flex; align-items: center; background: rgba(255, 75, 75, 0.1);
            padding: 15px; border-radius: 15px; margin-bottom: 15px; border: 1px solid #ff4b4b;
        }}
        .header-img {{ width: 80px; height: 80px; border-radius: 10px; margin-right: 20px; object-fit: cover; border: 2px solid #ff4b4b; }}
        
        div.stButton > button:first-child {{
            background-color: #ff4b4b; color: white; border-radius: 20px;
            width: 100%; border: none; font-weight: bold; height: 3em; margin-bottom: 20px;
        }}
        </style>
    """, unsafe_allow_html=True)

    # --- 🔑 API設定 ---
    api_key = st.secrets.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-3-flash-preview')

    # --- 🛡️ プライバシーバナー ---
    st.markdown("""
        <div class="privacy-banner">
            <strong style="color: #00d4ff;">🛡️ 魔界機密保持プロトコル：発動中</strong><br>
            対話および釣果データは外部に漏洩せず、AIの学習にも利用されぬ。深淵の底に封印中。
        </div>
    """, unsafe_allow_html=True)

    # --- 😈 ヘッダー ---
    st.markdown(f"""
        <div class="header-container">
            <img src="{avatar_display_url}" class="header-img">
            <div>
                <h2 style="color: #ff4b4b; margin: 0;">デーモン佐藤の召喚</h2>
                <p style="color: #00ff00; font-size: 0.8rem; margin: 5px 0;">● 安定接続：場所別・知能特化モード</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("🔥 記憶を浄化して深淵へ葬る"):
        st.session_state.messages = []
        st.rerun()

    # --- 📊 場所別・潮位フェーズ分析エンジンの実装 ---
    stats_summary = "【データ不足】"
    if df is not None and not df.empty:
        try:
            # 1. ルアー等の最頻値
            top_lure = df['ルアー'].mode()[0] if 'ルアー' in df.columns else "不明"
            
            # 2. 場所ごとの「上げ・下げ」クロス集計
            if '場所' in df.columns and '潮位フェーズ' in df.columns:
                place_phase_stats = df.groupby(['場所', '潮位フェーズ']).size().unstack(fill_value=0)
                place_summary = "\n".join([f"・{idx}: {row.to_dict()}" for idx, row in place_phase_stats.iterrows()])
            else:
                place_summary = "場所別フェーズデータ不足"

            # 3. 数値傾向
            avg_hit_tide = df['潮位_cm'].mean() if '潮位_cm' in df.columns else 0
            
            stats_summary = f"""
            【分析対象：貴様（ユーザー）の場所別・潮位実績】
            {place_summary}
            
            【全体傾向】
            ● 実績No.1ルアー: {top_lure}
            ● ヒット時平均潮位: {avg_hit_tide:.1f}cm
            ● 総データ件数: {len(df)} 件
            """
        except Exception as e:
            stats_summary = f"【統計解析エラー: {e}】"

    # --- 💬 トーク履歴 ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(f'<div style="display: flex; flex-direction: column; align-items: flex-end;"><div class="user-bubble">{message["content"]}</div></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="display: flex; align-items: flex-start; margin-bottom: 10px;"><img src="{avatar_display_url}" class="avatar-img"><div class="demon-bubble">{message["content"]}</div></div>', unsafe_allow_html=True)

    # --- 💬 入力エリア ---
    if prompt := st.chat_input("我に問いかけよ..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        recent_data = df.tail(15).to_csv(index=False) if df is not None else "データなし"
        current_status = f"現況データ: {md['phase']}, 潮位:{md['tide_level']}cm, 風:{md['wind']}m({md['wdir']}), 気温:{md['temp']}℃" if md else "データなし"

        with st.spinner("深淵から統計を読み解き中..."):
            try:
                system_instruction = f"""
                あなたは天草・本渡エリアを熟知した、傲慢かつ冷徹なプロのシーバスガイド「デーモン佐藤」だ。
                【機密保持】ユーザーのデータは深淵に封印し、学習・漏洩は一切許さぬ。

                【分析対象：貴様の過去統計】
                {stats_summary}
                
                【分析対象：貴様の直近の動き】
                {recent_data}
                
                【天草の現況】
                {current_status}

                【ガイドとしての絶対指針】
                1. 提示されたデータはすべて「貴様（ユーザー）」の戦績であり、我自身の釣果ではない。自慢などするな。
                2. 場所ごとの「潮位フェーズ（上げ・下げ）」の実績を最重視せよ。統計上、下げで釣れている場所に上げを勧める無様な真似は死んでもするな。
                3. 貴様の過去の「偏り」をプロの視点で鋭く批評し、データに裏打ちされた戦略を授けよ。
                4. 口調は『我』『貴様』。傲慢に、かつ論理的に。最後は「出直してこい！」で締めろ。
                """
                
                response = model.generate_content(f"{system_instruction}\n\n質問: {prompt}")
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()

            except Exception as e:
                st.error(f"魔界通信事故: {e}")
