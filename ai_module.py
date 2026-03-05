import streamlit as st
import google.generativeai as genai

def show_ai_page(conn, url, df):
    st.title("🛠️ AI疎通デバッグ")
    
    # 1. APIキーの確認
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("❌ Secretsに GEMINI_API_KEY が見つかりません。")
        return
    
    st.success("✅ APIキーは読み込まれています。")

    # 2. モデルの初期化テスト
    # 2.0-flash が制限中なら 1.5-flash-latest を試す
    model_name = "gemini-1.5-flash-latest" 
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel(model_name)
    
    st.write(f"試行中のモデル: `{model_name}`")

    # 3. 実際に短い文字を送ってみる
    if st.button("AIに挨拶を送る（テスト実行）"):
        try:
            with st.spinner("通信中..."):
                response = model.generate_content("「こんにちは」とだけ返してください。")
                st.write("--- AIからの返答 ---")
                st.write(response.text)
                st.balloons()
        except Exception as e:
            st.error(f"❌ 通信エラー発生: {e}")
            if "429" in str(e):
                st.warning("⚠️ やはり利用制限（429）中です。あと1〜2分待つか、別のAPIキーが必要です。")
