def show_ai_page(conn, url, df, md=None):
    # --- 👿 デーモン佐藤・検問プロトコル ---
    # URLの末尾に「?user=sato」がついているか確認
    query_params = st.query_params
    is_demon_sato = query_params.get("user") == "sato"

    if not is_demon_sato:
        # 🚧 一般人向けの「門前払い」画面 🚧
        st.markdown("""
            <style>
            .maint-box {
                text-align: center; 
                padding: 40px; 
                background-color: #1a1c23; 
                color: #ff4b4b;
                border: 3px double #ff4b4b; 
                border-radius: 20px; 
                margin-top: 50px;
                box-shadow: 0 0 20px rgba(255, 75, 75, 0.2);
            }
            </style>
            <div class="maint-box">
                <h1 style="font-size: 2.5rem;">🚧 魔界メンテナンス中 🚧</h1>
                <p style="font-size: 1.1rem; color: #cccccc;">
                    現在、デーモン佐藤が深淵のデータを調整中だ。<br>
                    貴様のような人間が立ち入る時間はまだ先の話よ。<br>
                    潮が満ちるまで震えて待て。
                </p>
                <hr style="border: 0.5px solid #333;">
                <p style="font-size: 0.8rem; color: #666;">Status: 深淵同期中... 66.6%</p>
            </div>
        """, unsafe_allow_html=True)
        st.stop()  # ここで処理を強制終了！下のAIコードは読み込ませない。

    # --- 👿 ここから下は「デーモン佐藤」だけが到達できる聖域 ---
    st.toast("👿 貴様か、佐藤。開発者権限を確認したぞ。", icon="🔥")
    
    # (ここから下に、貴様がさっき提示した avatar_display_url 以降のコードを繋げる)
