import streamlit as st
import pandas as pd
import os
import random

# --- 😈 デーモン佐藤の擬似人格 (API連携までの仮の姿) ---
def get_demon_sato_response(question, df):
    """
    ※ ここは将来的に Gemini API に置き換わります。
    現在は、それっぽいことを言うランダムな応答機能です。
    """
    record_count = len(df)
    recent_act = df.iloc[0] if not df.empty else None
    
    # デーモン佐藤らしい口調のテンプレート
    responses = [
        f"フン、我に教えを乞うとは殊勝な心がけだ。貴様のデータは現在{record_count}件しか溜まっておらんぞ。もっと精進せよ。",
        f"ほう...「{question}」だと？ その程度の質問、我の魔界の知識をもってすれば赤子の手をひねるようなもの。",
        "データを見る限り、貴様は潮汐の重要性を理解しておらんようだな。潮を読めぬ者に大物は微笑まぬ。",
        f"直近の記録では「{recent_act['場所']}」で「{recent_act['魚種']}」を釣ったようだな。悪くない...だが、魔界の基準では雑魚レベルだ！",
        "今は気分が乗らん。出直してこい。（※API未接続のため）",
        "貴様の釣り竿に魔力を込めてやろうか？ その代わり、魂を少しいただくがな...ククク。",
    ]
    
    # とりあえずランダムに返す
    ai_response_text = random.choice(responses)
    return ai_response_text

# --- メイン表示関数 ---
def show_ai_page(conn, url):
    st.header("😈 魔界釣果アドバイザー：デーモン佐藤")

    # データの読み込み
    df = conn.read(spreadsheet=url, ttl="0s")
    
    # 画像ファイルのパス
    avatar_path = "demon_sato.png"
    avatar_image = avatar_path if os.path.exists(avatar_path) else "😈" # 画像がなければ絵文字

    # 冒頭の挨拶（画像があれば表示）
    if os.path.exists(avatar_path):
        col1, col2 = st.columns([1, 4])
        with col1:
            st.image(avatar_path, width=100)
        with col2:
            st.write("「我を召喚したのは貴様か...。良いだろう、蓄積されたデータから、次の釣行のヒントを授けてやろう。感謝するのだな！」")
    else:
        st.warning("※ `demon_sato.png` が見つかりません。同じフォルダに配置してください。")

    st.markdown("---")

    if df.empty:
        st.warning("データがまだない。話にならん。")
        return

    # --- 💬 チャット履歴の初期化 ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # --- 履歴の表示 ---
    for message in st.session_state.messages:
        # ロール（役割）に応じてアバターを変える
        if message["role"] == "assistant":
            with st.chat_message(message["role"], avatar=avatar_image):
                st.markdown(message["content"])
        else:
            # ユーザー（人間）
            with st.chat_message(message["role"], avatar="👤"):
                st.markdown(message["content"])

    # --- ⌨️ 入力エリア ---
    if prompt := st.chat_input("デーモン佐藤に質問する... (例: 次の大潮の狙い目は？)"):
        # 1. ユーザーの質問を表示
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # 2. AI (デーモン佐藤) の応答を生成
        with st.chat_message("assistant", avatar=avatar_image):
            with st.spinner("魔界のデータベースにアクセス中..."):
                # ここでAI関数を呼び出す
                response_text = get_demon_sato_response(prompt, df)
                st.markdown(response_text)
        
        # 3. 応答を履歴に追加
        st.session_state.messages.append({"role": "assistant", "content": response_text})

    # (デバッグ用：現在のデータ傾向サマリーは下部に隠しておく)
    with st.expander("📊 現在のデータの傾向を見る"):
        st.dataframe(df[['date', '場所', '魚種', '潮位フェーズ']].tail(10))