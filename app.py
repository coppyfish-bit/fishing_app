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
                return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
        return None
    except:
        return None

# --- 🔮 指定日時の潮位を算出する関数 ---
def calculate_tide_at_time(target_dt, code="HS"):
    # 指定された日時のJSONを読み込む
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/main/data/{target_dt.year}/{code}.json"
    try:
        res = requests.get(url)
        if res.status_code != 200: return None, f"データ召喚失敗({res.status_code})"
        data = res.json()
        
        # 日付マッチング
        t1 = target_dt.strftime("%Y-%m-%d")
        t2 = target_dt.strftime("%Y-%-m-%-d") # 空白・ゼロ埋めなし対策
        day_info = next((i for i in data['data'] if i['date'].strip() in [t1, t2]), None)
        
        if not day_info: return None, f"{t1}のデータが深淵に存在しません"

        # 線形補間
        h = target_dt.hour
        mi = target_dt.minute
        h1_tide = day_info['hourly'][h]
        h2_tide = day_info['hourly'][(h + 1) % 24]
        current_tide = h1_tide + ((h2_tide - h1_tide) * (mi / 60.0))
        
        return {
            "current": current_tide,
            "events": day_info['events'],
            "hourly": day_info['hourly']
        }, None
    except Exception as e:
        return None, str(e)

# --- 📏 潮汐10分割算出 ---
def calculate_tide_phase_10(now_time, events):
    if not events: return "データなし", 0
    sorted_events = sorted(events, key=lambda x: x['time'])
    now_str = now_time.strftime("%H:%M")
    prev_ev, next_ev = None, None
    for i in range(len(sorted_events)):
        if sorted_events[i]['time'] <= now_str: prev_ev = sorted_events[i]
        else:
            next_ev = sorted_events[i]
            break
    if not prev_ev or not next_ev: return "潮止まり", 0
    fmt = "%H:%M"
    t_prev = datetime.strptime(prev_ev['time'], fmt)
    t_next = datetime.strptime(next_ev['time'], fmt)
    t_now = datetime.strptime(now_str, fmt)
    total_min = (t_next - t_prev).total_seconds() / 60
    elapsed_min = (t_now - t_prev).total_seconds() / 60
    phase_num = int((elapsed_min / total_min) * 10)
    label = "📈 上げ" if prev_ev['type'] == 'low' else "📉 下げ"
    return f"{label} {phase_num} 分", phase_num

# --- 🎨 画面構成 ---
st.set_page_config(page_title="デーモン佐藤・深淵の祭壇", layout="centered")
st.markdown("<style>.stApp { background-color: #0e1117; } .tide-card { text-align: center; padding: 25px; background: rgba(0, 212, 255, 0.1); border-radius: 20px; border: 2px solid #00d4ff; margin-bottom: 20px; }</style>", unsafe_allow_html=True)

st.title("📸 写真から海況を復元せよ")
st.write("釣果写真を捧げれば、その瞬間の潮位とフェーズを深淵より呼び戻す。")

uploaded_file = st.file_uploader("写真をアップロード（EXIF付き推奨）", type=["jpg", "jpeg"])

if uploaded_file:
    with st.spinner("刻を遡り中..."):
        photo_dt = get_exif_datetime(uploaded_file)
        
        if photo_dt:
            st.success(f"🎯 撮影日時を検知: {photo_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            result, err = calculate_tide_at_time(photo_dt)
            
            if result:
                phase_text, phase_val = calculate_tide_phase_10(photo_dt, result['events'])
                
                st.markdown(f"""
                    <div class="tide-card">
                        <p style="color: #00d4ff; margin:0;">⌛️ 復元された海況</p>
                        <h1 style="color: #ffffff; font-size: 4rem; margin: 10px 0;">{result['current']:.1f}<span style="font-size: 1.5rem;">cm</span></h1>
                        <h2 style="color: #00ff00; margin:0;">{phase_text}</h2>
                    </div>
                """, unsafe_allow_html=True)
                
                st.image(uploaded_file, caption="解析対象の供物", use_container_width=True)
                st.line_chart(result['hourly'])
            else:
                st.error(f"解析不能: {err}")
        else:
            st.error("🚨 EXIF情報が読み取れん。生の写真を捧げよ。")

st.markdown("---")
st.write("※この機能は過去の潮位JSONデータがGitHubに存在する場合のみ有効だ。")
