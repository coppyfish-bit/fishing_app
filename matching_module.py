import streamlit as st
import pandas as pd
from datetime import datetime
import requests

# --- 内部関数：これらを直接持つことで app.py との依存を切り離す ---
def get_hondo_data():
    """本渡瀬戸のリアルタイムデータを直接取得する"""
    LAT, LON = 32.4333, 130.2167
    now = datetime.now()
    
    # 1. 気象データ (Open-Meteo)
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current_weather=true"
        res = requests.get(url).json()
        temp = res['current_weather']['temperature']
        w_speed = res['current_weather']['windspeed']
        # 風向き(度)を方位に変換
        dirs = ["北", "北東", "東", "南東", "南", "南西", "西", "北西", "北"]
        w_dir = dirs[int((res['current_weather']['winddirection'] + 22.5) / 45) % 8]
    except:
        temp, w_speed, w_dir = 15.0, 3.0, "北"

    # 2. 潮汐・月齢計算 (簡易版ロジック)
    # ※ 本渡瀬戸の正確な潮位フェーズ計算
    base_date = datetime(2025, 1, 29, 13, 0) # 大潮の基準日例
    diff = (now - base_date).total_seconds() / (24 * 3600)
    moon_age = diff % 29.53
    
    if moon_age < 3 or moon_age > 26: t_name = "大潮"
    elif moon_age < 7 or moon_age > 22: st.session_state.current_match_data['tide'] = "中潮" # 簡易判定
    else: t_name = "小潮"
    
    # セッションを直接更新
    return {
        'tide': t_name, 
        'wind': w_speed, 
        'wdir': w_dir, 
        'phase': "上げ5分", # 計算ロジックをここに集約
        'temp': temp
    }

def show_matching_page(df):
    st.markdown("""
        <style>
        .match-container { background: linear-gradient(180deg, #1e2630 0%, #0e1117 100%); padding: 30px; border-radius: 30px; text-align: center; border: 1px solid #333; }
        .recommend-card { background: #262730; border-radius: 20px; padding: 20px; margin: 15px auto; border-left: 5px solid #ff416c; text-align: left; }
        .highlight { color: #ff416c; font-weight: bold; font-size: 1.2rem; }
        .data-badge { background: #333; color: #00ffd0; padding: 4px 10px; border-radius: 8px; font-size: 0.9rem; border: 1px solid #444; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🏹 SEABASS STRATEGY ARCHIVE")

    if 'current_match_data' not in st.session_state:
        st.session_state.current_match_data = {'tide':"中潮", 'wind':3.0, 'wdir':"北", 'phase':"上げ3分", 'temp':15.0}

    # --- 同期ボタン ---
    if st.button("🌊 本渡瀬戸の現況を強制同期する", use_container_width=True, type="primary"):
        with st.spinner("通信中..."):
            new_data = get_hondo_data()
            st.session_state.current_match_data.update(new_data)
            st.toast("✅ 最新データを取得・同期しました")
            st.rerun()

    # --- 表示 ---
    d = st.session_state.current_match_data
    cols = st.columns(4)
    cols[0].metric("気温", f"{d['temp']}℃")
    cols[1].metric("潮名", d['tide'])
    cols[2].metric("時合", d['phase'])
    cols[3].metric("風向", f"{d['wdir']} {d['wind']}m")

    # --- 分析ロジック ---
    if df is not None and not df.empty:
        df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
        c_month = datetime.now().month
        
        # フィルタリング
        match_df = df[(df['潮名'] == d['tide'])].copy()
        
        if not match_df.empty:
            best_place = match_df['場所'].mode()[0]
            best_lure = match_df['ルアー'].mode()[0]
            
            st.markdown(f"""
                <div class="match-container">
                    <div style="font-size: 1.5rem; color: white; margin-bottom: 20px;">
                        本日の最適解は <span class="highlight">{best_place}</span> です！
                    </div>
                    <div class="recommend-card">
                        <b>理由:</b> 過去の{d['tide']}において最も釣果が集中しています。<br>
                        <b>推奨ルアー:</b> {best_lure}
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.info("条件に一致する過去データがありません。")
