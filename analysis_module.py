import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 時合精密解析 (スマホ完全固定・画像版)")

    # --- 1. 場所・魚種の選択ロジック (変更なし) ---
    places = sorted(df["場所"].unique())
    if "prev_place" not in st.session_state:
        st.session_state.prev_place = places[0]
    selected_place = st.selectbox("📍 場所を選択", places, key="ana_place")
    df_p_base = df[df["場所"] == selected_place].copy()
    
    all_species = sorted(df_p_base["魚種"].unique())
    if st.session_state.prev_place != selected_place or "selected_species" not in st.session_state:
        if not df_p_base.empty:
            top_species = df_p_base["魚種"].value_counts().idxmax()
            st.session_state.selected_species = [top_species]
        else:
            st.session_state.selected_species = []
        st.session_state.prev_place = selected_place
    selected_species = st.multiselect("🐟 魚種を選択", all_species, key="selected_species")

    # --- 2. データ前処理 (計算ロジックのみ) ---
    df_p = df_p_base.copy()
    def clean_dt(val):
        if pd.isna(val): return None
        s = str(val).strip().translate(str.maketrans('０１２３４５６７８９：／－', '0123456789:/-'))
        return re.sub(r'[^0-9:/\-\s]', '', s.replace('年','/').replace('月','/').replace('日',' ').replace('時',':'))
    df_p['datetime'] = df_p['datetime'].apply(clean_dt).apply(lambda x: pd.to_datetime(x, errors='coerce'))
    df_p = df_p.dropna(subset=['datetime'])

    def process_coords(target_df):
        res_df = target_df.copy()
        def extract_step(ph):
            nums = re.findall(r'\d+', str(ph).translate(str.maketrans('０１２３４５６７８９', '0123456789')))
            return max(0, min(10, int(nums[0]))) if nums else 5
        res_df['step_val'] = res_df['潮位フェーズ'].apply(extract_step)
        res_df['is_up'] = res_df['潮位フェーズ'].apply(lambda x: "下げ" not in str(x))
        res_df['hour_cat'] = res_df['datetime'].dt.hour.apply(lambda h: 0 if 4 <= h <= 19 else 1)
        res_df['repeat_idx'] = res_df.groupby(['step_val', 'is_up', 'hour_cat']).cumcount()
        def calc(row):
            x = row['step_val'] * 0.6 if not row['is_up'] else 6 + (row['step_val'] * 0.6)
            off = 0 if row['hour_cat'] == 0 else 12.5
            fx = x + off + (row['repeat_idx'] * 0.18)
            fy = 100 * np.cos(x * np.pi / 6)
            return pd.Series([fx, fy])
        res_df[['x_sync', 'y_sync']] = res_df.apply(calc, axis=1)
        return res_df

    if not df_p.empty:
        df_p = process_coords(df_p)

    # --- 3. グラフ生成と表示 ---
    if selected_species and not df_p.empty:
        display_df = df_p[df_p['魚種'].isin(selected_species)]
        
        # タイドグラフ
        fig = go.Figure()
        x_plot = np.linspace(0, 25, 1000)
        y_plot = [100 * np.cos((x % 12.5) * np.pi / 6) if (x % 12.5) <= 12 else 100 for x in x_plot]
        fig.add_trace(go.Scatter(x=x_plot, y=y_plot, mode='lines', line=dict(color='#00d4ff', width=2), fill='tozeroy', fillcolor='rgba(0, 212, 255, 0.1)'))
        for species in selected_species:
            spec_df = display_df[display_df['魚種'] == species]
            if spec_df.empty: continue
            symbols = spec_df['is_up'].apply(lambda x: 'triangle-up' if x else 'triangle-down')
            colors = spec_df['is_up'].apply(lambda x: '#00ffd0' if x else '#ff4b4b')
            fig.add_trace(go.Scatter(x=spec_df['x_sync'], y=spec_df['y_sync'], mode='markers', name=species, marker=dict(size=14, symbol=symbols, color=colors, line=dict(width=1, color='white'))))
        
        fig.update_layout(xaxis=dict(tickvals=[6, 18.5], ticktext=["☀️ 昼", "🌙 夜"], range=[-0.5, 25.5], gridcolor='rgba(0,0,0,0)'), yaxis=dict(showticklabels=False, range=[-120, 150]), template="plotly_dark", height=320, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        
        # 【重要】グラフを「画像」として表示
        st.write("🌊 タイド分布")
        st.image(fig.to_image(format="png", scale=2), use_container_width=True)

        # 棒グラフ
        st.write("📈 フェーズ別ボリューム")
        phase_order = [f"下げ{i}分" for i in range(10)] + [f"上げ{i}分" for i in range(1, 11)]
        display_df_copy = display_df.copy()
        display_df_copy['norm_phase'] = display_df_copy.apply(lambda r: f"{'上げ' if r['is_up'] else '下げ'}{r['step_val']}分", axis=1)
        counts = display_df_copy['norm_phase'].value_counts().reindex(phase_order, fill_value=0).reset_index()
        counts.columns = ['フェーズ', '件数']
        
        fig_bar = go.Figure()
        colors_bar = ['#ff4b4b' if '下げ' in p else '#00ffd0' for p in counts['フェーズ']]
        fig_bar.add_trace(go.Bar(x=counts['フェーズ'], y=counts['件数'], marker_color=colors_bar))
        fig_bar.update_layout(template="plotly_dark", height=230, margin=dict(l=5, r=5, t=10, b=30), xaxis=dict(tickmode='array', tickvals=["下げ0分", "下げ5分", "下げ9分", "上げ1分", "上げ5分", "上げ10分"], ticktext=["満", "下5", "干前", "干", "上5", "満"], categoryorder='array', categoryarray=phase_order), yaxis=dict(showgrid=False), showlegend=False)
        
        # 【重要】棒グラフも「画像」として表示
        st.image(fig_bar.to_image(format="png", scale=2), use_container_width=True)

    else:
        st.info("魚種を選択してください。")
