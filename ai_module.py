import streamlit as st
import google.generativeai as genai

def show_ai_page(conn, url, df):
    st.title("🛠️ AI疎通デバッグ")
    
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("❌ Secretsに GEMINI_API_KEY が見つかりません。")
        return

    # --- 修正ポイント：確実に存在するモデルIDを指定 ---
    # 案1: gemini-1.5-flash (もっとも標準的)
    # 案2: gemini-1.5-flash-8b (さらに軽量で通りやすい)
    model_name = "gemini-2.0-flash" 
    
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    try:
        model = genai.GenerativeModel(model_name)
        st.success(f"✅ モデル `{model_name}` の初期化に成功")
    except Exception as e:
        st.error(f"モデル初期化失敗: {e}")
        return

    if st.button("AIに挨拶を送る（テスト実行）"):
        try:
            with st.spinner("深淵と通信中..."):
                # 非常に短いプロンプトでテスト
                response = model.generate_content("Hi")
                st.write("--- AIからの返答 ---")
                st.write(response.text)
                st.balloons()
        except Exception as e:
            st.error(f"❌ 通信エラー発生: {e}")
            # エラー内容に応じたアドバイス
            if "404" in str(e):
                st.warning("指定したモデル名が正しくないようです。")
            elif "429" in str(e):
                st.warning("利用制限（Quota）に達しています。1分待ってください。")
