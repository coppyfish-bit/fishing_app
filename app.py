import streamlit as st
import requests
from datetime import datetime
import pandas as pd

# --- 設定 ---
st.set_page_config(page_title="Tide Debug Center", layout="centered")

st.markdown(f"""
    <h1 style='text-align: center; color: #00ffd0;'>🌊 潮位解析デバッグセンター</h1>
    <p style='text-align: center; color: #888;'>ボタンがないとは言わせぬぞ……！</p>
""", unsafe_allow_html=True)

# 観測所リスト
TIDE_STATIONS = [
    {"name": "苓北", "code": "RH"},
    {"name": "三角", "code": "MS"},
    {"name": "本渡瀬戸", "code": "HS"},
    {"name": "八代", "code": "O5"},
    {"name": "熊本", "code": "KU"},
]

# --- 入力エリア（メイン画面） ---
col1, col2 = st.columns(2)
with col1:
    station_name = st.selectbox("1. 観測所を選べ", [s['name'] for s in TIDE_STATIONS])
with col2:
    target_date = st.date_input("2. 日付を選べ", datetime.now())

# --- 👿 運命のボタン ---
st.write("---")
if st.button("🔥 潮位データを強制取得して解析する", use_container_width=True):
    
    station_code = next(s['code'] for s in TIDE_STATIONS if s['name'] == station_name)
    year = target_date.year
    target_ymd = target_date.strftime('%y%m%d') # YYMMDD形式
    
    url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{year}/{station_code}.txt"
    
    st.info(f"アクセス中: {url}")
    
    try:
        res = requests.get(url, timeout=10)
        
        if res.status_code == 200:
            st.success(f"接続成功！ (Status: {res.status_code})")
            
            lines = res.text.splitlines()
            found = False
            
            for line in lines:
                # 73文字目から6文字が日付(YYMMDD)、その後に観測所コード
                if len(line) >= 80 and line[72:78] == target_ymd:
                    st.warning("🎯 該当日のデータ行を抽出したぞ！")
                    st.code(line)
                    
                    # 毎時潮位を可視化
                    hourly = [int(line[i*3 : (i+1)*3].strip()) for i in range(24)]
                    st.line_chart(pd.DataFrame(hourly, columns=["潮位(cm)"]))
                    
                    found = True
                    break
            
            if not found:
                st.error(f"❌ ファイル内に日付 '{target_ymd}' のデータが見つからん。")
                st.write("ファイルの中身（先頭5行）:")
                st.code("\n".join(lines[:5]))
                
        else:
            st.error(f"❌ ファイルが存在しない。URLが間違っているか、まだ公開されていない。 (Status: {res.status_code})")
            
    except Exception as e:
        st.error(f"💥 通信エラー: {e}")

st.write("---")
st.caption("※ 2026年のデータは気象庁が公開していなければ取得できぬぞ。")
