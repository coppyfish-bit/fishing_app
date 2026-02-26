# --- 5. マッチング・スコアリング（潮汐重視設定） ---
    if df is not None and not df.empty:
        def calc_score(row):
            s = 0
            try:
                # 1. 潮位フェーズ（最優先：50点）
                # 例：「下げ5分」が一致すれば即座に高得点
                if str(row.get('潮位フェーズ', '')) == t_phase:
                    s += 50
                
                # 2. 潮位(cm)の近さ（重要：30点）
                # ±20cm以内なら満点、±40cm以内なら15点
                tide_diff = abs(row.get('潮位_cm', 0) - t_tide)
                if tide_diff <= 20:
                    s += 30
                elif tide_diff <= 40:
                    s += 15
                
                # 3. 月・シーズンのマッチング（10点）
                row_month = None
                if '月' in row: row_month = row['月']
                elif '日付' in row: row_month = pd.to_datetime(row['日付']).month
                
                if row_month == t_month:
                    s += 10
                
                # 4. 48h降水量のマッチング（10点）
                # 雨後の濁りパターンの再現用
                if abs(row.get('降水量_48h', 0) - t_rain) <= 10:
                    s += 10
                    
            except:
                pass
            return s

        # スコア計算実行
        df['マッチ度'] = df.apply(calc_score, axis=1)
        
        # スコアが高い順に上位5件を表示
        results = df[df['マッチ度'] > 0].sort_values('マッチ度', ascending=False).head(5)

        st.subheader("🎯 潮汐条件に基づく推奨ポイント")
        if not results.empty:
            for _, row in results.iterrows():
                # スコアに応じたバッジ表示
                if row['マッチ度'] >= 80:
                    label = "💎 最適時合"
                elif row['マッチ度'] >= 50:
                    label = "✅ 期待大"
                else:
                    label = "📝 参考実績"
                
                with st.expander(f"{label} (マッチ度: {row['マッチ度']}%) ： {row.get('場所', '不明')}"):
                    c_a, c_b = st.columns(2)
                    with c_a:
                        st.write(f"🐟 **{row.get('魚種','-')}**")
                        st.write(f"📏 **{row.get('全長_cm','-')} cm**")
                    with c_b:
                        st.write(f"🌊 {row.get('潮位フェーズ','-')}")
                        st.write(f"📏 {row.get('潮位_cm','-')} cm")
                    st.progress(row['マッチ度'] / 100)
        else:
            st.warning("現在の潮汐条件に合致する過去実績がありません。")
