import streamlit as st
import pandas as pd
import requests
import traceback
from streamlit_gsheets import GSheetsConnection

# AIとの会話は学習に使用したり外部に漏れたりしません。釣果情報も共有しません。

st.set_page_config(page_title="潮汐デバッグモード", layout="wide")
st.title("🔎 潮位取得プロセス・完全検証")

# --- 1. スプレッドシート設定（ご提示いただいたURL） ---
GS_URL = "https://docs.google.com/spreadsheets/d/12hcg7hagi0oLq3nS-K27OqIjBYmzMYXh_FcoS8gFFyE/edit?gid=0#gid=0"

# --- 2. 潮位解析関数 (ガード・空白補正付き) ---
def get_tide_details(res, dt):
    try:
        if isinstance(res, str):
            res = requests.get(res)
        data = res.json()
        
        # 2026- 3- 4 のような「空白あり」と「ゼロ埋めなし」に対応する検索キー
        # 例: 2026-03-04 -> 202634 / 2026- 3- 4 -> 202634
        target_date_clean = dt.strftime("%Y-%m-%d").replace("-0", "-").replace("-", "").replace(" ", "")
        
        day_info = None
        for item in data.get('data', []):
            json_date_clean = str(item.get('date', '')).replace("-", "").replace(" ", "")
            if json_date_clean == target_date_clean:
                day_info = item
                break
        
        if not day_info:
            return {"cm": 0, "phase": f"日付不一致(キー:{target_date_clean})"}

        # 潮位データの数値化
        hourly = [int(v) for v in day_info.get('hourly', [])]
        h, mi = dt.hour, dt.minute
        t1, t2 = hourly[h], hourly[(h+1)%24]
        current_cm = int(round(t1 + (t2 - t1) * (mi / 60.0)))

        return {"cm": current_cm, "phase": "取得成功", "day_info": day_info}
    except Exception as e:
        return {"cm": 0, "phase": f"解析失敗: {e}"}

# --- 3. メイン実行部 ---
try:
    # 接続テスト
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=GS_URL, ttl="0s")
    
    if not df.empty:
        # 最新の1件を表示
        row = df.iloc[-1]
        st.write("### 🗂️ スプレッドシートから読み込んだ最新データ")
        st.table(pd.DataFrame(row).T)

        st.divider()
        
        # ボタンを押して検証開始
        if st.button("🚀 このデータで潮位計算をテストする", use_container_width=True):
            with st.status("デバッグ実行中...", expanded=True):
                # A. 日時変換
                dt = pd.to_datetime(str(row['datetime']).strip())
                st.write(f"1️⃣ 解析日時: `{dt}`")

                # B. URL生成 (とりあえず本渡瀬戸 HS で検証)
                user = "coppyfish-bit"
                repo = "fishing_app"
                url = f"https://raw.githubusercontent.com/{user}/{repo}/main/data/{dt.year}/HS.json"
                st.write(f"2️⃣ 生成URL: `{url}`")

                # C. GitHub通信
                res = requests.get(url)
                st.write(f"3️⃣ HTTPステータス: `{res.status_code}`")
                
                if res.status_code == 200:
                    # D. 解析実行
                    result = get_tide_details(res, dt)
                    st.write(f"4️⃣ 解析状況: `{result['phase']}`")
                    
                    if "取得成功" in result['phase']:
                        st.balloons()
                        st.success(f"🎉 潮位の取得に成功しました！")
                        st.metric("算出された潮位", f"{result['cm']} cm")
                        with st.expander("JSONの生データを確認"):
                            st.json(result['day_info'])
                    else:
                        st.error(f"❌ 解析エラー: {result['phase']}")
                else:
                    st.error(f"❌ GitHubからデータを取得できませんでした (404)。URLが正しいかブラウザで確認してください。")
    else:
        st.warning("スプレッドシートが空です。")

except Exception as e:
    st.error(f"⚠️ 接続エラー: {e}")
    st.info("スプレッドシートの共有設定が『リンクを知っている全員』になっているか確認してください。")
    st.code(traceback.format_exc())
