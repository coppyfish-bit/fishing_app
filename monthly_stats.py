import streamlit as st
import pandas as pd

def show_monthly_stats(df):
    if df is None or df.empty:
        st.info("データがありません。")
        return

    # 1. データのクレンジング
    df_stats = df.copy()
    
    # 「テスト」「ボウズ」を統計から完全に除外
    exclude_list = ["テスト", "ボウズ"]
    df_stats = df_stats[~df_stats['魚種'].isin(exclude_list)]
    
    # 全長_cmを数値に変換（変換できないものは0に）
    df_stats['length_num'] = pd.to_numeric(df_stats['全長_cm'], errors='coerce').fillna(0)
    
    # 日付型に変換
    df_stats['datetime'] = pd.to_datetime(df_stats['datetime'], errors='coerce')
    df_stats = df_stats.dropna(subset=['datetime'])
    
    # 統計用の「月(数字)」列を作成 (1〜12)
    df_stats['month_num'] = df_stats['datetime'].dt.month

    st.subheader("📊 スズキ年間釣果分析 (1月〜12月)")

    # 2. スズキのみのデータにフィルタリング
    df_suzuki = df_stats[df_stats['魚種'] == "スズキ"]

    if df_suzuki.empty:
        st.warning("「スズキ」のデータがまだありません。")
    else:
        # --- 1月〜12月の軸を固定するためのベース枠を作成 ---
        # これにより、釣果がない月もグラフ上に表示されます
        base_months = pd.DataFrame({'月': range(1, 13)})
        
        # スズキの月別集計（数と最大サイズ）
        suzuki_monthly = df_suzuki.groupby('month_num').agg(
            釣果数=('datetime', 'count'),
            最大サイズ=('length_num', 'max')
        ).reset_index()
        suzuki_monthly.rename(columns={'month_num': '月'}, inplace=True)

        # 12ヶ月の枠とマージして、データがない月を0で埋める
        final_suzuki = pd.merge(base_months, suzuki_monthly, on='月', how='left').fillna(0)
        final_suzuki = final_suzuki.set_index('月')

        # --- A. スズキ月別釣果数 (棒グラフ) ---
        st.write("📈 【スズキ】月別キャッチ数")
        st.bar_chart(final_suzuki['釣果数'], color="#00ffd0")

        # --- B. スズキ月別最大サイズ (折れ線グラフ) ---
        st.write("📏 【スズキ】月別最大サイズ推移 (cm)")
        st.line_chart(final_suzuki['最大サイズ'], color="#ff4b4b")

    # --- C. 月別×魚種別の詳細（テスト・ボウズを除く） ---
    st.markdown("---")
    st.write("📅 全魚種・月別の内訳")
    
    # 月列を作成 (YYYY-MM)
    df_stats['月別'] = df_stats['datetime'].dt.strftime('%Y-%m')
    
    monthly_fish = df_stats.pivot_table(
        index='月別', 
        columns='魚種', 
        values='datetime', 
        aggfunc='count', 
        fill_value=0
    )
    # 最新月を一番上に表示
    monthly_fish = monthly_fish.sort_index(ascending=False)
    st.dataframe(monthly_fish, use_container_width=True)

    # --- D. 累計サマリー ---
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    
    suzuki_total = len(df_suzuki)
    suzuki_max = df_suzuki['length_num'].max() if not df_suzuki.empty else 0
    total_catch = len(df_stats)
    
    c1.metric("スズキ総数", f"{suzuki_total} 匹")
    c2.metric("スズキ歴代最大", f"{suzuki_max} cm")
    c3.metric("全魚種合計", f"{total_catch} 匹")
