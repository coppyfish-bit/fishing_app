import streamlit as st
import pandas as pd
import requests
import google.generativeai as genai
import os
import base64
from datetime import datetime, timedelta, timezone
from PIL import Image
from PIL.ExifTags import TAGS

# --- 👿 設定：リポジトリ情報 ---
GITHUB_USER = "coppyfish-bit"
REPO_NAME = "fishing_app"

# --- 📸 EXIFから撮影日時を抜き出す関数 ---
def get_exif_datetime(uploaded_file):
    try:
        img = Image.open(uploaded_file)
        exif_data = img._getexif()
        if not exif_data: return None
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "DateTimeOriginal":
                # EXIF形式 "YYYY:MM:DD HH:MM:SS" をパース
                return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
        return None
    except:
        return None

# --- 🔮 指定日時の潮位を算出する関数（JST/空白対策済） ---
def calculate_tide_at_time(target_dt, code="HS"):
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/main/data/{target_dt.year}/{code}.json"
    try:
        res = requests.get(url)
        if res.status_code != 200: return None, f"データ召喚失敗({res.status_code})"
        data = res.json()
        
        # 日付マッチング（空白やゼロ埋めの有無を無視して比較）
        t1 = target_dt.strftime("%Y-%m-%d")
        day_info = next((i for i in data['data'] if i['date'].replace(" ", "") == t1 or i['date'].strip() == t1), None)
        
        if not day_info: return None, f"{t1}のデータが深淵に存在しません"

        # 線形補間
        h = target_dt.hour
        mi = target_dt.minute
        h1_tide = day_info['hourly'][h]
        h2_tide = day_info['hourly'][(h + 1) % 24]
        current_tide = h1_tide + ((h2_tide - h1_tide) * (mi / 60.0))
        
        return {
            "current": current_tide,
            "h1": h1_tide,
            "h2": h2_tide,
            "events": day_info['events'],
            "hourly": day_info['hourly']
        }, None
    except Exception as e:
        return None, str(e)

# --- 📏 潮汐10分割算出（時間形式エラー鉄壁ガード版） ---
def calculate_tide_phase_10(now_time, events):
    if not events: return "データなし", 0
    
    # データの正規化
    norm_events = []
    for ev in events:
        clean_time = ev['time'].strip().zfill(5) # " 3:59" -> "03:59"
        norm_events.append({"time": clean_time, "type": ev['type']})
        
    sorted_events = sorted(norm_events, key=lambda x: x['time'])
    now_str = now_time.strftime("%H:%M")
    
    prev_ev, next_ev = None, None
    for i in range(len(sorted_events)):
        if sorted_events[i]['time'] <= now_str:
            prev_ev = sorted_events[i]
        else:
            next_ev = sorted_events[i]
            break
            
    if not prev_ev or not next_ev: return "潮止まり", 0

    fmt = "%H:%M"
    t_prev = datetime.strptime(prev_ev['time'], fmt)
    t_next = datetime.strptime(next_ev['time'], fmt)
    t_now = datetime.strptime(now_str, fmt)
    
    total_min = (t_next - t_prev).total_seconds() / 60
    if total_min < 0: total_min += 1440 # 日またぎ補正
    
    elapsed_min = (t_now - t_prev).total_seconds() / 60
    if elapsed_min < 0: elapsed_min += 1440

    phase_num = int((elapsed_min / total_min) * 10)
    phase_num = min(max(phase_num, 0), 10)
    
    label = "📈 上げ" if prev_ev['type'] == 'low' else "📉 下げ"
    return f"{label} {phase_num} 分", phase_num

# --- 🎨 画面構成 ---
st.set_page_config(page_title="デーモン佐藤・深淵の祭壇", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    .tide-card { text-align: center; padding: 25px; background: rgba(0, 255, 0, 0.05); border-radius: 20px; border: 2px dashed #00ff00; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

st.title("📸 釣果写真・海況復元プロトコル")
st.write("写真を捧げよ。EXIFから刻を遡り、その瞬間の天草の海を再現する。")

uploaded_file = st.file_uploader("写真をアップロード (JPEGのみ)", type=["jpg", "jpeg"])

if uploaded_file:
    with st.spinner("EXIF解析中..."):
        photo_dt = get_exif_datetime(uploaded_file)
        
        if photo_dt:
            st.success(f"🎯 撮影日時を検知: {photo_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 指定日時のデータで計算
            result, err = calculate_tide_at_time(photo_dt)
            
            if result:
                phase_text, _ = calculate_tide_phase_10(photo_dt, result['events'])
                
                st.markdown(f"""
                    <div class="tide-card">
                        <p style="color: #00ff00; margin:0;">⌛️ 復元された潮位</p>
                        <h1 style="color: #ffffff; font-size: 4rem; margin: 10px 0;">{result['current']:.1f}<span style="font-size: 1.5rem;">cm</span></h1>
                        <h2 style="color: #00ff00; margin:0;">{phase_text}</h2>
                    </div>
                """, unsafe_allow_html=True)
                
                st.image(uploaded_file, caption=f"撮影時: {photo_dt.strftime('%H:%M')}", use_container_width=True)
                
                # 撮影日の潮汐グラフ
                st.markdown(f"### 📅 {photo_dt.strftime('%Y-%m-%d')} の潮汐グラフ")
                st.line_chart(result['hourly'])
            else:
                st.error(f"解析失敗: {err}")
        else:
            st.error("🚨 EXIFが見つからん。SNS等で加工されていない、カメラの生データを捧げよ。")

# 😈 デーモン佐藤への相談
st.markdown("---")
st.write("この潮回りでなぜ釣れたのか、デーモン佐藤に分析させるか？")
if st.button("😈 デーモン分析を開始する"):
    st.info("ここに分析結果を表示するロジックを組むことも可能だ。")
