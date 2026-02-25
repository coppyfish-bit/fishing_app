import streamlit as st
import pandas as pd
from datetime import datetime
import requests  # これが必要です

def get_hondo_data():
    """本渡瀬戸の正確な気象と潮汐フェーズを取得する"""
    LAT, LON = 32.4333, 130.2167
    now = datetime.now()
    
    res_data = {
        'tide': "中潮", 'wind': 3.0, 'wdir': "北", 
        'phase': "解析中...", 'temp': 15.0
    }

    try:
        # 1. 気象データ取得
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current_weather=true"
        w_res = requests.get(w_url, timeout=5).json()
        if 'current_weather' in w_res:
            res_data['temp'] = w_res['current_weather']['temperature']
            res_data['wind'] = w_res['current_weather']['windspeed']
            dirs = ["北", "北東", "東", "南東", "南", "南西", "西", "北西", "北"]
            res_data['wdir'] = dirs[int((w_res['current_weather']['winddirection'] + 22.5) / 45) % 8]

        # 2. 精密潮汐データ取得
        t_url = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT}&longitude={LON}&hourly=tide_height&timezone=Asia%2FTokyo"
        t_res = requests.get(t_url, timeout=5).json()
        
        if 'hourly' in t_res:
            times = t_res['hourly']['time']
            heights = t_res['hourly']['tide_height']
            current_time_str = now.strftime('%Y-%m-%dT%H:00')
            
            if current_time_str in times:
                idx = times.index(current_time_str)
                h0 = heights[idx]
                h1 = heights[idx+1]
                diff = h1 - h0
                
                # 潮位の変化方向と高さで判定
                if diff > 0:
                    status = "上げ"
                else:
                    status = "下げ"
                
                # 0〜10の間で簡易的にフェーズ化
                phase_num = int(abs(h0) * 5) + 1
                phase_num = min(max(phase_num, 1), 9)
                res_data['phase'] = f"{status}{phase_num}分"

        # 3. 潮名判定
        y, m, d = now.year, now.month, now.day
        moon_age = (((y - 2009) % 19) * 11 + [0, 2, 0, 2, 2, 4, 5, 6, 7, 8, 9, 10][m-1] + d) % 30
        if moon_age in [0, 1, 2, 14, 15, 16, 29]: res_data['tide'] = "大潮"
        elif moon_age in [3, 4, 5, 12, 13, 17, 18, 19, 27, 28]: res_data['tide'] = "中潮"
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

    if 'current_match_data' not in st.session_state:
        st.session_state.current_match_data = {'tide': "中潮", 'wind': 3.0, 'wdir': "北", 'phase': "上げ5分", 'temp': 15.0}

    if st.button("🌊 本渡瀬戸の現況を強制同期する", use_container_width=True, type="primary"):
        with st.spinner("最新データを取得中..."):
            new_data = get_hondo_data()
            st.session_state.current_match_data = new_data
            st.rerun()

    d = st.session_state.current_match_data
    cols = st.columns(4)
    cols[0].metric("気温", f"{d.get('temp', '--')}℃")
    cols[1].metric("潮名", d.get('tide', '--'))
    cols[2].metric("時合", d.get('phase', '--'))
    cols[3].metric("風向", f"{d.get('wdir', '--')} {d.get('wind', '--')}m")

    if df is not None and not df.empty:
        df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
        c_month = datetime.now().month
        
        # 潮名と季節でフィルタ
        match_df = df[df['潮名'] == d.get('tide')].copy()
        
        if not match_df.empty:
            best_place = match_df['場所'].mode()[0] if '場所' in match_df.columns else "不明"
            best_lure = match_df['ルアー'].mode()[0] if 'ルアー' in match_df.columns else "不明"
            
            st.markdown(f"""
                <div class="match-container">
                    <div style="font-size: 1.5rem; color: white; margin-bottom: 20px;">
                        本日の最適解は <span class="highlight">{best_place}</span> です！
                    </div>
                    <div class="recommend-card">
                        <b>戦略の根拠:</b> 過去の{d.get('tide')}においてヒットが集中しています。<br>
                        <b>推奨ルアー:</b> {best_lure}
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.info("この条件に一致する過去データがありません。")
