import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import requests

def get_realtime_weather():
    """本渡瀬戸の現況を同期（48h降水量・8方位風向込）"""
    LAT, LON = 32.4333, 130.2167
    now = datetime.now()
    # 鉄壁の初期値
    data = {
        'tide': "中潮", 'temp': 15.0, 'wind': 3.0, 'wdir': "北",
        'tide_level': 100, 'phase': "上げ5分", 'precip_48h': 0.0
    }
    
    try:
        # 1. 気象予報API
        w_url = f"https://api.open-meteo.com/v1/forecast?latitude={LAT}&longitude={LON}&current_weather=true&hourly=precipitation&past_days=2&timezone=Asia%2FTokyo"
        w_res = requests.get(w_url, timeout=5).json()
        
        if 'current_weather' in w_res:
            cw = w_res['current_weather']
            data['temp'] = float(cw.get('temperature', 15.0))
            data['wind'] = float(cw.get('windspeed', 3.0))
            
            # 風向を8方位へ即時変換
            deg = cw.get('winddirection', 0)
            directions = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
            data['wdir'] = directions[int((deg + 22.5) / 45) % 8]
            
            if 'hourly' in w_res:
                current_idx = 48 + now.hour
                p_list = w_res['hourly'].get('precipitation', [0.0]*72)
                # 48時間分を安全に合計
                data['precip_48h'] = round(sum(p_list[max(0, current_idx-48):current_idx+1]), 1)

        # 2. 海洋予報API
        t_url = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT}&longitude={LON}&hourly=tide_height&timezone=Asia%2FTokyo"
        t_res = requests.get(t_url, timeout=5).json()
        if 'hourly' in t_res:
            h_list = t_res['hourly'].get('tide_height', [0.0]*24)
            h0, h1 = h_list[now.hour], h_list[(now.hour+1)%24]
            data['tide_level'] = int(h0 * 100)
            status = "上げ" if h1 - h0 > 0 else "下げ"
            p_val = min(max(int(abs(h0) * 5) + 1, 1), 9)
            data['phase'] = f"{status}{p_val}分"
            
    except:
        pass # 失敗しても初期値（data）が維持される
    return data

def simplify_direction(wdir):
    """過去データの16方位を8方位に丸める補助関数"""
    wdir = str(wdir)
    mapping = {
        '北北東': '北東', '東北東': '北東',
        '東南東': '南東', '南南東': '南東',
        '南南西': '南西', '西南西': '南西', '珠南西': '南西', 
        '西北西': '北西', '北北西': '北西'
    }
    return mapping.get(wdir, wdir)

def show_matching_page(df):
    st.markdown("""
        <style>
        .stButton>button { background-color: #ff4b6c; color: white; border-radius: 25px; border: none; padding: 12px; font-weight: bold; width: 100%; }
        .input-card { background-color: #1e1e1e; padding: 20px; border-radius: 15px; border: 1px solid #333; margin-bottom: 20px; }
        .recommend-card { background: linear-gradient(135deg, #2c3e50 0%, #000000 100%); padding: 20px; border-radius: 15px; border-left: 5px solid #ff4b6c; margin-bottom: 15px; color: white; position: relative; }
        .score-badge { position: absolute; top: 20px; right: 20px; font-size: 1.8rem; font-weight: bold; color: #ff4b6c; }
        </style>
    """, unsafe_allow_html=True)

    st.title("🏹 SeaBass Match AI v2.8")

    # セッション状態の初期化
    if 'm_data' not in st.session_state:
        st.session_state.m_data = get_realtime_weather()

    # --- 入力セクション ---
    st.markdown("<div class='input-card'>", unsafe_allow_html=True)
    if st.button("🔄 本渡瀬戸の全データを同期"):
        st.session_state.m_data = get_realtime_weather()
        st.rerun()

    # .get() を使ってKeyErrorを絶対に回避
    md = st.session_state.m_data
    col1, col2 = st.columns(2)
    with col1:
        tide_in = st.selectbox("潮名", ["大潮", "中潮", "小潮", "長潮", "若潮"], 
                                 index=["大潮", "中潮", "小潮", "長潮", "若潮"].index(md.get('tide', '中潮')))
        temp_in = st.number_input("気温 (℃)", value=float(md.get('temp', 15.0)))
        precip_in = st.number_input("48h降水量 (mm)", value=float(md.get('precip_48h', 0.0)))
    with col2:
        phase_list = ["上げ1分","上げ3分","上げ5分","上げ7分","上げ9分","満潮","下げ1分","下げ3分","下げ5分","下げ7分","下げ9分","干潮"]
        current_phase = md.get('phase', '上げ5分')
        phase_in = st.selectbox("時合", phase_list, index=phase_list.index(current_phase) if current_phase in phase_list else 2)
        
        wdir_list = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
        current_wdir = md.get('wdir', '北')
        wdir_in = st.selectbox("風向 (8方位)", wdir_list, index=wdir_list.index(current_wdir) if current_wdir in wdir_list else 0)
        
        wind_in = st.number_input("風速 (m/s)", value=float(md.get('wind', 3.0)))
    st.markdown("</div>", unsafe_allow_html=True)

    # --- ランキング診断 ---
    if st.button("💘 ランキングを診断する"):
        if df is not None and not df.empty:
            # 内部データのクリーニング
            df['is_bouzu'] = df['魚種'].astype(str).str.contains('ボウズ', na=False)
            df['風向_8'] = df['風向'].apply(simplify_direction)
            
            match_df = df[df['潮名'] == tide_in].copy()
            
            if not match_df.empty:
                results = []
                for place in match_df['場所'].unique():
                    p_df = match_df[match_df['場所'] == place]
                    success_df = p_df[~p_df['is_bouzu']]
                    
                    if not success_df.empty:
                        # 成功率(30) + 風向一致(20) + 時合一致(20) + 気象類似(30)
                        base_score = (len(success_df) / len(p_df)) * 30
                        wdir_bonus = 20 if not success_df[success_df['風向_8'] == wdir_in].empty else 0
                        phase_bonus = 20 if not success_df[success_df['潮位フェーズ'] == phase_in].empty else 0
                        
                        avg_p48 = success_df['48時間降水量'].mean() if '48時間降水量' in success_df.columns else 0.0
                        w_diff = abs(success_df['気温'].mean() - temp_in) * 2 + abs(avg_p48 - precip_in) * 0.5
                        weather_score = max(0, 30 - w_diff)
                        
                        total_score = min(int(base_score + wdir_bonus + phase_bonus + weather_score), 99)
                        
                        lure_mode = success_df['ルアー'].dropna().mode()
                        results.append({
                            'place': place, 'score': total_score, 'hits': len(success_df), 
                            'lure': lure_mode[0] if not lure_mode.empty else "未登録"
                        })
                
                results = sorted(results, key=lambda x: x['score'], reverse=True)
                for i, res in enumerate(results):
                    st.markdown(f"""
                        <div class='recommend-card'>
                            <div class='score-badge'>{res['score']}%</div>
                            <div style='font-size:1.2rem; font-weight:bold;'>{i+1}位: {res['place']}</div>
                            <div>実績: {res['hits']}件 / 推奨: <span style='color:#00ffd0;'>{res['lure']}</span></div>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info(f"{tide_in}での過去データが見つかりません。")
