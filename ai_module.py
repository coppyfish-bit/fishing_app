import streamlit as st
import google.generativeai as genai

def show_ai_page(conn, url, df):
    st.title("🚀 Gemini 2.0 Flash 疎通デバッグ")
    
    # 1. Secretsの確認
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("❌ Secretsに `GEMINI_API_KEY` が設定されていません。")
        return

    # 2. モデルIDの設定
    # 2.0 Flashの正式なIDは "gemini-2.0-flash" です
    model_id = "gemini-2.0-flash"
    
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

    # 3. 利用可能なモデルリストを表示（これが最強のデバッグです）
    if st.checkbox("利用可能なモデルリストを確認する"):
        try:
            models = genai.list_models()
            st.write("あなたのAPIキーで利用可能なモデル一覧:")
            for m in models:
                if 'generateContent' in m.supported_generation_methods:
                    st.code(m.name)
        except Exception as e:
            st.error(f"モデルリストの取得に失敗: {e}")

    st.divider()

    # 4. 実行テスト
    if st.button("2.0 Flash でテスト送信"):
        try:
            with st.spinner(f"モデル {model_id} と通信中..."):
                model = genai.GenerativeModel(model_id)
                # 応答
                response = model.generate_content("「2.0 Flash、起動成功」とだけ答えてください。")
                
                st.success("🎉 通信成功！")
                st.markdown(f"### AIからの返答:\n{response.text}")
                st.balloons()
        except Exception as e:
            st.error(f"❌ エラー発生詳細:\n{e}")
            
            # エラー別の対策案内
            error_msg = str(e)
            if "404" in error_msg:
                st.warning("⚠️ 404エラー: モデル名が見つかりません。上のチェックボックスで正しいモデル名を確認してください。")
            elif "429" in error_msg:
                st.warning("⚠️ 429エラー: 1日の上限または1分間の上限に達しました。")
            elif "API_KEY_INVALID" in error_msg:
                st.error("⚠️ APIキーが無効です。コピーミスがないか確認してください。")
