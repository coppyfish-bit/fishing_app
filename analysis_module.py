import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 シームレス・時合精密解析 (座標同期修正版)")

    if df.empty:
        st.info("データがありません。")
        return

    # --- 1. フィルタリング設定 ---
    col_f1, col_f2 = st.columns([1, 2])
    
    with col_f1:
        places = sorted(df["場所"].unique())
        selected_place = st.selectbox("📍 場所を選択", places, key="ana_place")
    
    df_p_base = df[df["場所"] == selected_place].copy()

    with col_f2:
        all_species = sorted(df_p_base["魚種"].unique())
        priority_species = ["スズキ", "ヒラスズキ"]
        default_selection = [s for s in priority_species if s in all_species]
        
        if not default_selection and not df_p_base.empty:
            top_species = df_p_base["魚種"].value_counts().idxmax()
            default_selection = [top_species]
        
        selected_species = st.multiselect("🐟 魚種を選択", all_species, default=default_selection, key="ana_species")

    # --- 2. データの前処理 ---
    df_p = df_p_base.copy()
    
    def clean_datetime_safe(val):
        if pd.isna(val): return None
        s = str(val).strip()
        s = s.translate(str.maketrans('０１２３４５６７８９：／－', '0123456789:/-'))
        s = s.replace('年', '/').replace('月', '/').replace('日', ' ').replace('時', ':').replace('分', '')
        s = re.sub(r'[^0-9:/\-\s]', '', s)
        return s if s else None

    def parse_dt(s):
        if not s: return pd.NaT
        dt = pd.to_datetime(s, errors='coerce')
        if pd.notna(dt): return dt
        for fmt in ('%Y-%m-%d %H:%M', '%Y/%m/%d %H:%M'):
            try:
                return pd.to_datetime(s, format=fmt)
            except:
                continue
        return pd.NaT

    df_p['datetime_str'] = df_p['datetime'].apply(clean_datetime_safe)
    df_p['datetime'] = df_p['datetime_str'].apply(parse_dt)
    df_p = df_p.dropna(subset=['datetime'])

    # --- 3. 座標計算ロジック (同期バグ修正版) ---
    def process_coordinates(target_df):
        if target_df.empty:
            return target_df
        
        res_df = target_df.copy()
        
        def extract_step(phase_str):
            nums = re.findall(r'\d+', str(phase_str).translate(str.maketrans('０１２３４５６７８９', '0123456789')))
            step = int(nums[0]) if nums else 5
            return max(0, min(10, step))

        res_df['step_val'] = res_df['潮位フェーズ'].apply(extract_step)
        res_df['is_up'] = res_df['潮位フェーズ'].apply(lambda x: "下げ" not in str(x))
        res_df['hour_cat'] = res_df['datetime'].dt.hour.apply(lambda h: 0 if 4 <= h <= 19 else 1)
        
        # 重なり判定用
        res_df['repeat_idx'] = res_df.groupby(['step_val', 'is_up', 'hour_cat']).cumcount()

        def calculate_coords(row):
            # X軸の計算
            x_base = row['step_val'] * 0.6 if not row['is_up'] else 6 + (row['step_val'] * 0.6)
            area_offset = 0 if row['hour_cat'] == 0 else 12.5
            jitter = row['repeat_idx'] * 0.15
            final_x = x_base + area_offset + jitter
            
            # Y軸の計算 (重要: x_baseをそのままcosに入れることで、背景の波形と完全同期させる)
            # 背景波形は y = 100 * cos(x * pi / 6)
            final_y = 100 * np.cos(x_base * np.pi / 6)
            
            return pd.Series([final_x, final_y])

        res_df[['x_sync', 'y_sync']] = res_df.apply(calculate_coords, axis=1)
        return res_df

    if not df_p.empty:
        df_p = process_coordinates(df_p)

    # --- 4. グラフ描画 ---
    if selected_species and not df_p.empty:
        display_df = df_p[df_p['魚種'].isin(selected_species)]
        st.caption(f"💡 現在表示中の釣果: {len(display_df)} 件")
        
        fig = go.Figure()
        
        # 背景のシームレス曲線 (x=0〜25)
        x_line = np.linspace(0, 25, 1000)
        # y = 100 * cos( (x % 12.5) * pi / 6 ) とすることで、0-12.5 と 12.5-25 で同じ波形を繰り返す
        y_line = 100 * np.cos((x_line % 12.5) * np.pi / 6)
        
        fig.add_trace(go.Scatter(
            x=x_line, y=y_line, 
            mode='lines', 
            line=dict(color='#00d4ff', width=3, shape='spline'),
            fill='tozeroy', 
            fillcolor='rgba(0, 212, 255, 0.2)',
            hoverinfo='skip',
            name='潮位'
        ))

        fig.add_vline(x=12.25, line_width=1, line_dash="dot", line_color="rgba(255,255,255,0.3)")

        for species in selected_species:
            spec_df = display_df[display_df['魚種'] == species]
            if spec_df.empty: continue
            
            is_up_list = spec_df['is_up']
            symbols = is_up_list.apply(lambda x: 'triangle-up' if x else 'triangle-down')
            colors = is_up_list.apply(lambda x: '#00ffd0' if x else '#ff4b4b')
            
            fig.add_trace(go.Scatter(
                x=spec_df['x_sync'], y=spec_df['y_sync'],
                mode='markers',
                name=species,
                marker=dict(size=18, symbol=symbols, color=colors, line=dict(width=1.5, color='white')),
                text=spec_df['datetime'].dt.strftime('%m/%d %H:%M'),
                hovertemplate="<b>%{name}</b><br>%{text}<extra></extra>"
            ))

        fig.update_layout(
            xaxis=dict(
                tickvals=[6, 18.5], ticktext=["☀️ 昼 エリア", "🌙 夜 エリア"],
                range=[-0.5, 25.5], gridcolor='rgba(255,255,255,0)', zeroline=False
            ),
            yaxis=dict(
                tickvals=[100, 0, -100], ticktext=["満潮", "中間", "干潮"],
                range=[-120, 150], gridcolor='rgba(255,255,255,0.1)'
            ),
            template="plotly_dark", height=550, margin=dict(l=10, r=10, t=20, b=60)
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("表示する魚種を選択してください。")
