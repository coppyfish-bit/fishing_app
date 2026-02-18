import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    # CSSガードを解除し、マウスオーバーとクリックを有効化
    st.markdown("""
        <style>
        [data-testid="stPlotlyChart"] {
            pointer-events: auto !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.subheader("📊 時合精密解析 (インタラクティブ版)")

    if df.empty:
        st.info("データがありません。")
        return

    # --- 1. 場所・魚種の選択 ---
    places = sorted(df["場所"].unique())
    selected_place = st.selectbox("📍 場所を選択", places, key="ana_place")
    df_p_base = df[df["場所"] == selected_place].copy()
    
    all_species = sorted(df_p_base["魚種"].unique())
    selected_species = st.multiselect("🐟 魚種を選択", all_species, default=all_species[:1] if all_species else [], key="selected_species")

    # --- 2. データ前処理 (座標計算ロジック) ---
    def process_coords(target_df):
        res_df = target_df.copy()
        def extract_step(ph):
            ph_str = str(ph).translate(str.maketrans('０１２３４５６７８９', '0123456789'))
            nums = re.findall(r'\d+', ph_str)
            if nums: return max(0, min(10, int(nums[0])))
            if any(x in ph_str for x in ["干潮後", "上げ始め"]): return 1
            if "満潮前" in ph_str: return 9
            if any(x in ph_str for x in ["満潮後", "下げ始め"]): return 1
            if "干潮前" in ph_str: return 9
            return 5

        res_df['is_up'] = res_df['潮位フェーズ'].apply(lambda x: "下げ" not in str(x))
        res_df['step_val'] = res_df['潮位フェーズ'].apply(extract_step)
        res_df['hour_cat'] = pd.to_datetime(res_df['datetime'], errors='coerce').dt.hour.apply(lambda h: 0 if 4 <= h <= 19 else 1)
        res_df['repeat_idx'] = res_df.groupby(['step_val', 'is_up', 'hour_cat']).cumcount()

        def calc(row):
            x_base = row['step_val'] * 0.625 if not row['is_up'] else 6.25 + (row['step_val'] * 0.625)
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
        display_df = df_p[df_p['魚種'].isin(selected_species)]
        
        fig = go.Figure()
        x_plot = np.linspace(0, 25, 500)
        y_plot = [100 * np.cos((x % 12.5) * np.pi / 6.25) for x in x_plot]
        fig.add_trace(go.Scatter(x=x_plot, y=y_plot, mode='lines', line=dict(color='rgba(0, 212, 255, 0.2)', width=1), fill='tozeroy', hoverinfo='skip'))
        
        for species in selected_species:
            spec_df = display_df[display_df['魚種'] == species]
            if spec_df.empty: continue
            
            # マウスオーバー時に表示するテキストを作成
            hover_text = spec_df.apply(lambda r: f"魚種: {r['魚種']}<br>サイズ: {r['サイズ']}cm<br>時間: {r['datetime']}<br>潮位: {r['潮位フェーズ']}", axis=1)
            
            fig.add_trace(go.Scatter(
                x=spec_df['x_sync'], y=spec_df['y_sync'],
                mode='markers', name=species,
                text=hover_text,
                hoverinfo='text',
                customdata=spec_df.index, # クリック時に元のデータのインデックスを特定するため
                marker=dict(size=12, symbol=spec_df['is_up'].apply(lambda x: 'triangle-up' if x else 'triangle-down'),
                            line=dict(width=1, color='white'))
            ))
        
        fig.update_layout(xaxis=dict(tickvals=[6.25, 18.75], ticktext=["昼", "夜"]), yaxis=dict(showticklabels=False), template="plotly_dark", height=350, margin=dict(l=10, r=10, t=10, b=10), clickmode='event+select')

        # グラフの表示とクリックイベントの取得
        selected_point = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

        # --- 4. クリックした釣果の詳細表示 ---
        if selected_point and "points" in selected_point and len(selected_point["points"]) > 0:
            idx = selected_point["points"][0]["customdata"]
            fish_data = df.loc[idx]
            
            st.markdown("---")
            st.success(f"📌 **釣果詳細: {fish_data['魚種']}**")
            
            col1, col2 = st.columns([1, 1])
            with col1:
                # 写真があれば表示
                if "画像" in fish_data and pd.notna(fish_data["画像"]):
                    st.image(fish_data["画像"], caption=f"{fish_data['魚種']} {fish_data['サイズ']}cm", use_container_width=True)
                else:
                    st.info("写真はありません")
            
            with col2:
                st.write(f"**日時:** {fish_data['datetime']}")
                st.write(f"**サイズ:** {fish_data['サイズ']} cm")
                st.write(f"**潮位:** {fish_data['潮位フェーズ']}")
                if "メモ" in fish_data:
                    st.write(f"**メモ:** {fish_data['メモ']}")
        else:
            st.info("グラフのプロットをクリックすると、写真と詳細が表示されます。")

    else:
        st.info("魚種を選択してください。")
