import streamlit as st
import pandas as pd
import requests
import google.generativeai as genai
import os
import base64
from datetime import datetime

# --- 👿 設定：ここを自分の情報に書き換えろ ---
GITHUB_USER = "coppyfish-bit"
REPO_NAME = "fishing_app"

# --- 🖼️ 画像をBase64に変換（アイコン・ヘッダー用） ---
def get_image_as_base64(file_path):
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        absolute_path = os.path.join(current_dir, file_path)
        with open(absolute_path, "rb") as f:
            data = f.read()
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    except:
        return "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"

# --- 🔮 JSONデータをGitHubから召喚する関数 ---
def load_tide_json(code="HS"):
    now = datetime.now()
    year = now.year
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/main/data/{year}/{code}.json"
    
    try:
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            # 日付の空白対策（"2026- 3- 3" 等に対応）
            y, m, d = now.year, now.month, now.day
            t1, t2 = f"{y}-{m:02d}-{d:02d}", f"{y}-{m:>2d}-{d:>2d}"
            day_data = next((i for i in data['data'] if i['date'].strip() == t1 or i['date'] == t2), None)
            return day_data, None
        return None, f"死霊通信失敗 (Status: {res.status_code})"
    except Exception as e:
        return None, str(e)

# --- 📏 潮汐10分割（上げ/下げ○分）を算出する関数 ---
def calculate_tide_phase_10(now_time, events):
    if not events: return "データなし", 0
    sorted_events = sorted(events, key=lambda x: x['time'])
    now_str = now_time.strftime("%H:%M")
    
    prev_ev, next_ev = None, None
    for i in range(len(sorted_events)):
        if sorted_events[i]['time'] <= now_str:
            prev_ev = sorted_events[i]
        else:
            next_ev = sorted_events[i]
            break
            
    if not prev_ev or not next_ev: return "潮止まり（端境期）", 0

    fmt = "%H:%M"
    t_prev = datetime.strptime(prev_ev['time'], fmt)
    t_next = datetime.strptime(next_ev['time'], fmt)
    t_now = datetime.strptime(now_str, fmt)
    
    total_min = (t_next - t_prev).total_seconds() / 60
    elapsed_min = (t_now - t_prev).total_seconds() / 60
    phase_num = int((elapsed_min / total_min) * 10)
    phase_num = min(max(phase_num, 0), 10)
    
    label = "📈 上げ" if prev_ev['type'] == 'low' else "📉 下げ"
    return f"{label} {phase_num} 分", phase_num

# --- 🎨 画面基本設定 ---
st.set_page_config(page_title="デーモン佐藤・深淵の祭壇", layout="centered")

# --- 🚧 巨大メンテナンス・バナー ---
st.markdown("""
    <style>
    .maint-banner {
        background-color: #800000; color: #ffffff; padding: 15px; 
        text-align: center; border: 4px double #ff0000; border-radius: 10px;
        margin-bottom: 20px; animation: blink 2s infinite;
    }
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.7; } 100% { opacity: 1; } }
    .stApp { background-color: #0e1117; }
    .user-bubble { align-self: flex-end; background-color: #0084ff; color: white; padding: 10px 15px; border-radius: 18px 18px 2px 18px; max-width:
    
