import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    # CSS: 以前の「透明な板（pointer-events: none）」を解除し、ホバーを有効化
    st.markdown("""
        <style>
        [data-testid="stPlotlyChart"] {
            pointer-events: auto !important;
            touch-action: auto !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.subheader("📊 時合精密解析 (詳細ホバー版)")

    if df.empty:
        st.info("データがありません。")
        return

    # --- 1. 場所・魚種の選択ロジック ---
    places = sorted(df["場所"].unique())
    selected_place = st.selectbox("📍 場所を選択", places, key="ana_place")
    df_p_base = df[df["場所"] == selected_place].copy()
    
    all_species = sorted(df_p_base["魚種"].unique())
    selected_species = st.multiselect("🐟 魚種を選択", all_species, default=all_species[:1] if all_species else [], key="selected_species")

    # --- 2. データ前処理 ---
    def process_coords(target_df):
        res_df = target_df.copy()

        def extract_step(ph):
            ph_str = str(ph).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
            nums = re.findall(r'\d+', ph_str)
            if nums:
                return max(0, min(10, int(nums[0])))
            if any(x in ph_str for x in ["干潮後", "上げ始め", "上げ初め"]):
                return 1
            if any(x in ph_str for x in ["満潮前", "上げ終盤"]):
                return 9
            if any(x in ph_str for x in ["満潮後", "下げ始め", "下げ初め"]):
                return 1
            if any(x in ph_str for x in ["干潮前", "下げ終盤"]):
                return 9
            return 5

        res_df['is_up'] = res_df['潮位フェーズ'].apply(lambda x: "下げ" not in str(x))
        res_df['step_val'] = res_df['潮位フェーズ'].apply(extract_step)
        res_df['dt_temp'] = pd.to_datetime(res_df['datetime'], errors='coerce')
        res_df['hour_cat'] = res_df['dt_temp'].dt.hour.apply(lambda h: 0 if 4 <= h <= 19 else 1)
        res_df['repeat_idx'] = res_df.groupby(['step_val', 'is_up', 'hour_cat']).cumcount()

        def calc(row):
            if not row['is_up']:
                x_base = row['step_val'] * 0.625
            else:
                x_base = 6.25 + (row['step_val'] * 0.625)
            
            offset = 0 if row['hour_cat'] == 0 else 12.5
            jitter = row['repeat_idx'] * 0.25
            final_x = x_base + offset + jitter
            final_y = 100 * np.cos(x_base * np.pi / 6.25)
            
            return pd.Series([final_x, final_y])

        res_df[['x_sync', 'y_sync']] = res_df.apply(calc, axis=1)
        return res_df

    df_p = process_coords(df_p_base)

    # --- 3. グラフ描画 ---
    if selected_species and not df_p.empty:
        display_df = df_p[df_p['魚種'].isin(selected_species)].sort_values('datetime', ascending=False)
        
        # タイド分布グラフ
        fig = go.Figure()
        x_plot = np.linspace(0, 25, 1000)
        y_plot = [100 * np.cos((x % 12.5) * np.pi / 6.25) for x in x_plot]
        fig.add_trace(go.Scatter(x=x_plot, y=y_plot, mode='lines', line=dict(color='#00d4ff', width=2), fill='tozeroy', fillcolor='rgba(0, 212, 255, 0.1)', hoverinfo='skip'))
        
        for species in selected_species:
            spec_df = display_df[display_df['魚種'] == species]
            if spec_df.empty: continue
            
            # ホバーテキスト作成 (潮名、潮位、全長を追加)
            def make_hover(r):
                return (f"<b>{r['魚種']}</b> ({r.get('全長_cm','-')}cm)<br>"
                        f"時刻: {r.get('time','-')}<br>"
                        f"潮名: {r.get('潮名','-')}<br>"
                        f"潮位: {r.get('潮位_cm','-')}cm<br>"
                        f"フェーズ: {r.get('潮位フェーズ','-')}")

            fig.add_trace(go.Scatter(
                x=spec_df['x_sync'], y=spec_df['y_sync'],
                mode='markers', name=species,
                text=spec_df.apply(make_hover, axis=1),
                hoverinfo='text',
                customdata=spec_df.index,
                marker=dict(size=14, symbol=spec_df['is_up'].apply(lambda x: 'triangle-up' if x else 'triangle-down'),
                            color=spec_df['is_up'].apply(lambda x: '#00ffd0' if x else '#ff4b4b'),
                            line=dict(width=1, color='white'))
            ))
        
        fig.update_layout(
            xaxis=dict(tickvals=[6.25, 18.75], ticktext=["☀️ 昼", "🌙 夜"], range=[-0.5, 25.5], gridcolor='rgba(255,255,255,
