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
    df_stats['length_num'] = pd.to_numeric(df_stats['全長_cm'], errors='coerce').fillna(0)
    df_stats['datetime'] = pd.to_datetime(df_stats['datetime'], errors='coerce')
    df_stats = df_stats.dropna(subset=['datetime'])
    df_stats['month_num'] = df_stats['datetime'].dt.month

    st.subheader("📊 スズキ年間分析（釣果数 × 最大サイズ）")

    # 2. スズキのみのデータにフィルタリング
    df_suzuki = df_stats[df_stats['魚種'] == "スズキ"]

    if df_suzuki.empty:
        st.warning("「スズキ」のデータがまだありません。")
    else:
        # 1月〜12月のベース枠作成
        base_months = pd.DataFrame({'月': range(1, 13)})
        suzuki_monthly = df_suzuki.groupby('month_num').agg(
            釣果数=('datetime', 'count'),
            最大サイズ=('length_num', 'max')
        ).reset_index().rename(columns={'month_num': '月'})
        
        final_suzuki = pd.merge(base_months, suzuki_monthly, on='月', how='left').fillna(0)

        # --- Plotlyによる2軸グラフの作成 ---
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        # 棒グラフ：釣果数（左軸）
        fig.add_trace(
            go.Bar(x=final_suzuki['月'], y=final_suzuki['釣果数'], 
                   name="釣果数 (匹)", marker_color='#00ffd0', opacity=0.6),
            secondary_y=False,
        )

        # 折れ線グラフ：最大サイズ（右軸）
        fig.add_trace(
            go.Scatter(x=final_suzuki['月'], y=final_suzuki['最大サイズ'], 
                       name="最大サイズ (cm)", line=dict(color='#ff4b4b', width=3), mode='lines+markers'),
            secondary_y=True,
        )

        # レイアウト設定
        fig.update_layout(
            title_text="月別スズキ釣果トレンド",
            xaxis=dict(title="月", tickmode='linear', tick0=1, dtick=1),
            yaxis=dict(title="釣果数 (匹)", side="left"),
            yaxis2=dict(title="最大サイズ (cm)", side="right", overlaying="y", range=[0, 100]),
            legend=dict(x=0, y=1.1, orientation="h"),
            margin=dict(l=20, r=20, t=60, b=20),
            hovermode="x unified"
        )

        st.plotly_chart(fig, use_container_width=True)

    # --- C. 全魚種の月別内訳（下部に配置） ---
    st.markdown("---")
    st.write("📅 全魚種・月別詳細（ボウズ・テスト除外）")
    df_stats['月別'] = df_stats['datetime'].dt.strftime('%Y-%m')
    monthly_pivot = df_stats.pivot_table(
        index='月別', columns='魚種', values='datetime', aggfunc='count', fill_value=0
    )
    st.dataframe(monthly_pivot.sort_index(ascending=False), use_container_width=True)

    # --- D. サマリー ---
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    suz_total = len(df_suzuki)
    suz_max = df_suzuki['length_num'].max() if not df_suzuki.empty else 0
    c1.metric("スズキ総数", f"{suz_total} 匹")
    c2.metric("スズキ最大", f"{suz_max} cm")
    c3.metric("全魚種合計", f"{len(df_stats)} 匹")
