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
    
    # 「年月」の列を作成（並び替え用に Period型を使用）
    df_stats['year_month'] = df_stats['datetime'].dt.to_period('M')

    st.subheader("📈 スズキ釣果トレンド（全期間）")

    # 2. スズキのみのデータにフィルタリング
    df_suzuki = df_stats[df_stats['魚種'] == "スズキ"]

    if df_suzuki.empty:
        st.warning("「スズキ」のデータがまだありません。")
    else:
        # --- 全期間のベース枠作成（抜け漏れのないカレンダー作成） ---
        start_month = df_stats['year_month'].min()
        end_month = df_stats['year_month'].max()
        all_months = pd.period_range(start=start_month, end=end_month, freq='M')
        base_df = pd.DataFrame({'year_month': all_months})
        
        # 月ごとの集計
        suzuki_monthly = df_suzuki.groupby('year_month').agg(
            釣果数=('datetime', 'count'),
            最大サイズ=('length_num', 'max')
        ).reset_index()
        
        # マージしてグラフ用データ作成（釣果なしの月を0で埋める）
        final_suzuki = pd.merge(base_df, suzuki_monthly, on='year_month', how='left').fillna(0)
        # Plotly表示用に文字列に変換
        final_suzuki['display_month'] = final_suzuki['year_month'].astype(str)

        # Plotlyによる2軸グラフ
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # 棒グラフ：釣果数
        fig.add_trace(
            go.Bar(x=final_suzuki['display_month'], y=final_suzuki['釣果数'], 
                   name="釣果数 (匹)", marker_color='#00ffd0', opacity=0.6),
            secondary_y=False,
        )

        # 折れ線グラフ：最大サイズ
        fig.add_trace(
            go.Scatter(x=final_suzuki['display_month'], y=final_suzuki['最大サイズ'], 
                       name="最大サイズ (cm)", line=dict(color='#ff4b4b', width=3), mode='lines+markers'),
            secondary_y=True,
        )

        fig.update_layout(
            title_text="スズキ全期間釣果推移",
            xaxis=dict(title="年月", tickangle=45),
            yaxis=dict(title="釣果数 (匹)", side="left"),
            yaxis2=dict(title="最大サイズ (cm)", side="right", overlaying="y", range=[0, 100]),
            legend=dict(x=0, y=1.1, orientation="h"),
            margin=dict(l=20, r=20, t=60, b=80),
            hovermode="x unified"
        )

        st.plotly_chart(fig, use_container_width=True)

    # --- C. 全魚種の累計内訳表 ---
    st.markdown("---")
    st.write("📅 月別・魚種別内訳（全期間）")
    
    df_stats['年月'] = df_stats['datetime'].dt.strftime('%Y-%m')
    monthly_pivot = df_stats.pivot_table(
        index='年月', columns='魚種', values='datetime', aggfunc='count', fill_value=0
    )
    # 最新が一番上
    st.dataframe(monthly_pivot.sort_index(ascending=False), use_container_width=True)

    # --- D. 総合サマリー ---
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    suz_total = len(df_suzuki)
    suz_max = df_suzuki['length_num'].max() if not df_suzuki.empty else 0
    c1.metric("スズキ 累計", f"{suz_total} 匹")
    c2.metric("歴代最大", f"{suz_max} cm")
    c3.metric("全魚種 累計", f"{len(df_stats)} 匹")
