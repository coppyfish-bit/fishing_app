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
        .data-badge { background: #333; color: #00ffd0; padding: 4px 10px; border-radius: 8px; font-size: 0.9rem; margin-right: 5px; border: 1px solid #444; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🏹 SEABASS STRATEGY ARCHIVE")

    if df is None or df.empty:
        st.warning("釣果データが不足しています。")
        return

    # --- 2. セッション状態の初期化 ---
    if 'current_match_data' not in st.session_state:
        st.session_state.current_match_data = {
            'tide': "中潮", 'wind': 3.0, 'wdir': "北", 'phase': "上げ3分", 'temp': 15.0
        }

    # --- 3. 本渡瀬戸のリアルタイムデータ取得 ---
    if st.button("🌊 本渡瀬戸の現在状況を同期する", use_container_width=True, type="primary"):
        with st.spinner("本渡瀬戸の気象・潮汐を分析中..."):
            try:
                import app
                LAT_HONDO, LON_HONDO = 32.4333, 130.2167
                now = datetime.now()
                
                temp, wind_s, wind_d, _ = app.get_weather_data_openmeteo(LAT_HONDO, LON_HONDO, now)
                tide_details = app.get_tide_details('HS', now)
                m_age = app.get_moon_age(now)
                t_name = app.get_tide_name(m_age)
                
                st.session_state.current_match_data.update({
                    'tide': t_name, 'wind': float(wind_s) if wind_s else 3.0,
                    'wdir': wind_d if wind_d else "北", 'temp': temp if temp else 15.0,
                    'phase': tide_details['phase'] if tide_details else "不明"
                })
                st.toast("✅ 本渡瀬戸の現況を同期しました")
                st.rerun()
            except Exception as e:
                # 重複IDエラー等は無視してリラン
                if "multiple" in str(e) or "Duplicate" in str(e):
                    st.rerun()
                else:
                    st.error(f"データ取得エラー: {e}")

    # --- 4. 現在の条件を表示（.get() でエラー回避） ---
    d = st.session_state.current_match_data
    st.markdown(f"""
        <div style="margin-bottom:25px; display: flex; flex-wrap: wrap; gap: 8px;">
            <span class="data-badge">🌡️ {d.get('temp', '--')}℃</span>
            <span class="data-badge">🌊 {d.get('tide', '--')}</span>
            <span class="data-badge">⏳ {d.get('phase', '--')}</span>
            <span class="data-badge">🚩 {d.get('wdir', '--')}風 {d.get('wind', '--')}m</span>
        </div>
    """, unsafe_allow_html=True)

    # --- 5. マッチング・分析ロジック ---
    df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
    c_month = datetime.now().month

    # フィルタ：同じ潮名 ＋ 季節（前後2ヶ月）
    season_months = [(c_month-2)%12+1, (c_month-1)%12+1, c_month, (c_month%12)+1, ((c_month+1)%12)+1]
    match_df = df[
        (df['潮名'] == d.get('tide')) & 
        (df['datetime'].dt.month.isin(season_months))
    ].copy()

    st.markdown("---")
    
    if not match_df.empty:
        # 今の風向きに近いデータを優先
        wind_match = match_df[match_df['風向'] == d.get('wdir')]
        target = wind_match if not wind_match.empty else match_df

        best_place = target['場所'].mode()[0] if '場所' in target.columns else "不明"
        best_phase = target['潮位フェーズ'].mode()[0] if '潮位フェーズ' in target.columns else "不明"
        avg_size = target['全長_cm'].mean() if '全長_cm' in target.columns else 0
        best_lure = target['ルアー'].mode()[0] if 'ルアー' in target.columns else "実績ルアーを参照"

        # 推奨戦略の表示
        st.subheader("🎯 今日の推奨戦略")
        
        
        st.markdown(f"""
        <div class="match-container">
            <div style="font-size: 1.1rem; color: #ccc; margin-bottom: 10px;">過去 {len(match_df)} 件の成功ログから導き出された最適解：</div>
            <div style="font-size: 1.5rem; color: white; margin-bottom: 20px;">
                狙い目は <span class="highlight">{best_place}</span> での <span class="highlight">{best_phase}</span> です！
            </div>
            
            <div class="recommend-card">
                <div style="color: #888; font-size: 0.8rem;">REASON / 根拠</div>
                <div style="margin-top: 5px;">
                    現在の<b>{d.get('tide')}・{d.get('phase')}</b>という条件は、過去に <b>{avg_size:.1f}cm</b> クラスがヒットしている鉄板パターンです。
                </div>
            </div>

            <div class="recommend-card" style="border-left-color: #00ffd0;">
                <div style="color: #888; font-size: 0.8rem;">WEAPON / 推奨ルアー</div>
                <div style="margin-top: 5px; color: #00ffd0; font-weight: bold;">{best_lure}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander("📸 同条件での過去のヒット事例"):
            cols = st.columns(3)
            for i, (idx, row) in enumerate(target.head(3).iterrows()):
                with cols[i % 3]:
                    if pd.notna(row['filename']):
                        st.image(row['filename'], caption=f"{row['date']}")

    else:
        st.info(f"現在、{d.get('tide')}・{c_month}月付近のデータが蓄積されていません。")
        st.write("他の潮名を選択するか、新しい釣果を記録してデータを育てましょう！")
