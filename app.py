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

# --- 📏 潮汐10分割算出（時間形式エラー対策版） ---
def calculate_tide_phase_10(now_time, events):
    if not events: return "データなし", 0
    
    # 1. 時間の空白を削除してソート
    for ev in events:
        ev['time'] = ev['time'].strip()
        
    sorted_events = sorted(events, key=lambda x: x['time'])
    now_str = now_time.strftime("%H:%M")
    
    prev_ev, next_ev = None, None
    for i in range(len(sorted_events)):
        # 0埋めなしの比較にも対応させるため、一度数値や正規化された形式で比較するのが安全だが、
        # ここでは文字列表現を整えて比較する
        current_ev_time = sorted_events[i]['time'].zfill(5) # "3:59" -> "03:59"
        if current_ev_time <= now_str:
            prev_ev = sorted_events[i]
        else:
            next_ev = sorted_events[i]
            break
            
    if not prev_ev or not next_ev: return "潮止まり", 0

    # 2. 👿 フォーマット不一致を破壊する解析ロジック
    def parse_time_flexibly(time_str):
        # " 3:59" や "3:59" を "03:59" として解釈する
        time_str = time_str.strip()
        try:
            return datetime.strptime(time_str, "%H:%M")
        except ValueError:
            # 0埋めされていない形式（例: "3:59"）にも対応
            return datetime.strptime(time_str, "%H:%M" if ":" in time_str else "%H")

    t_prev = parse_time_flexibly(prev_ev['time'])
    t_next = parse_time_flexibly(next_ev['time'])
    t_now = datetime.strptime(now_str, "%H:%M")
    
    total_min = (t_next - t_prev).total_seconds() / 60
    # もし日付を跨ぐ場合（23時から01時など）の計算補正
    if total_min < 0: total_min += 1440 
    
    elapsed_min = (t_now - t_prev).total_seconds() / 60
    if elapsed_min < 0: elapsed_min += 1440

    phase_num = int((elapsed_min / total_min) * 10)
    phase_num = min(max(phase_num, 0), 10)
    
    label = "📈 上げ" if prev_ev['type'] == 'low' else "📉 下げ"
    return f"{label} {phase_num} 分", phase_num
