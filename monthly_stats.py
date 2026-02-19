import streamlit as st
import pandas as pd

def show_monthly_stats(df):
    if df is None or df.empty:
        st.info("データがありません。")
        return

    # データのコピーと型変換
    df_stats = df.copy()
    
    # 全長_cmを数値に変換（変換できないものは0に）
    df_stats['length_num'] = pd.to_numeric(df_stats['全長_cm'], errors='coerce').fillna(0)
    
    # 日付型に変換
    df_stats['datetime'] = pd.to_datetime(df_stats['datetime'], errors='coerce')
    df_stats = df_stats.dropna(subset=['datetime'])
    
    # 月列を作成 (例: 2026-02)
    df_stats['month'] = df_stats['datetime'].dt.strftime('%Y-%m')

    st.subheader("📊 月別釣果統計")

    # --- A. 月別キャッチ数のグラフ ---
    monthly_counts = df_stats.groupby('month').size().reset_index(name='釣果数')
    # 新しい順に並べる場合は ascending=False
    monthly_counts = monthly_counts.sort_values('month', ascending=True)
    
    st.write("📈 月別キャッチ数")
    st.bar_chart(data=monthly_counts, x='month', y='釣果数', color="#00ffd0")

    # --- B. 月別×魚種別のクロス集計表 ---
    st.write("📅 月別・魚種別の内訳")
    monthly_fish = df_stats.pivot_table(
        index='month', 
        columns='魚種', 
        values='datetime', 
        aggfunc='count', 
        fill_value=0
    )
    # 最新月を一番上に表示
    monthly_fish = monthly_fish.sort_index(ascending=False)
    st.dataframe(monthly_fish, use_container_width=True)

    # --- C. 月別の最大サイズ推移 ---
    st.write("📏 月別最大サイズ (cm)")
    monthly_max = df_stats.groupby('month')['length_num'].max().reset_index(name='最大サイズ')
    st.line_chart(data=monthly_max, x='month', y='最大サイズ', color="#ff4b4b")

    # --- D. 累計サマリー ---
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    c1.metric("総キャッチ数", f"{len(df_stats)} 匹")
    c2.metric("歴代最大", f"{df_stats['length_num'].max()} cm")
    c3.metric("今月の釣果", f"{len(df_stats[df_stats['month'] == pd.Timestamp.now().strftime('%Y-%m')])} 匹")