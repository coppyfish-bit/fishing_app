# --- 3. 座標計算ロジック (重なり回避・自動散らし版) ---
    def get_sync_coords(df_group):
        # グループ内での出現順（0, 1, 2...）を取得して、重なりを回避する
        df_group = df_group.copy()
        
        # 潮位フェーズからステップ数を抽出
        def extract_step(phase_str):
            nums = re.findall(r'\d+', str(phase_str).translate(str.maketrans('０１２３４５６７８９', '0123456789')))
            step = int(nums[0]) if nums else 5
            return max(0, min(10, step))

        df_group['step'] = df_group['潮位フェーズ'].apply(extract_step)
        df_group['is_up'] = df_group['潮位フェーズ'].apply(lambda x: "下げ" not in str(x))

        # 同じ「フェーズ」かつ「昼夜」が同じデータに連番を振る
        df_group['hour_cat'] = df_group['datetime'].dt.hour.apply(lambda h: 0 if 4 <= h <= 19 else 1)
        df_group['repeat_idx'] = df_group.groupby(['step', 'is_up', 'hour_cat']).cumcount()

        def calculate_final_x(row):
            # 基本のx座標
            x_val = row['step'] * 0.6 if not row['is_up'] else 6 + (row['step'] * 0.6)
            offset = 0 if row['hour_cat'] == 0 else 12.5
            
            # 【重要】重なり回避：2件目以降は 0.15 ユニットずつ右にずらす
            shift = row['repeat_idx'] * 0.15
            
            return x_val + offset + shift

        df_group['x_sync'] = df_group.apply(calculate_final_x, axis=1)
        # y座標は波の曲線上に固定（あえてずらさないことで、同じ潮位であることを示す）
        df_group['y_sync'] = df_group.apply(lambda r: 100 * np.cos((r['step'] * 0.6) * np.pi / 6), axis=1)
        
        return df_group

    if not df_p.empty:
        # 場所・魚種フィルタリング後のデータ全体に対して重なり防止を適用
        df_p = get_sync_coords(df_p)
