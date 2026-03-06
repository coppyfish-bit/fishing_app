import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import plotly.graph_objects as go
import requests
import numpy as np

def create_mini_tide_chart(row):
    try:
        dt = row['datetime_parsed']
        hit_hour = dt.hour + dt.minute / 60.0
        phase_str = str(row.get('潮位フェーズ', '不明'))
        
        # 波のデータ
        hours = np.linspace(0, 24, 100)
        tide_curve = 70 * np.sin(hours * (2 * np.pi / 12.5)) + 120

        fig = go.Figure()

        # --- 1. 背景の塗り分け（昼と夜） ---
        # 0時〜6時（夜）、18時〜24時（夜）を暗く、6時〜18時（昼）を少し明るく
        fig.add_vrect(x0=0, x1=6, fillcolor="#06090f", opacity=1, layer="below", line_width=0)
        fig.add_vrect(x0=6, x1=18, fillcolor="#161b22", opacity=1, layer="below", line_width=0)
        fig.add_vrect(x0=18, x1=24, fillcolor="#06090f", opacity=1, layer="below", line_width=0)

        # 潮汐曲線
        fig.add_trace(go.Scatter(
            x=hours, y=tide_curve,
            mode='lines',
            line=dict(color='#00ffd0', width=1.5),
            fill='tozeroy',
            fillcolor='rgba(0, 255, 208, 0.08)',
            hoverinfo='skip'
        ))

        # --- 2. プロットの高さ計算 ---
        plot_y = 120
        if "上げ" in phase_str:
            step = int(''.join(filter(str.isdigit, phase_str))) if any(c.isdigit() for c in phase_str) else 5
            plot_y = 50 + (step * 14)
        elif "下げ" in phase_str:
            step = int(''.join(filter(str.isdigit, phase_str))) if any(c.isdigit() for c in phase_str) else 5
            plot_y = 190 - (step * 14)

        # --- 3. 夜釣りのプロットを「光らせる」 ---
        is_night = hit_hour < 6 or hit_hour >= 18
        main_color = "#ffca00" if is_night else "#ff4b4b" # 夜は黄色、昼は赤
        
        # 外光（光って見えるように重ねる）
        if is_night:
            fig.add_trace(go.Scatter(
                x=[hit_hour], y=[plot_y],
                mode='markers',
                marker=dict(color=main_color, size=20, opacity=0.3),
                hoverinfo='skip'
            ))

        # メインの×印
        fig.add_trace(go.Scatter(
            x=[hit_hour], y=[plot_y],
            mode='markers',
            marker=dict(
                color=main_color, size=12, symbol='x',
                line=dict(width=2, color="white")
            ),
            name='Hit!'
        ))

        fig.update_layout(
            height=90, margin=dict(l=5, r=5, t=5, b=5),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, range=[0, 24], showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, range=[0, 240], showticklabels=False),
        )
        return fig
    except:
        return None

