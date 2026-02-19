import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def show_strategy_analysis(df):
    if df is None or df.empty:
        st.info("データがありません。")
        return

    # 1. データのクレンジング（スズキ限定、テスト・ボウズ除外）
    df_suzuki = df.copy()
    df_suzuki = df_suzuki[(df_suzuki['魚種'] == "スズキ") & (~df_suzuki['魚種'].isin(["テスト", "ボウズ"]))]
    
    if df_suzuki.empty:
        st.warning("分析に必要な「スズキ」のデータがまだありません。")
        return

    # 数値変換
    df_suzuki['length_num'] = pd.to_numeric(df_suzuki['全長_cm'], errors='coerce').fillna(0)

    st.subheader("🎯 スズキ専用 戦略分析")

    # 共通のスマホ最適化設定
    config = {'scrollZoom': False, 'displayModeBar': False}

    # --- A. 潮名別実績（釣果数 & 全長） ---
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

    # --- B. 場所名別の全長実績 ---
    st.write("📍 場所別のサイズ分布")
    # 箱ひげ図で「その場所でどのサイズが釣れやすいか」を可視化
    fig_loc = px.box(df_suzuki, x='場所名', y='length_num', color='場所名',
                     points="all", height=400)
    apply_mobile_style(fig_loc)
    st.plotly_chart(fig_loc, use_container_width=True, config=config)

    # --- C. 風向き別のキャッチ数実績 ---
    st.write("🌬️ 風向き別実績")
    wind_stats = df_suzuki.groupby('風向き').size().reset_index(name='件数')
    fig_wind = px.pie(wind_stats, values='件数', names='風向き', hole=0.3)
    apply_mobile_style(fig_wind)
    st.plotly_chart(fig_wind, use_container_width=True, config=config)

    # --- D. ルアー別実績 ---
    st.write("🎣 ヒットルアー TOP10")
    lure_stats = df_suzuki.groupby('ルアー名').size().reset_index(name='個数').sort_values('個数', ascending=False).head(10)
    fig_lure = px.bar(lure_stats, x='個数', y='ルアー名', orientation='h', 
                      color_discrete_sequence=['#00ffd0'])
    fig_lure.update_layout(yaxis={'categoryorder':'total ascending'})
    apply_mobile_style(fig_lure)
    st.plotly_chart(fig_lure, use_container_width=True, config=config)

def apply_mobile_style(fig):
    """スマホでスクロールを邪魔しないための共通レイアウト設定"""
    fig.update_layout(
        margin=dict(l=10, r=10, t=30, b=10),
        dragmode=False, # ドラッグ無効
        xaxis=dict(fixedrange=True), # ズーム禁止
        yaxis=dict(fixedrange=True),
        hovermode="closest"
    )
