import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 時合精密解析 (自動追従版)")

    if df.empty:
        st.info("データがありません。")
        return

    # --- 1. 場所の選択 ---
    places = sorted(df["場所"].unique())
    # Session State を使って場所の変更を管理
    if "prev_place" not in st.session_state:
        st.session_state.prev_place = places[0]

    selected_place = st.selectbox("📍 場所を選択", places, key="ana_place")
    
    # 選択された場所のデータを抽出
    df_p_base = df[df["場所"] == selected_place].copy()

    # --- 2. 魚種の自動選択ロジック ---
    all_species = sorted(df_p_base["魚種"].unique())
    
    # 場所が変わった場合、またはまだ初期化されていない場合に最多魚種をセット
    if st.session_state.prev_place != selected_place or "selected_species" not in st.session_state:
        if not df_p_base.empty:
            # その場所で一番釣れている魚種を特定
            top_species = df_p_base["魚種"].value_counts().idxmax()
            st.session_state.selected_species = [top_species]
        else:
            st.session_state.selected_species = []
        st.session_state.prev_place = selected_place

    # マルチセレクトの値を st.session_state で管理
    selected_species = st.multiselect(
        "🐟 魚種を選択", 
        all_species, 
        key="selected_species"
    )

    # --- 3. データの前処理 (以下、描画ロジックは継続) ---
    df_p = df_p_base.copy()
    
    def clean_datetime_safe(val):
        if pd.isna(val): return None
        s = str(val).strip().translate(str.maketrans('０１２３４５６７８９：／－', '0123456789:/-'))
        s = s.replace('年', '/').replace('月', '/').replace('日', ' ').replace('時', ':').replace('分', '')
        s = re.sub(r'[^0-9:/\-\s]', '', s)
        return s if s else None

    def parse_dt(s):
        if not s: return pd.NaT
        dt = pd.to_datetime(s, errors='coerce')
        if pd.notna(dt): return dt
        for fmt in ('%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M'):
            try: return pd.to_datetime(s, format=fmt)
            except: continue
        return pd.NaT

    df_p['datetime_str'] = df_p['datetime'].apply(clean_datetime_safe)
    df_p['datetime'] = df_p['datetime_str'].apply(parse_dt)
    df_p = df_p.dropna(subset=['datetime'])

    # 座標計算 (タイドグラフ用)
    def process_coordinates(target_df):
        res_df = target_df.copy()
        def extract_step_smart(phase_str):
            phase_str = str(phase_str)
            nums = re.findall(r'\d+', phase_str.translate(str.maketrans('０１２３４５６７８９', '0123456789')))
            if nums: return max(0, min(10, int(nums[0])))
            if "干潮後" in phase_str: return 1
            if "満潮前" in phase_str: return 9
            if "満潮後" in phase_str: return 1
            if "干潮前" in phase_str: return 9
            return 5
        res_df['step_val'] = res_df['潮位フェーズ'].apply(extract_step_smart)
        res_df['is_up'] = res_df['潮位フェーズ'].apply(lambda x: "下げ" not in str(x))
        res_df['hour_cat'] = res_df['datetime'].dt.hour.apply(lambda h: 0 if 4 <= h <= 19 else 1)
        res_df['repeat_idx'] = res_df.groupby(['step_val', 'is_up', 'hour_cat']).cumcount()
        def calculate_coords(row):
            if not row['is_up']: x_pos = row['step_val'] * 0.6
            else: x_pos = 6 + (row['step_val'] * 0.6)
            area_offset = 0 if row['hour_cat'] == 0 else 12.5
            jitter = row['repeat_idx'] * 0.18
            final_x = x_pos + area_offset + jitter
            final_y = 100 * np.cos(x_pos * np.pi / 6)
            return pd.Series([final_x, final_y])
        res_df[['x_sync', 'y_sync']] = res_df.apply(calculate_coords, axis=1)
        return res_df

    if not df_p.empty:
        df_p = process_coordinates(df_p)

    # --- 4. グラフ描画 ---
    if selected_species and not df_p.empty:
        display_df = df_p[df_p['魚種'].isin(selected_species)]
        
        # タイドグラフ
        fig = go.Figure()
        x_plot = np.linspace(0, 25, 1000)
        y_plot = [100 * np.cos((x % 12.5) * np.pi / 6) if (x % 12.5) <= 12 else 100 for x in x_plot]
        fig.add_trace(go.Scatter(x=x_plot, y=y_plot, mode='lines', line=dict(color='#00d4ff', width=2), fill='tozeroy', fillcolor='rgba(0, 212, 255, 0.1)', hoverinfo='skip'))
        
        for species in selected_species:
            spec_df = display_df[display_df['魚種'] == species]
            if spec_df.empty: continue
            symbols = spec_df['is_up'].apply(lambda x: 'triangle-up' if x else 'triangle-down')
            colors = spec_df['is_up'].apply(lambda x: '#00ffd0' if x else '#ff4b4b')
            hover_text = [f"<b>{dt.strftime('%m/%d %H:%M')}</b><br>全長: {size} cm<br>潮位: {tide} cm<br>{ph}" for dt, size, tide, ph in zip(spec_df['datetime'], spec_df['全長_cm'], spec_df['潮位_cm'], spec_df['潮位フェーズ'])]
            fig.add_trace(go.Scatter(x=spec_df['x_sync'], y=spec_df['y_sync'], mode='markers', name=species, marker=dict(size=14, symbol=symbols, color=colors, line=dict(width=1, color='white')), text=hover_text, hovertemplate="%{text}<extra></extra>"))

        fig.update_layout(xaxis=dict(tickvals=[6, 18.5], ticktext=["☀️ 昼", "🌙 夜"], range=[-0.5, 25.5], gridcolor='rgba(0,0,0,0)'), yaxis=dict(showticklabels=False, range=[-120, 150]), template="plotly_dark", height=350, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)

        # 棒グラフ (下げ0-9 -> 上げ1-10)
        st.write("📈 **フェーズ別ボリューム**")
        phase_order = [f"下げ{i}分" for i in range(10)] + [f"上げ{i}分" for i in range(1, 11)]
        display_df_copy = display_df.copy()
        display_df_copy['norm_phase'] = display_df_copy.apply(lambda r: f"{'上げ' if r['is_up'] else '下げ'}{r['step_val']}分", axis=1)
        counts = display_df_copy['norm_phase'].value_counts().reindex(phase_order, fill_value=0).reset_index()
        counts.columns = ['フェーズ', '件数']
        
        fig_bar = go.Figure()
        colors_bar = ['#ff4b4b' if '下げ' in p else '#00ffd0' for p in counts['フェーズ']]
        fig_bar.add_trace(go.Bar(x=counts['フェーズ'], y=counts['件数'], marker_color=colors_bar, hovertemplate="<b>%{x}</b>: %{y}件<extra></extra>"))
        fig_bar.update_layout(template="plotly_dark", height=250, margin=dict(l=5, r=5, t=10, b=30), xaxis=dict(tickmode='array', tickvals=["下げ0分", "下げ5分", "下げ9分", "上げ1分", "上げ5分", "上げ10分"], ticktext=["満潮", "下げ5", "干前", "干潮", "上げ5", "満潮"], categoryorder='array', categoryarray=phase_order), yaxis=dict(showgrid=False), showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("魚種を選択してください。")
