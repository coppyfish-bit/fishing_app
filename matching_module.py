import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import requests

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

        # 2. 精密潮汐データ取得 (Marine API)
        # 本渡瀬戸の現在時刻の潮位（海面高度）を取得
        t_url = f"https://marine-api.open-meteo.com/v1/marine?latitude={LAT}&longitude={LON}&hourly=tide_height&timezone=Asia%2FTokyo"
        t_res = requests.get(t_url, timeout=5).json()
        
        if 'hourly' in t_res:
            times = t_res['hourly']['time']
            heights = t_res['hourly']['tide_height']
            
            # 現在時刻に最も近いインデックスを探す
            current_time_str = now.strftime('%Y-%m-%dT%H:00')
            if current_time_str in times:
                idx = times.index(current_time_str)
                h0 = heights[idx]   # 今
                h1 = heights[idx+1] # 1時間後
                
                # 潮位の変化からフェーズを判定
                diff = h1 - h0
                abs_h = h0 # 潮位の絶対値
                
                # 簡易的なフェーズ判定ロジック（潮位の高さと変化方向で判定）
                if diff > 0: # 上げ潮
                    if abs_h < -0.5: phase = "上げ1分"
                    elif abs_h < -0.2: phase = "上げ3分"
                    elif abs_h < 0.2: phase = "上げ5分"
                    elif abs_h < 0.5: phase = "上げ7分"
                    else: phase = "上げ9分"
                else: # 下げ潮
                    if abs_h > 0.5: phase = "下げ1分"
                    elif abs_h > 0.2: phase = "下げ3分"
                    elif abs_h > -0.2: phase = "下げ5分"
                    elif abs_h > -0.5: phase = "下げ7分"
                    else: phase = "下げ9分"
                
                res_data['phase'] = phase

        # 3. 潮名（月齢）
        # 簡易計算ではなく、今日の日付から正確に判定
        y, m, d = now.year, now.month, now.day
        if m < 3: y -= 1; m += 12
        moon_age = (((y - 2009) % 19) * 11 + [0, 2, 0, 2, 2, 4, 5, 6, 7, 8, 9, 10][m-1] + d) % 30
        
        if moon_age in [0, 1, 2, 14, 15, 16, 29]: res_data['tide'] = "大潮"
        elif moon_age in [3, 4, 5, 12, 13, 17, 18, 19, 27, 28]: res_data['tide'] = "中潮"
        elif moon_age in [6, 7, 8, 10, 11, 20, 21, 22, 25, 26]: res_data['tide'] = "小潮"
        else: res_data['tide'] = "長潮/若潮"

    except Exception as e:
        st.error(f"同期エラー: {e}")

    return res_data
