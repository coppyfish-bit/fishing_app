import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

# --- 👿 設定（ここを間違えると 404 の呪いにかかる） ---
GITHUB_USER = "coppyfish-bit"
REPO_NAME = "fishing_app"

# --- 🎨 画面構成（メンテナンス・モード） ---
st.set_page_config(page_title="デーモン佐藤・深淵の祭壇", layout="centered")

st.markdown("""
    <style>
    .maint-banner {
        background-color: #800000; color: #ffffff; padding: 15px; 
        text-align: center; border: 4px double #ff0000; border-radius: 10px;
        margin-bottom: 20px;
    }
    .stApp { background-color: #0e1117; }
    </style>
    <div class="maint-banner">
        <h2 style="margin:0;">⚠️ 🚧 SYSTEM UNDER MAINTENANCE 🚧 ⚠️</h2>
        <p style="margin:5px 0 0 0;">現在、デーモン佐藤が JSON データの結合テストを強行中だ。</p>
    </div>
""", unsafe_allow_html=True)

# --- 🔮 データ抽出の魔術（関数） ---
def test_load_json(code="HS"):
    now = datetime.now()
    year = now.year
    # GitHubのRaw URL
    url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/main/data/{year}/{code}.json"
    
    try:
        res = requests.get(url)
        if res.status_code == 200:
            data = res.json()
            # 日付の空白対策（2026- 3- 3 等に対応）
            y, m, d = now.year, now.month, now.day
            t1, t2 = f"{y}-{m:02d}-{d:02d}", f"{y}-{m:>2d}-{d:>2d}"
            
            day_data = next((i for i in data['data'] if i['date'].strip() == t1 or i['date'] == t2), None)
            return day_data, None
        else:
            return None, f"死霊通信失敗 (Status: {res.status_code})"
    except Exception as e:
        return None, str(e)

# --- 👿 テスト実行エリア ---
st.title("🧪 JSON 抽出実験場")

if st.button("🔥 本渡瀬戸のデータを召喚せよ"):
    with st.spinner("深淵の JSON を解析中..."):
        day_info, err = test_load_json("HS")
        
        if day_info:
            st.success("✅ データの抽出に成功したぞ！")
            
            # 1. 毎時潮位の確認
            st.subheader(f"📅 日付: {day_info['date']}")
            st.write("【毎時潮位データ（24時間分）】")
            st.line_chart(day_info['hourly'])
            
            # 2. 満干潮イベントの確認
            st.write("【本日の満干潮】")
            df_ev = pd.DataFrame(day_info['events'])
            st.table(df_ev)
            
        else:
            st.error(f"🚨 召喚失敗: {err}")
            st.info("原因候補：1.リポジトリがPrivateのまま 2.ファイルパスが違う 3.今日の日付がない")
