import streamlit as st
import requests
import re
from datetime import datetime
import pandas as pd

# --- 設定 ---
st.set_page_config(page_title="Tide Ultimate Debugger", layout="wide")

st.markdown("<h1 style='color: #00ffd0;'>🌊 潮位解析・最終デバッグ装置</h1>", unsafe_allow_html=True)

# 観測所リスト（地点コードを正確に！）
TIDE_STATIONS = [
    {"name": "本渡瀬戸", "code": "HS"},
    {"name": "三角", "code": "MS"},
    {"name": "苓北", "code": "RH"},
    {"name": "八代", "code": "O5"},
    {"name": "熊本", "code": "KU"},
]

# --- UI部 ---
with st.sidebar:
    st.header("🔍 解析パラメータ")
    station = st.selectbox("観測所を選択", TIDE_STATIONS, format_func=lambda x: f"{x['name']} ({x['code']})")
    target_date = st.date_input("解析日", datetime.now())
    target_time = st.time_input("解析時刻", datetime.now().time())
    
    execute = st.button("🔥 データを強制解析する", use_container_width=True)

if execute:
    dt = datetime.combine(target_date, target_time)
    code = station['code']
    url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{dt.year}/{code}.txt"
    
    st.info(f"🌐 接続先: {url}")
    
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            st.error(f"❌ データ取得失敗 (HTTP {res.status_code})")
        else:
            st.success("✅ ファイル取得成功。解析を開始する。")
            lines = res.text.splitlines()
            
            # 日付パターン検索 (YY MM DD CODE)
            # スペースが1つ以上あることを想定
            yy = dt.strftime('%y')
            mm = str(dt.month)
            dd = str(dt.day)
            pattern = rf"{yy}\s+{mm}\s+{dd}\s*{code}"
            
            target_line = None
            for line in lines:
                if re.search(pattern, line):
                    target_line = line
                    break
            
            if not target_line:
                st.warning(f"⚠️ パターン '{yy} {mm} {dd}{code}' が見つかりません。")
                st.write("ファイル先頭5行の内容:")
                st.code("\n".join(lines[:5]))
            else:
                st.markdown("### 🎯 抽出された生データ行")
                st.code(target_line)
                
                # 数値の全抽出
                nums = re.findall(r'-?\d+', target_line)
                st.write(f"検出された数値の数: {len(nums)}")
                
                if len(nums) >= 24:
                    # 1. 毎時潮位
                    hourly = [int(n) for n in nums[:24]]
                    
                    # 2. 現在の潮位計算
                    h, m = dt.hour, dt.minute
                    t1, t2 = hourly[h], (hourly[h+1] if h < 23 else hourly[h])
                    current_cm = int(round(t1 + (t2 - t1) * (m / 60.0)))
                    
                    # 3. グラフ表示
                    st.markdown(f"#### 📊 潮位推移 ({dt.strftime('%Y/%m/%d')})")
                    df = pd.DataFrame({"潮位(cm)": hourly})
                    st.line_chart(df)
                    st.metric(label=f"{dt.strftime('%H:%M')} の推定潮位", value=f"{current_cm} cm")
                    
                    # 4. 満干潮イベント (27番目以降)
                    event_data = nums[27:]
                    st.markdown("#### ⏱️ 満干潮イベント解析")
                    events = []
                    # 満潮(4ペア)
                    for i in range(0, 8, 2):
                        if i+1 < len(event_data) and event_data[i] != "9999":
                            events.append({"時刻": event_data[i].zfill(4), "潮位": event_data[i+1], "種別": "満潮"})
                    # 干潮(4ペア)
                    for i in range(8, 16, 2):
                        if i+1 < len(event_data) and event_data[i] != "9999":
                            events.append({"時刻": event_data[i].zfill(4), "潮位": event_data[i+1], "種別": "干潮"})
                    
                    if events:
                        st.table(pd.DataFrame(events))
                    else:
                        st.info("満干潮データが 9999 (未定義) です。")

    except Exception as e:
        st.error(f"💥 致命的エラー: {e}")

st.write("---")
st.caption("※ 修正した正規表現により、本渡瀬戸(HS)特有のスペース区切りも解析可能だ。")
