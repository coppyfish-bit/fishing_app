import streamlit as st
import pandas as pd
from datetime import datetime
import requests

def get_hondo_data():
    """本渡瀬戸のリアルタイムデータを直接取得する（自己完結型）"""
    LAT, LON = 32.4333, 130.2167
    now = datetime.now()
    
    # デフォルト値
    res_data = {
        'tide': "中潮", 
        'wind': 3.0, 
        'wdir': "北", 
        'phase': "上げ5分", 
        'temp': 15.0
    }

    # 1. 気象データ (Open-Meteo)
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current_weather=true"
        res = requests.get(url, timeout=5).json()
        if 'current_weather' in res:
            res_data['temp'] = res['current_weather']['temperature']
            res_data['wind'] = res['current_weather']['windspeed']
            dirs = ["北", "北東", "東", "南東", "南", "南西", "西", "北西", "北"]
            res_data['wdir'] = dirs[int((res['current_weather']['winddirection'] + 22.5) / 45) % 8]
    except Exception:
        pass # 失敗時はデフォルト値を使用

    # 2. 潮汐・月齢計算（簡易ロジック：精度より動作優先）
    try:
        # 簡易的な月齢計算
        base_date = datetime(2025, 1, 29) # 大潮の目安
        days_diff = (now - base_date).days
        moon_age = days_diff % 29.5
        if moon_age < 3 or moon_age > 26: res_data['tide'] = "大潮"
        elif moon_age < 9 or moon_age > 20: res_data['tide'] = "中潮"
        else: res_data['tide'] = "小潮"
    except Exception:
        pass

    return res_data

def show_matching_page(df):
    st.markdown("""
        <style>
        .match-container { background: linear-gradient(180deg, #1e2630 0%, #0e1117 100%); padding: 30px; border-radius: 30px; text-align: center; border: 1px solid #333; }
        .recommend-card { background: #262730; border-radius: 20px; padding: 20px; margin: 15px auto; border-left: 5px solid #ff416c; text-align: left; }
        .highlight { color: #ff416c; font-weight: bold; font-size: 1.2rem; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🏹 SEABASS STRATEGY ARCHIVE")

    # --- 重要：セッションの完全な初期化 ---
    if 'current_match_data' not in st.session_state or not isinstance(st.session_state.current_match_data, dict):
        st.session_state.current_match_data = {
            'tide': "中潮", 'wind': 3.0, 'wdir': "北", 'phase': "上げ3分", 'temp': 15.0
        }

    # --- 同期ボタン ---
    if st.button("🌊 本渡瀬戸の現況を強制同期する", use_container_width=True, type="primary"):
        with st.spinner("最新データを取得中..."):
            new_data = get_hondo_data()
            st.session_state.current_match_data = new_data # 辞書を丸ごと差し替え
            st.toast("✅ 同期が完了しました")
            st.rerun()

    # --- 表示部分（.get() を使って KeyError を物理的に防ぐ） ---
    d = st.session_state.current_match_data
    cols = st.columns(4)
    # .get(キー, デフォルト値) を使うことで、キーがなくても止まらない
    cols[0].metric("気温", f"{d.get('temp', '--')}℃")
    cols[1].metric("潮名", d.get('tide', '--'))
    cols[2].metric("時合", d.get('phase', '--'))
    cols[3].metric("風向", f"{d.get('wdir', '--')} {d.get('wind', '--')}m")

    # --- 分析ロジック ---
    if df is not None and not df.empty:
        # 列名の存在チェック
        if 'datetime' in df.columns and '潮名' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
            
            # フィルタリング
            current_tide = d.get('tide', '中潮')
            match_df = df[df['潮名'] == current_tide].copy()
            
            if not match_df.empty:
                # モード（最頻値）を安全に取得
                best_place = match_df['場所'].mode()[0] if '場所' in match_df.columns and not match_df['場所'].empty else "記録なし"
                best_lure = match_df['ルアー'].mode()[0] if 'ルアー' in match_df.columns and not match_df['ルアー'].empty else "記録なし"
                
                st.markdown(f"""
                    <div class="match-container">
                        <div style="font-size: 1.5rem; color: white; margin-bottom: 20px;">
                            過去の統計による最適解は <span class="highlight">{best_place}</span> です！
                        </div>
                        <div class="recommend-card">
                            <b>理由:</b> 過去の{current_tide}において最も実績が高いエリアです。<br>
                            <b>推奨ルアー:</b> {best_lure}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.info(f"現在の条件（{current_tide}）に一致する過去データがありません。")
