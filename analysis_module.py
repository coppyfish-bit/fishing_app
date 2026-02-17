def show_phase_analysis_page(df):
    st.subheader("🌊 潮位フェーズ別・釣果集中度分析")

    if df.empty:
        st.info("データがありません。")
        return

    # 1. フィルタリング設定（場所と魚種）
    col1, col2 = st.columns(2)
    with col1:
        selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()), key="phase_place")
    with col2:
        all_species = sorted(df[df["場所"] == selected_place]["魚種"].unique())
        selected_species = st.multiselect(
            "🐟 魚種を選択", 
            all_species, 
            default=[s for s in ["スズキ", "ヒラスズキ"] if s in all_species] or all_species[:1],
            key="phase_species"
        )

    if not selected_species:
        st.info("魚種を選択してください。")
        return

    # データの絞り込み
    df_f = df[(df["場所"] == selected_place) & (df["魚種"].isin(selected_species))].copy()

    if df_f.empty:
        st.warning("該当するデータがありません。")
        return

    # 2. 潮位フェーズの並び順を定義（自然な流れにする）
    # スプレッドシートの表記に合わせて調整してください
    phase_order = [
        "干潮", "上げ1分", "上げ2分", "上げ3分", "上げ4分", "上げ5分", 
        "上げ6分", "上げ7分", "上げ8分", "上げ9分", "満潮",
        "下げ1分", "下げ2分", "下げ3分", "下げ4分", "下げ5分", 
        "下げ6分", "下げ7分", "下げ8分", "下げ9分"
    ]

    # 集計
    phase_counts = df_f.groupby('潮位フェーズ').size().reset_index(name='釣果数')
    
    # 定義した順序でソート（リストにないものは後ろへ）
    phase_counts['sort_idx'] = phase_counts['潮位フェーズ'].apply(
        lambda x: phase_order.index(x) if x in phase_order else 99
    )
    phase_counts = phase_counts.sort_values('sort_idx')

    # 3. グラフ作成
    # 上げは水色系、下げは赤色系にするためのカラー設定
    colors = ['#00d4ff' if '上げ' in p or p == '干潮' else '#ff4b4b' for p in phase_counts['潮位フェーズ']]

    fig = go.Figure(data=[
        go.Bar(
            x=phase_counts['潮位フェーズ'],
            y=phase_counts['釣果数'],
            marker_color=colors,
            text=phase_counts['釣果数'],
            textposition='auto',
        )
    ])

    fig.update_layout(
        title=f"【{selected_place}】潮位フェーズごとの釣果数",
        xaxis_title="潮位フェーズ",
        yaxis_title="釣果数（本）",
        template="plotly_dark",
        height=500
    )

    st.plotly_chart(fig, use_container_width=True)

    # 4. 分析コメント
    top_phase = phase_counts.loc[phase_counts['釣果数'].idxmax(), '潮位フェーズ']
    st.success(f"💡 この条件では **{top_phase}** に最も釣果が集中しています。狙い目です！")
