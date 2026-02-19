import streamlit as st
import pandas as pd
import plotly.express as px

def show_strategy_analysis(df):
    if df is None or df.empty:
        st.info("データがありません。")
        return

    # 1. データのクレンジング
    df_suzuki = df.copy()
    
    # スズキ限定、テスト・ボウズ除外（共有いただいた「魚種」カラムを使用）
    df_suzuki = df_suzuki[(df_suzuki['魚種'] == "スズキ") & (~df_suzuki['魚種'].isin(["テスト", "ボウズ"]))]
    
    if df_suzuki.empty:
        st.warning("分析に必要な「スズキ」のデータがまだありません。")
        return

    # 全長を数値に変換（共有いただいた「全長_cm」カラムを使用）
    df_suzuki['length_num'] = pd.to_numeric(df_suzuki['全長_cm'], errors='coerce')
    # 数値化できない、または空のデータを除外（グラフエラー防止）
    df_suzuki = df_suzuki.dropna(subset=['length_num'])

    st.subheader("🎯 スズキ専用 戦略分析")

    # 共通のスマホ最適化設定
    config = {'scrollZoom': False, 'displayModeBar': False}

    # --- A. 潮名別実績（潮名カラムを使用） ---
    if '潮名' in df_suzuki.columns:
        st.write("🌊 潮名別の実績")
        tide_stats = df_suzuki.groupby('潮名').agg(
            釣果数=('魚種', 'count'),
            平均全長=('length_num', 'mean')
        ).reset_index()
        
        fig_tide = px.bar(tide_stats, x='潮名', y='釣果数', color='平均全長',
                          color_continuous_scale='Viridis', height=350,
                          labels={'平均全長': '平均サイズ(cm)'})
        apply_mobile_style(fig_tide)
        st.plotly_chart(fig_tide, use_container_width=True, config=config)

    # --- B. 場所別の全長実績（場所カラムを使用） ---
    if '場所' in df_suzuki.columns:
        st.write("📍 場所別のサイズ分布")
        # 箱ひげ図で「その場所のポテンシャル」を可視化
        fig_loc = px.box(df_suzuki, x='場所', y='length_num', color='場所',
                         points="all", height=400,
                         labels={'length_num': '全長(cm)'})
        apply_mobile_style(fig_loc)
        st.plotly_chart(fig_loc, use_container_width=True, config=config)

    # --- C. 風向別の実績（風向カラムを使用） ---
    if '風向' in df_suzuki.columns:
        st.write("🌬️ 風向別実績")
        wind_stats = df_suzuki['風向'].value_counts().reset_index()
        wind_stats.columns = ['風向', '件数']
        fig_wind = px.pie(wind_stats, values='件数', names='風向', hole=0.3)
        apply_mobile_style(fig_wind)
        st.plotly_chart(fig_wind, use_container_width=True, config=config)

    # --- D. ルアー別実績（ルアーカラムを使用） ---
    if 'ルアー' in df_suzuki.columns:
        st.write("🎣 ヒットルアー TOP10")
        lure_stats = df_suzuki['ルアー'].value_counts().reset_index().head(10)
        lure_stats.columns = ['ルアー', '個数']
        fig_lure = px.bar(lure_stats, x='個数', y='ルアー', orientation='h', 
                          color_discrete_sequence=['#00ffd0'])
        fig_lure.update_layout(yaxis={'categoryorder':'total ascending'})
        apply_mobile_style(fig_lure)
        st.plotly_chart(fig_lure, use_container_width=True, config=config)

def apply_mobile_style(fig):
    """スマホでスクロールを邪魔しないための共通設定"""
    fig.update_layout(
        margin=dict(l=10, r=10, t=30, b=10),
        dragmode=False,
        xaxis=dict(fixedrange=True),
        yaxis=dict(fixedrange=True),
        hovermode="closest"
    )
