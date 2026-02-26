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
        
        /* 🛡️ プライバシーバナー */
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

    # --- 🛡️ プライバシー保護宣言 ---
    st.markdown("""
        <div class="privacy-banner">
            <strong style="color: #00d4ff;">🛡️ 魔界機密保持プロトコル：発動中</strong><br>
            貴様との対話および釣果データは外部に漏洩せず、AIの学習にも一切利用されぬ。深淵の底に封印されておる。
        </div>
    """, unsafe_allow_html=True)

    # --- 😈 ヘッダー ---
    st.markdown(f"""
        <div class="header-container">
            <img src="{avatar_display_url}" class="header-img">
            <div>
                <h2 style="color: #ff4b4b; margin: 0;">デーモン佐藤の召喚</h2>
                <p style="color: #00ff00; font-size: 0.8rem; margin: 5px 0;">● 安定接続：知能特化モード</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    if st.button("🔥 記憶を浄化して深淵へ葬る"):
        st.session_state.messages = []
        st.rerun()
# ↓↓↓ ここから書き換え開始 ↓↓↓
    # --- 📊 全体統計要約エンジンの真価 ---
    stats_summary = "【データ不足】"
    if df is not None and not df.empty:
        try:
            # 1. 全体を通した最強の要素（最頻値）
            top_place = df['場所'].mode()[0] if '場所' in df.columns else "不明"
            top_lure = df['ルアー'].mode()[0] if 'ルアー' in df.columns else "不明"
            top_tide_name = df['潮名'].mode()[0] if '潮名' in df.columns else "不明"
            top_phase = df['潮位フェーズ'].mode()[0] if '潮位フェーズ' in df.columns else "不明"
            
            # 2. 全体の数値傾向（平均値）
            avg_hit_temp = df['気温'].mean() if '気温' in df.columns else 0
            avg_hit_wind = df['風速'].mean() if '風速' in df.columns else 0
            avg_hit_tide = df['潮位_cm'].mean() if '潮位_cm' in df.columns else 0
            
            # 3. 風向の支配力（どの風で最も釣っているか）
            top_wdir = df['風向'].mode()[0] if '風向' in df.columns else "不明"
            
            # 4. 月齢の傾向
            avg_moon = df['月齢'].mean() if '月齢' in df.columns else 0

            stats_summary = f"""
            【全釣行を通した絶対的傾向】
            ● 主戦場: {top_place}
            ● 信頼ルアー: {top_lure}
            ● 黄金の潮回り: {top_tide_name} ({top_phase})
            ● ヒット時の風向: {top_wdir} が支配的
            ● 数値的中央値: 気温 {avg_hit_temp:.1f}℃ / 風速 {avg_hit_wind:.1f}m / 潮位 {avg_hit_tide:.1f}cm
            ● 平均月齢: {avg_moon:.1f}
            ● 総データ数: {len(df)} 件の経験則に基づく
            """
        except Exception as e:
            stats_summary = f"【統計解析中に魔界のノイズ混入: {{e}}】"
    # ↑↑↑ ここまで書き換え終了 ↑↑↑
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
        
        # 直近の具体的な流れ（15件）
        recent_data = df.tail(15).to_csv(index=False) if df is not None else "データなし"
        
        # 今、目の前の状況
        current_status = f"現況データ: {md['phase']}, 潮位:{md['tide_level']}cm, 風:{md['wind']}m({md['wdir']}), 気温:{md['temp']}℃" if md else "データなし"

        with st.spinner("魔界の知識を練り上げ中..."):
            try:
                # 😈 ここが重要だ！ stats_summary（全体統計）を命令に叩き込む
                system_instruction = f"""
                あなたは天草の熟練ガイド「デーモン佐藤」だ。
                【機密保持】学習・漏洩厳禁。
                
                【全データから見た貴様の統計的傾向】
                {stats_summary}
                
                【直近15件の具体的な流れ】
                {recent_data}
                
                【今のリアルタイム状況】
                {current_status}
                
                これら全てを照らし合わせ、統計的な裏付けを持って傲慢に回答せよ。
                一人称は「我」、二人称は「貴様」。最後は突き放せ。
                """
                
                response = model.generate_content(f"{system_instruction}\n\n質問: {prompt}")
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()

            except Exception as e:
                st.error(f"魔界通信事故: {e}")




