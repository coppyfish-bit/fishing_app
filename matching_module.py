def show_matching_page(df):
    st.title("🏹 SeaBass Matcher Pro")
    st.caption("最新のカラム構成に基づいた高精度マッチング")

    # セッション状態の初期化（エラー回避用）
    if 'tide' not in st.session_state: st.session_state.tide = 150
    if 'phase' not in st.session_state: st.session_state.phase = "下げ"
    if 'wind' not in st.session_state: st.session_state.wind = 2.0
    if 'wdir' not in st.session_state: st.session_state.wdir = "北"
    if 'month' not in st.session_state: st.session_state.month = datetime.now().month

    # --- 1. 入力セクション ---
    with st.expander("🌍 海況データの設定", expanded=True):
        if st.button("🔄 リアルタイム情報を取得"):
            t_cm, t_ph = get_jma_tide_hs()
            temp, wind_spd, wdir_val = get_weather()
            st.session_state.tide = t_cm
            st.session_state.phase = t_ph
            st.session_state.wind = wind_spd
            st.session_state.wdir = wdir_val
            st.session_state.month = datetime.now().month
            st.rerun() # 値を反映させるために再起動

        c1, c2, c3 = st.columns(3)
        # 月の選択
        month = c1.selectbox("月", list(range(1, 13)), index=st.session_state.month - 1)
        
        # 潮位入力
        tide = c2.number_input("潮位(cm)", 0, 400, value=st.session_state.tide)
        
        # 潮位フェーズの選択（indexエラーを回避する安全な書き方）
        phase_options = ["上げ", "下げ", "満潮", "干潮"]
        default_phase = st.session_state.phase if st.session_state.phase in phase_options else "下げ"
        phase = c3.selectbox("潮位フェーズ", phase_options, index=phase_options.index(default_phase))
        
        c4, c5 = st.columns(2)
        wind = c4.number_input("風速(m)", 0.0, 20.0, value=st.session_state.wind)
        
        wdir_options = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
        default_wdir = st.session_state.wdir if st.session_state.wdir in wdir_options else "北"
        wdir = c5.selectbox("風向", wdir_options, index=wdir_options.index(default_wdir))

    # --- 2. マッチングロジック ---
    st.divider()
    
    # ...（以下、calculate_score や表示ロジックは前回と同じ）...
