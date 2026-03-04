import streamlit as st
import pandas as pd
import requests
import traceback
from streamlit_gsheets import GSheetsConnection

# AIとの会話は学習に使用したり外部に漏れたりしません。釣果情報も共有しません。

st.set_page_config(page_title="潮汐デバッグモード", layout="wide")
st.title("🔎 潮位取得プロセス・完全検証")

# --- 1. スプレッドシート設定（ご自身のURLに差し替えてください） ---
# ここにスプレッドシートのURLを貼り付けてください
GS_URL = "https://docs.google.com/spreadsheets/d/1X..." 

# --- 2. 潮位解析関数 (ガード付き) ---
def get_tide_details(res, dt):
    try:
        if isinstance(res, str):
            res = requests.get(res)
        data = res.json()
        
        # 2026- 3- 4 対策の検索キー作成
        target_date_clean = dt.strftime("%Y-%m-%d").replace("-0", "-").replace("-", "").replace(" ", "")
        
        day_info = None
        for item in data.get('data', []):
            json_date_clean = str(item.get('date', '')).replace("-", "").replace(" ", "")
            if json_date_clean == target_date_clean:
                day_info = item
                break
        
        if not day_info:
            return {"cm": 0, "phase": f"日付不一致({target_date_clean})"}

        hourly = [int(v) for v in day_info.get('hourly', [])]
        h, mi = dt.hour, dt.minute
        t1, t2 = hourly[h], hourly[(h+1)%24]
        current_cm = int(round(t1 + (t2 - t1) * (mi / 60.0)))

        return {"cm": current_cm, "phase": "取得成功", "day_info": day_info}
    except Exception as e:
        return {"cm": 0, "phase": f"解析失敗: {e}"}

# --- 3. メイン実行部 ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(spreadsheet=GS_URL, ttl="0s")
    
    if not df.empty:
        # 最新の1件を取得
        row = df.iloc[-1]
        st.write("### 🗂️ 検証するスプレッドシートの行")
        st.table(pd.DataFrame(row).T)

        if st.button("🚀 潮位データを取得してみる"):
            # A. 日時変換
            dt = pd.to_datetime(str(row['datetime']).strip())
            st.write(f"1. 解析した日時: `{dt}`")

            # B. URL生成 (本渡瀬戸 HS でテスト)
            user = "coppyfish-bit"
            repo = "fishing_app"
            url = f"https://raw.githubusercontent.com/{user}/{repo}/main/data/{dt.year}/HS.json"
            st.write(f"2. 生成したURL: `{url}`")

            # C. 通信と解析
            res = requests.get(url)
            st.write(f"3. HTTPステータス: `{res.status_code}`")
            
            if res.status_code == 200:
                result = get_tide_details(res, dt)
                st.write(f"4. 解析結果: `{result['phase']}`")
                
                if "取得成功" in result['phase']:
                    st.metric("算出された潮位", f"{result['cm']} cm")
                    with st.expander("JSONの該当日の生データ"):
                        st.json(result['day_info'])
                else:
                    st.error(result['phase'])
            else:
                st.error("GitHubからファイルを読み込めませんでした。URLが正しいかブラウザで確認してください。")
    else:
        st.warning("スプレッドシートにデータが見つかりません。")

except Exception as e:
    st.error(f"システムエラー: {e}")
    st.code(traceback.format_exc())
