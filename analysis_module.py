import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    # CSS: ホバーを有効化。スマホスクロールを妨げない設定
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
    places = sorted(df["場所"].unique()) if "場所" in df.columns else []
    selected_place = st.selectbox("📍 場所を選択", places, key="ana_place")
    df_p_base = df[df["場所"] == selected_place].copy()
    
    all_species = sorted(df_p_base["魚種"].unique()) if "魚種" in df_p_base.columns else []
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
        fig.add_trace(go.Scatter(x=x_plot, y=y_plot, mode='lines', line=dict(color='#00d4ff', width=2), fill='tozeroy', fillcolor='rgba(0, 212, 255, 0.1)', hoverinfo='skip', showlegend=False))
        
        for species in selected_species:
            spec_df = display_df[display_df['魚種'] == species]
            if spec_df.empty: continue
            
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
            xaxis=dict(tickvals=[6.25, 18.75], ticktext=["☀️ 昼", "🌙 夜"], range=[-0.5, 25.5], gridcolor='rgba(255,255,255,0.1)'),
            yaxis=dict(showticklabels=False, range=[-120, 150]),
            template="plotly_dark", height=350, margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            dragmode=False
        )
        
        st.write("🌊 タイド分布")
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        # --- 4. 釣果詳細 (セレクトボックス方式) ---
        st.markdown("---")
        st.subheader("📌 釣果詳細")
        fish_options = {f"{r['date']} {r['time']} - {r['魚種']}": i for i, r in display_df.iterrows()}
        selected_label = st.selectbox("詳細を表示する釣果を選択", ["選択してください"] + list(fish_options.keys()))

        if selected_label != "選択してください":
            idx = fish_options[selected_label]
            fish_data = df.loc[idx]
            c1, c2 = st.columns([1, 1.2])
            with c1:
                img_path = fish_data.get('filename', None)
                if img_path and pd.notna(img_path):
                    st.image(img_path, use_container_width=True)
                else:
                    st.info("📸 写真なし")
            with c2:
                st.write(f"**全長:** {fish_data.get('全長_cm', '-')} cm")
                st.write(f"**潮名:** {fish_data.get('潮名', '-')}")
                st.write(f"**潮位:** {fish_data.get('潮位_cm', '-')} cm")
                st.write(f"**ルアー:** {fish_data.get('ルアー', '-')}")
                st.write(f"**備考:** {fish_data.get('備考', '-')}")

        st.markdown("---")

        # --- 5. 棒グラフ ---
        st.write("📈 フェーズ別ボリューム")
        phase_order = [f"下げ{i}分" for i in range(10)] + [f"上げ{i}分" for i in range(1, 11)]
        display_df_copy = display_df.copy()
        display_df_copy['norm_phase'] = display_df_copy.apply(lambda r: f"{'上げ' if r['is_up'] else '下げ'}{r['step_val']}分", axis=1)
        counts = display_df_copy['norm_phase'].value_counts().reindex(phase_order, fill_value=0).reset_index()
        counts.columns = ['フェーズ', '件数']
        
        fig_bar = go.Figure()
        colors_bar = ['#ff4b4b' if '下げ' in p else '#00ffd0' for p in counts['フェーズ']]
        fig_bar.add_trace(go.Bar(x=counts['フェーズ'], y=counts['件数'], marker_color=colors_bar))
        fig_bar.update_layout(
            template="plotly_dark", height=230, margin=dict(l=5, r=5, t=10, b=30),
            xaxis=dict(tickmode='array', tickvals=["下げ0分", "下げ5分", "下げ9分", "上げ1分", "上げ5分", "上げ10分"],
                       ticktext=["満", "下5", "干前", "干", "上5", "満"], categoryorder='array', categoryarray=phase_order),
            yaxis=dict(showgrid=False), showlegend=False
        )
        st.plotly_chart(fig_bar, use_container_width=True, config={'staticPlot': True})

    else:
        st.info("魚種を選択してください。")