def show_gallery_page(df):
    # --- 1. スタイル設定（CSS） ---
    st.markdown("""
        <style>
        .stExpander {
            border: none !important;
            background-color: #1e2630 !important;
            border-radius: 15px !important;
            margin-bottom: 20px !important;
        }
        .result-count {
            color: #00ffd0;
            font-size: 0.9rem;
            font-weight: bold;
            letter-spacing: 0.1rem;
            margin-bottom: 15px;
            text-transform: uppercase;
        }
        .fish-card {
            position: relative;
            width: 100%;
            border-radius: 20px 20px 0 0; /* 下側を平らにしてグラフと結合 */
            overflow: hidden;
            background: #0e1117;
            box-shadow: 0 10px 25px rgba(0,0,0,0.6);
            transition: transform 0.3s ease;
        }
        .fish-card:hover {
            transform: translateY(-5px);
        }
        .fish-img {
            width: 100%;
            aspect-ratio: 1/1;
            object-fit: cover;
            display: block;
            mask-image: linear-gradient(to bottom, black 70%, transparent 100%);
            -webkit-mask-image: linear-gradient(to bottom, black 70%, transparent 100%);
        }
        .overlay-content {
            position: absolute;
            bottom: 0;
            width: 100%;
            padding: 15px;
            background: linear-gradient(to top, rgba(0,0,0,1) 0%, rgba(0,0,0,0.8) 60%, transparent 100%);
            color: #ffffff;
        }
        .fish-title {
            color: #00ffd0;
            font-size: 1.1rem;
            font-weight: 900;
            margin-bottom: 4px;
        }
        .info-row {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.8rem;
            margin-bottom: 2px;
            color: #cccccc;
        }
        .tide-badge {
            display: inline-block;
            background: rgba(0, 255, 208, 0.15);
            color: #00ffd0;
            padding: 2px 10px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: bold;
            margin-top: 5px;
            border: 1px solid rgba(0, 255, 208, 0.3);
        }
        /* グラフエリアのスタイル */
        .chart-container {
            background: #0e1117;
            border-radius: 0 0 20px 20px;
            padding: 0 10px 10px 10px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.6);
            margin-bottom: 25px;
            border-top: 1px solid rgba(255,255,255,0.05);
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🖼️ GALLERY")

    if st.button("🔄 最新データに更新 (キャッシュ破棄)"):
        st.cache_data.clear()
        st.success("深淵の記憶を更新した。")
        time.sleep(1)
        st.rerun()
    
    if df is None or df.empty:
        st.info("No records found.")
        return

    df_gallery = df.copy()

    # --- 2. 前処理 ---
    def clean_datetime_str(x):
        if pd.isna(x): return x
        return str(x).replace("/", "-").strip()

    df_gallery['datetime_tmp'] = df_gallery['datetime'].apply(clean_datetime_str)
    df_gallery['datetime_parsed'] = pd.to_datetime(df_gallery['datetime_tmp'], errors='coerce')
    df_gallery = df_gallery.dropna(subset=['datetime_parsed'])

    # --- 3. 検索パネル ---
    with st.expander("🔍 Filter", expanded=False):
        col_f, col_p = st.columns(2)
        fish_list = ["すべて"] + sorted(df_gallery['魚種'].unique().tolist())
        selected_fish = col_f.selectbox("🐟 SPECIES", fish_list)
        place_list = ["すべて"] + sorted(df_gallery['場所'].unique().tolist())
        selected_place = col_p.selectbox("📍 FIELD", place_list)

        absolute_min = df_gallery['datetime_parsed'].min().date() if not df_gallery.empty else date(2024, 1, 1)
        date_range = st.date_input(
            "📅 DATE RANGE", 
            value=(absolute_min, date.today()), 
            min_value=absolute_min, 
            max_value=date.today()
        )

    # フィルタリング
    if selected_fish != "すべて":
        df_gallery = df_gallery[df_gallery['魚種'] == selected_fish]
    if selected_place != "すべて":
        df_gallery = df_gallery[df_gallery['場所'] == selected_place]
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date, end_date = date_range
        df_gallery = df_gallery[(df_gallery['datetime_parsed'].dt.date >= start_date) & (df_gallery['datetime_parsed'].dt.date <= end_date)]

    df_gallery = df_gallery.sort_values(by=['datetime_parsed', 'datetime_tmp'], ascending=[False, False])
    valid_rows = df_gallery[df_gallery['filename'].notna() & (df_gallery['filename'].astype(str).str.lower() != "nan")]

    if valid_rows.empty:
        st.warning("No records match your criteria.")
        return

    st.markdown(f'<p class="result-count">Showing {len(valid_rows)} captures</p>', unsafe_allow_html=True)

    # --- 4. グリッド表示 ---
    for i in range(0, len(valid_rows), 3):
        chunk = valid_rows.iloc[i : i + 3]
        cols = st.columns(3) 
        for j, (_, row) in enumerate(chunk.iterrows()):
            with cols[j]:
                img_url = row.get("filename")
                lat, lon = row.get('lat'), row.get('lon')
                map_url = f"https://www.google.com/maps?q={lat},{lon}" if pd.notnull(lat) and lat != 0 else "#"
                dt_val = row.get('datetime_parsed')
                display_dt = dt_val.strftime('%Y.%m.%d %H:%M')
                
                fish_info = f"{row.get('魚種', '-')} / {row.get('全長_cm', '-')}cm"
                wind_info = f"{row.get('風向', '')}{row.get('風速', '-')}m"
                weather_info = f"🌡️{row.get('気温', '-')}℃ / 💨{wind_info}"
                tide_cm = f"{row.get('潮位_cm', '-')}cm"

                # カード(HTML)
                st.markdown(f"""
                <a href="{map_url}" target="_blank" style="text-decoration: none;">
                    <div class="fish-card">
                        <img src="{img_url}" class="fish-img">
                        <div class="overlay-content">
                            <div class="fish-title">{fish_info}</div>
                            <div class="info-row">📍 {row.get('場所', '-')}</div>
                            <div class="info-row">📅 {display_dt}</div>
                            <div class="info-row">{weather_info}</div>
                            <div class="tide-badge">🌊 {row.get('潮位フェーズ', '-')} ({tide_cm})</div>
                        </div>
                    </div>
                </a>
                """, unsafe_allow_html=True)
                
                # グラフ(Plotly)をコンテナに入れて表示
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                fig = create_mini_tide_chart(row)
                if fig:
                    # keyを追加して重複エラーを回避！
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=f"chart_{row.name}_{i}_{j}")
                st.markdown('</div>', unsafe_allow_html=True)



