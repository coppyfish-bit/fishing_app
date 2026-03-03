import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- 👿 ここを自分の GitHub 情報に変えろ！ ---
GITHUB_USER = "coppyfish-bit"  # 貴様のユーザー名
REPO_NAME = "fishing_app"      # リポジトリ名（例: my-tide-data）

TIDE_STATIONS = [
    {"name": "苓北", "code": "RH"},
    {"name": "三角", "code": "MS"},
    {"name": "本渡瀬戸", "code": "HS"},
    {"name": "八代", "code": "O5"},
    {"name": "水俣", "code": "O7"},
    {"name": "熊本", "code": "KU"},
    {"name": "大牟田", "code": "O6"},
    {"name": "大浦", "code": "OU"},
    {"name": "口之津", "code": "KT"},
]

def get_tide_data(year, code):
    # GitHubの Raw URL（生データ用URL）を構築
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/main/data/{year}/{code}.json"
    try:
        res = requests.get(url)
        if res.status_code == 200:
            return res.json()
        return None
    except:
        return None

# --- UI 表示部 ---
st.title("🌊 熊本・有明海 爆速潮汐システム")

selected_st = st.selectbox("地点を選択", TIDE_STATIONS, format_func=lambda x: x['name'])
now = datetime.now()

if st.button("🔥 潮位を召喚する"):
    # GitHubからJSONをロード
    json_data = get_tide_data(now.year, selected_st['code'])
    
    if json_data:
        # 今日の日付のデータをリストから探す
        today_str = now.strftime('%Y-%m-%d')
        day_info = next((d for d in json_data['data'] if d['date'] == today_str), None)
        
        if day_info:
            # 1. 現在潮位 (30分単位で最も近い時間を抽出)
            nearest_hour = now.hour if now.minute < 30 else (now.hour + 1) % 24
            current_cm = day_info['hourly'][nearest_hour]
            
            st.markdown(f"### 🎯 現在の判定時刻: {now.strftime('%H:%M')}")
            st.metric(label=f"【{nearest_hour}:00】の観測潮位", value=f"{current_cm} cm")
            
            # 2. 満干潮イベント表
            st.markdown("### 📋 本日の満干潮")
            df_ev = pd.DataFrame(day_info['events'])
            df_ev.columns = ['時刻', '種別', '潮位(cm)']
            st.table(df_ev)
            
            # 3. 毎時潮位グラフ（おまけだ！）
            st.markdown("### 📈 24時間の潮位推移")
            st.line_chart(day_info['hourly'])
            
        else:
            st.error(f"本日（{today_str}）のデータが JSON 内に見当たりません。")
    else:
        st.error("GitHub からデータを取得できません。URL またはファイル名を確認せよ。")

