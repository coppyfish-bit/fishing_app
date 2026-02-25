import streamlit as st
import pandas as pd
from datetime import datetime

def show_matching_page(df):
    # --- 1. スタイル設定 ---
    st.markdown("""
        <style>
        .match-container { background: linear-gradient(180deg, #1e2630 0%, #0e1117 100%); padding: 30px; border-radius: 30px; text-align: center; border: 1px solid #333; }
        .recommend-card { background: #262730; border-radius: 20px; padding: 20px; margin: 15px auto; border-left: 5px solid #ff416c; text-align: left; }
        .highlight { color: #ff416c; font-weight: bold; font-size: 1.2rem; }
        .data-badge { background: #333; color: #00ffd0; padding: 2px 8px; border-radius: 5px; font-size: 0.8rem; margin-right: 5px; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🏹 SEABASS STRATEGY ARCHIVE")
    st.caption("本渡瀬戸の現況を解析し、過去の成功ログから今日の戦略を提案")

    if df is None or df.empty:
        st.warning("釣果データが不足しています。")
        return

    # セッション状態の初期化
    if 'current_match_data' not in st.session_state:
        st.session_state.current_match_data = {
            'tide': "中潮", 'wind': 3.0, 'wdir': "北", 'phase': "上げ3分", 'temp': 15.0
        }

    # --- 2. 本渡瀬戸のリアルタイムデータ取得 ---
    if st.button("🌊 本渡瀬戸の現在状況を同期する", use_container_width=True, type="primary"):
        with st.spinner("本渡瀬戸の気象・潮汐を分析中..."):
            try:
                import app  # app.pyの関数を借用
                LAT_HONDO, LON_HONDO = 32.4333, 130.2167
                now = datetime.now()
                
                # データ取得
                temp, wind_s, wind_d, _ = app.get_weather_data_openmeteo(LAT_HONDO, LON_HONDO, now)
                tide_details = app.get_tide_details('HS', now)
                m_age = app.get_moon_age(now)
                t_name = app.get_tide_name(m_age)
                
                # セッション更新
                st.session_state.current_match_data.update({
                    'tide': t_name, 'wind': float(wind_s) if wind_s else 3.0,
                    'wdir': wind_d if wind_d else "北", 'temp': temp if temp else 15.0,
                    'phase': tide_details['phase'] if tide_details else "不明"
                })
                st.toast("✅ 本渡瀬戸の現況を同期しました")
                st.rerun()
            except Exception as e:
                st.error(f"データ取得エラー: {e}")

    # 現在の条件を表示
    d = st.session_state.current_match_data
    st.markdown(f"""
        <div style="margin-bottom:20px;">
            <span class="data-badge">🌡️ {d['temp']}℃</span>
            <span class="data-badge">🌊 {d['tide']}</span>
            <span class="data-badge">⏳ {d['phase']}</span>
            <span class="data-badge">🚩 {d['wdir']}風 {d['wind']}m</span>
        </div>
    """, unsafe_allow_html=True)

    # --- 3. マッチング・分析ロジック ---
    # datetime型変換
    df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
    c_month = datetime.now().month

    # フィルタリング：同じ「潮名」かつ「季節（前後2ヶ月）」
    season_months = [(c_month-2)%12+1, (c_month-1)%12+1, c_month, (c_month%12)+1, ((c_month+1)%12)+1]
    match_df = df[
        (df['潮名'] == d['tide']) & 
        (df['datetime'].dt.month.isin(season_months))
    ].copy()

    st.markdown("---")
    
    if not match_df.empty:
        # 過去データから「今の風向き」に近いものをさらに優先（重み付け）
        wind_match = match_df[match_df['風向'] == d['wdir']]
        analysis_target = wind_match if not wind_match.empty else match_df

        best_place = analysis_target['場所'].mode()[0]
        best_phase = analysis_target['潮位フェーズ'].mode()[0]
        avg_size = analysis_target['全長_cm'].mean()
        best_lure = analysis_target['ルアー'].mode()[0]

        # --- 4. 提案の表示 ---
        st.subheader("🎯 今日の推奨戦略")
        
        
        st.markdown(f"""
        <div class="match-container">
            <div style="font-size: 1.1rem; color: #ccc; margin-bottom: 10px;">本渡瀬戸の現況と過去 {len(match_df)} 件の成功ログを照合：</div>
            <div style="font-size: 1.5rem; color: white; margin-bottom: 20px;">
                今日は <span class="highlight">{best_place}</span> での <span class="highlight">{best_phase}</span> が激アツです！
            </div>
            
            <div class="recommend-card">
                <div style="color: #888; font-size: 0.8rem;">STRATEGY / 戦略の根拠</div>
                <div style="margin-top: 5px;">
                    現在の<b>{d['tide']}・{d['phase']}</b>は、過去に平均 <b>{avg_size:.1f}cm</b> が出ている得意パターンです。<br>
                    特に今の<b>{d['wdir']}風</b>は、{best_place}においてベイトが寄りやすい条件に合致しています。
                </div>
            </div>

            <div class="recommend-card" style="border-left-color: #00ffd0;">
                <div style="color: #888; font-size: 0.8rem;">WEAPON / 推奨ルアー</div>
                <div style="margin-top: 5px; color: #00ffd0; font-weight: bold;">{best_lure}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("📸 類似コンディションでの過去の栄光"):
            cols = st.columns(3)
            for i, (idx, row) in enumerate(analysis_target.head(3).iterrows()):
                with cols[i % 3]:
                    if pd.notna(row['filename']):
                        st.image(row['filename'], caption=f"{row['date']} - {row['全長_cm']}cm")

    else:
        st.error(f"😭 現在の条件（{d['tide']}・季節）に一致するデータがまだありません。")
        st.info("データが溜まるまで、別の潮名でシミュレーションするか、新しい記録を増やしましょう！")
