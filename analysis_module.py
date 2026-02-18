# --- データの前処理 (自前クリーンアップ版) ---
    df_p = df_p_base.copy()
    
    def clean_datetime(val):
        if pd.isna(val): return val
        s = str(val).strip()
        # 全角を半角に変換
        s = s.translate(str.maketrans('０１２３４５６７８９：／－', '0123456789:/-'))
        # 「年」「月」「日」「時」「分」を区切り記号に置換
        s = s.replace('年', '/').replace('月', '/').replace('日', ' ').replace('時', ':').replace('分', '')
        # 余計な文字（「頃」など）を数字・記号以外削除
        s = re.sub(r'[^0-9:/\-\s]', '', s)
        return s

    # 文字列を綺麗にしてから変換
    df_p['datetime_clean'] = df_p['datetime'].apply(clean_datetime)
    df_p['datetime'] = pd.to_datetime(df_p['datetime_clean'], errors='coerce')

    # エラーチェック
    before_drop = len(df_p)
    df_p = df_p.dropna(subset=['datetime'])
    after_drop = len(df_p)
    
    if before_drop != after_drop:
        # まだエラーが出る場合は原因の文字列を表示して確認できるようにする
        error_rows = df_p_base[pd.to_datetime(df_p_base['datetime'].apply(clean_datetime), errors='coerce').isna()]
        st.error(f"❌ まだ1件読み込めません。スプレッドシートのこの値を確認してください: `{error_rows['datetime'].iloc[0]}`")
