import streamlit as st
import pandas as pd
import plotly.express as px

def show_strategy_analysis(df):
    if df is None or df.empty:
        st.info("データがありません。")
        return

    # 1. データの準備
    df_suzuki = df.copy()
    df_suzuki = df_suzuki[(df_suzuki['魚種'] == "スズキ") & (~df_suzuki['魚種'].isin(["テスト", "ボウズ"]))]
    
    if df_suzuki.empty:
        st.warning("スズキのデータが不足しています。")
        return

    # 数値変換とクレンジング
    df_suzuki['length_num'] = pd.to_numeric(df_suzuki['全長_cm'], errors='coerce').fillna(0)
    df_suzuki['tide_cm'] = pd.to_numeric(df_suzuki['潮位_cm'], errors='coerce').fillna(0)
    
    # 風向8方位変換
    wind_map = {'北':'北','北北東':'北東','北東':'北東','東北東':'北東','東':'東','東南東':'南東','南東':'南東','南南東':'南東','南':'南','南南西':'南西','南西':'南西','西北西':'南西','西':'西','西北西':'北西','北西':'北西','北北西':'北西'}
    if '風向' in df_suzuki.columns:
        df_suzuki['風向_8'] = df_suzuki['風向'].map(wind_map).fillna(df_suzuki['風向'])

    st.header("🎯 スズキ専用 戦略分析")

    places = [p for p in df_suzuki['場所'].unique() if p]
    selected_place = st.selectbox("分析する場所を選択", places)

    if selected_place:
        p_df = df_suzuki[df_suzuki['場所'] == selected_place].copy()

        # --- 2. 新ロジック：最多ヒット潮位域 (上げor下げ) の算出 ---
        # 潮位を20cm刻みのレンジにする
        p_df['tide_range_label'] = (p_df['tide_cm'] // 20 * 20).astype(int).astype(str) + "-" + (p_df['tide_cm'] // 20 * 20 + 20).astype(int).astype(str) + "cm"
        
        # 「上げ」か「下げ」かを判定（潮位フェーズの文字列から抽出）
        def judge_up_down(phase):
            if pd.isna(phase): return "不明"
            if "上げ" in str(phase): return "上げ"
            if "下げ" in str(phase): return "下げ"
            return str(phase)

        p_df['上げ下げ'] = p_df['潮位フェーズ'].apply(judge_up_down)
        
        # 「潮位域 + 上げ下げ」を結合したキーを作成 (例: 140-160cm(下げ))
        p_df['combined_tide_key'] = p_df['tide_range_label'] + " (" + p_df['上げ下げ'] + ")"
        
        # 最多ヒットの組み合わせを特定
        if not p_df['combined_tide_key'].empty:
            top_condition = p_df['combined_tide_key'].mode()[0]
        else:
            top_condition = "-"

        # 下げ○分の計算
        p_df['datetime'] = pd.to_datetime(p_df['datetime'], errors='coerce')
        p_df['last_high_tide'] = pd.to_datetime(p_df['直前の満潮_時刻'], errors='coerce')
        p_df['mins_since_high'] = (p_df['datetime'] - p_df['last_high_tide']).dt.total_seconds() / 60
        ebb_df = p_df[p_df['上げ下げ'] == '下げ']
        avg_ebb_mins = int(ebb_df['mins_since_high'].mean()) if not ebb_df.empty else 0

        # --- 3. 特選データ表示 ---
        st.subheader(f"📍 {selected_place} の特選実績")
        c1, c2 = st.columns(2)
        with c1:
            st.metric("歴代最大サイズ", f"{p_df['length_num'].max()} cm")
            st.metric("最多ヒット潮位域", top_condition) # ここを差し替え
        with c2:
            st.metric("最大ヒット潮位", f"{p_df['tide_cm'].max()} cm")
            st.metric("最多ヒット時合", f"下げ {avg_ebb_mins} 分")

        st.markdown("---")
        config = {'scrollZoom': False, 'displayModeBar': False}

        # --- 4. グラフ表示 ---
        col_a, col_b = st.columns(2)
        with col_a:
            st.write("🌬️ 有利な風向き")
            w_stats = p_df['風向_8'].value_counts().reset_index()
            w_stats.columns = ['風向', '件数']
            fig_w = px.bar(w_stats, x='風向', y='件数', color='件数', color_continuous_scale='Blues')
            apply_mobile_style(fig_w)
            st.plotly_chart(fig_w, use_container_width=True, config=config)
        with col_b:
            st.write("🌊 有利な潮名")
            t_stats = p_df.groupby('潮名').size().reset_index(name='件数')
            fig_t = px.bar(t_stats, x='潮名', y='件数', color='件数', color_continuous_scale='Viridis')
            apply_mobile_style(fig_t)
            st.plotly_chart(fig_t, use_container_width=True, config=config)

        st.write("🎣 ヒットルアー TOP10")
        l_stats = p_df['ルアー'].value_counts().reset_index().head(10)
        l_stats.columns = ['ルアー', '個数']
        fig_l = px.bar(l_stats, x='個数', y='ルアー', orientation='h', color_discrete_sequence=['#00ffd0'])
        fig_l.update_layout(yaxis={'categoryorder':'total ascending'})
        apply_mobile_style(fig_l, height=400)
        st.plotly_chart(fig_l, use_container_width=True, config=config)

def apply_mobile_style(fig, height=300):
    fig.update_layout(
        margin=dict(l=5, r=5, t=30, b=10),
        dragmode=False,
        xaxis=dict(fixedrange=True),
        yaxis=dict(fixedrange=True),
        hovermode="closest",
        height=height
    )
