import streamlit as st
import pandas as pd
from datetime import datetime, date
import time
import plotly.graph_objects as go
import requests
import numpy as np

def create_mini_tide_chart(row):
    """
    レコードのデータから24時間のタイドグラフを生成する
    """
    try:
        dt = row['datetime_parsed']
        # 釣れた時間の計算 (例: 15:30 -> 15.5)
        hit_hour = dt.hour + dt.minute / 60.0
        hit_cm = row.get('潮位_cm', 0)
        
        # --- 潮汐カーブのデータ準備 ---
        hours = list(range(24))
        # 本来はGitHubから取得したhourlyデータを入れたいが、
        # gallery単体で動くよう、簡易的な潮汐カーブを生成
        # (満潮・干潮の時間を考慮したサインカーブ)
        tide_curve = 80 * np.sin((np.array(hours) - 6) * (2 * np.pi / 12.5)) + 130

        fig = go.Figure()

        # 1. 潮汐曲線（水色のライン）
        fig.add_trace(go.Scatter(
            x=hours, y=tide_curve,
            mode='lines',
            line=dict(color='#00ffd0', width=2, shape='spline'),
            fill='tozeroy',
            fillcolor='rgba(0, 255, 208, 0.05)',
            hoverinfo='skip'
        ))

        # 2. ヒットポイント（釣れた瞬間の赤い×）
        # もし潮位データがNaNなら、カーブ上の値を推測してプロット
        plot_y = hit_cm if pd.notnull(hit_cm) and hit_cm != '-' else tide_curve[dt.hour]
        
        fig.add_trace(go.Scatter(
            x=[hit_hour], 
            y=[plot_y],
            mode='markers',
            marker=dict(
                color='#ff4b4b', 
                size=12, 
                symbol='x',
                line=dict(width=2, color="white")
            ),
            name='Hit!'
        ))

        # レイアウト設定（超ミニマム）
        fig.update_layout(
            height=80, 
            margin=dict(l=5, r=5, t=5, b=5),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=False,
            xaxis=dict(
                showgrid=False, zeroline=False, range=[0, 23], 
                tickvals=[0, 6, 12, 18, 23],
                ticktext=['0h', '6', '12', '18', '24'],
                tickfont=dict(size=8, color="#666")
            ),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
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
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                st.markdown('</div>', unsafe_allow_html=True)
