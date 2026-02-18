# --- データの前処理 (秒なし・秒あり両対応版) ---
    df_p = df_p_base.copy()
    
    def clean_datetime_safe(val):
        if pd.isna(val): return None
        s = str(val).strip()
        # 全角変換や不要文字削除（前回のロジックを継続）
        s = s.translate(str.maketrans('０１２３４５６７８９：／－', '0123456789:/-'))
        s = s.replace('年', '/').replace('月', '/').replace('日', ' ').replace('時', ':').replace('分', '')
        s = re.sub(r'[^0-9:/\-\s]', '', s)
        return s if s else None

    # 文字列をクリーンアップ
    df_p['datetime_str'] = df_p['datetime'].apply(clean_datetime_safe)

    # 【重要】日付変換：複数のフォーマットを試す
    def parse_dt(s):
        if not s: return pd.NaT
        # 1. まず標準的な変換を試す
        dt = pd.to_datetime(s, errors='coerce')
        if pd.notna(dt): return dt
        # 2. 秒がない形式を試す (2026-02-17 14:50 など)
        try:
            return pd.to_datetime(s, format='%Y-%m-%d %H:%M')
        except:
            try:
                return pd.to_datetime(s, format='%Y/%m/%d %H:%M')
            except:
                return pd.NaT

    df_p['datetime'] = df_p['datetime_str'].apply(parse_dt)

    # エラーチェック（警告を出す条件を厳格に）
    invalid_rows = df_p[df_p['datetime'].isna() & df_p['datetime_str'].notna()]
    if not invalid_rows.empty:
        st.warning(f"⚠️ まだ読み込めない形式があります: `{invalid_rows['datetime_str'].iloc[0]}`")
    
    df_p = df_p.dropna(subset=['datetime'])
