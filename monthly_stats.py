import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def show_monthly_stats(df):
    if df is None or df.empty:
        st.info("データがありません。")
        return

    # 1. データのクレンジング
    df_stats = df.copy()
    exclude_list = ["テスト", "ボウズ"]
    df_stats = df_stats[~df_stats['魚種'].isin(exclude_list)]
    
    # 数値と日付の変換
    df_stats['length_num'] = pd.to_numeric(df_stats['全長_cm'], errors='coerce').fillna(0)
    df_stats['datetime'] = pd.to_datetime(df_stats['datetime'], errors='coerce')
    df_stats = df_stats.dropna(subset=['datetime'])
    
    # スズキのみにフィルタリング
    df_suzuki = df_stats[df_stats['魚種'] == "スズキ"]

    if df_suzuki.empty:
        st.warning("「スズキ」のデータがまだありません。")
        return

    # --- A. 全期間トレンド ---
    st.subheader("📈 スズキ全期間トレンド")
    
    df_suzuki['year_month'] = df_suzuki['datetime'].dt.to_period('M')
    start_m = df_stats['datetime'].dt.to_period('M').min()
    end_m = df_stats['datetime'].dt.to_period('M').max()
    all_months_range = pd.period_range(start=start_m, end=end_m, freq='M')
    
    base_trend = pd.DataFrame({'year_month': all_months_range})
    trend_data = df_suzuki.groupby('year_month').agg(
        釣果数=('datetime', 'count'),
        最大サイズ=('length_num', 'max')
    ).reset_index()
    
    final_trend = pd.merge(base_trend, trend_data, on='year_month', how='left').fillna(0)
    final_trend['display_month'] = final_trend['year_month'].astype(str)

    fig_trend = create_dual_axis_chart(final_trend, 'display_month', "年月")
    # configで操作を制限
    st.plotly_chart(fig_trend, use_container_width=True, config={'staticPlot': False, 'scrollZoom': False, 'displayModeBar': False})


    # --- B. シーズン傾向（1月〜12月） ---
    st.markdown("---")
    st.subheader("📅 スズキ年間統計（1-12月）")

    df_suzuki['month_num'] = df_suzuki['datetime'].dt.month
    base_months = pd.DataFrame({'月': range(1, 13)})
    
    season_data = df_suzuki.groupby('month_num').agg(
        釣果数=('datetime', 'count'),
        最大サイズ=('length_num', 'max')
    ).reset_index().rename(columns={'month_num': '月'})
    
    final_season = pd.merge(base_months, season_data, on='月', how='left').fillna(0)

    fig_season = create_dual_axis_chart(final_season, '月', "月")
    # 同様にconfigで制限
    st.plotly_chart(fig_season, use_container_width=True, config={'staticPlot': False, 'scrollZoom': False, 'displayModeBar': False})


    # --- C. 全魚種の月別内訳表 ---
    st.markdown("---")
    st.write("📋 月別・魚種別内訳")
    df_stats['年月'] = df_stats['datetime'].dt.strftime('%Y-%m')
    monthly_pivot = df_stats.pivot_table(
        index='年月', columns='魚種', values='datetime', aggfunc='count', fill_value=0
    )
    st.dataframe(monthly_pivot.sort_index(ascending=False), use_container_width=True)

def create_dual_axis_chart(data, x_col, x_label):
    """スマホ向けに最適化された2軸グラフ"""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # 棒グラフ
    fig.add_trace(
        go.Bar(x=data[x_col], y=data['釣果数'], 
               name="匹数", marker_color='#00ffd0', opacity=0.6),
        secondary_y=False,
    )
    
    # 折れ線グラフ
    fig.add_trace(
        go.Scatter(x=data[x_col], y=data['最大サイズ'], 
                   name="cm", line=dict(color='#ff4b4b', width=3), mode='lines+markers'),
        secondary_y=True,
    )
    
    fig.update_layout(
        xaxis=dict(
            title=x_label, 
            tickmode='linear' if x_label=="月" else 'auto',
            tickangle=45 if x_label!="月" else 0, # 長い年月ラベルを斜めにして重なり防止
            fixedrange=True # X軸のズーム・移動を禁止
        ),
        yaxis=dict(title="釣果数 (匹)", side="left", fixedrange=True), # Y軸の操作禁止
        yaxis2=dict(title="最大サイズ (cm)", side="right", overlaying="y", range=[0, 100], fixedrange=True),
        legend=dict(x=0.5, y=1.2, xanchor='center', orientation="h"), # 凡例を中央上部に
        margin=dict(l=5, r=5, t=30, b=10), # 左右の余白を極限まで削ってグラフを広げる
        height=350, # スマホで一画面に収まりやすい高さ
        hovermode="x unified",
        dragmode=False # グラフ上のドラッグ（範囲選択）を無効化
    )
    return fig
