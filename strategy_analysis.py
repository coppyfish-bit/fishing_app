import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def show_strategy_analysis(df):
    if df is None or df.empty:
        st.info("データがありません。")
        return

    # スズキのみ、かつ「テスト・ボウズ」を除外
    df_suzuki = df[(df['魚種'] == "スズキ") & (~df['魚種'].isin(["テスト", "ボウズ"]))]
    
    if df_suzuki.empty:
        st.warning("スズキの釣果データが不足しています。")
        return

    # 数値変換
    df_suzuki['length_num'] = pd.to_numeric(df_suzuki['全長_cm'], errors='coerce').fillna(0)

    st.header("🎯 スズキ専用 戦略分析")

    # --- 共通のグラフ設定（スマホ最適化） ---
    config = {'scrollZoom': False, 'displayModeBar': False}

    # 1. 潮名別：釣果数 & 平均サイズ
    st.subheader("🌊 潮名別の実績")
    tide_stats = df_suzuki.groupby('潮名').agg(
        釣果数=('魚種', 'count'),
        平均全長=('length_num', 'mean')
    ).reset_index()
    
    fig_tide = px.bar(tide_stats, x='潮名', y='釣果数', color='平均全長',
                      title="潮名別実績（色は平均サイズ）",
                      color_continuous_scale='Viridis', height=350)
    update_fig_layout(fig_tide)
    st.plotly_chart(fig_tide, use_container_width=True, config=config)

    # 2. 場所別：サイズ実績
    st.subheader("📍 場所別のサイズ実績")
    fig_loc = px.box(df_suzuki, x='場所名', y='length_num', color='場所名',
                     title="場所別の全長分布（箱ひげ図）")
    update_fig_layout(fig_loc)
    st.plotly_chart(fig_loc, use_container_width=True, config=config)

    # 3. 風向き別：キャッチ数
    st.subheader("🌬️ 風向き別実績")
    wind_stats = df_suzuki.groupby('風向き').size().reset_index(name='キャッチ数')
    fig_wind = px.pie(wind_stats, values='キャッチ数', names='風向き', 
                      hole=0.4, title="風向き別シェア")
    update_fig_layout(fig_wind)
    st.plotly_chart(fig_wind, use_container_width=True, config=config)

    # 4. ルアー別：キャッチ数
    st.subheader("🎣 ヒットルアーTOP10")
    lure_stats = df_suzuki.groupby('ルアー名').size().reset_index(name='個数').sort_values('個数', ascending=False).head(10)
    fig_lure = px.bar(lure_stats, x='個数', y='ルアー名', orientation='h',
                      title="ルアー別キャッチ数", color_discrete_sequence=['#ff4b4b'])
    fig_lure.update_layout(yaxis={'categoryorder':'total ascending'})
    update_fig_layout(fig_lure)
    st.plotly_chart(fig_lure, use_container_width=True, config=config)

def update_fig_layout(fig):
    """グラフのスマホ最適化共通設定"""
    fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        hovermode="closest",
        dragmode=False,
        xaxis=dict(fixedrange=True),
        yaxis=dict(fixedrange=True)
    )