import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import re
from datetime import datetime

# --- 設定 ---
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1x7pDDkRpf4EO2x-T-T68vqoVc3i0WUXz07kG0sW3G6k/edit"

def main():
    st.set_page_config(page_title="Tide Parser Pro", layout="centered")
    st.title("🌊 潮汐データ解析 (A列全探索版)")

    conn = st.connection("gsheets", type=GSheetsConnection)

    # 地点と日時の選択
    target_point = st.selectbox("地点コード", ["HS", "KUMAMOTO"])
    target_dt = st.datetime_input("釣行日時", datetime.now())

    if st.button("📡 解析を実行"):
        try:
            # 1. スプレッドシート読み込み
            # header=Noneを使い、全ての行をフラットに読み込みます
            df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=target_point, ttl=0, header=None)
            
            # 2. 検索する日付
            date_str = target_dt.strftime('%Y-%m-%d')
            
            # 3. A列(0番目)を1行ずつループして、日付とJSONの両方を含む行を探す
            found_data = None
            for index, row in df.iterrows():
                cell_value = str(row[0])
                # 日付が含まれているかチェック
                if date_str in cell_value:
                    # 波括弧が含まれているかチェック
                    if '{' in cell_value:
                        found_data = cell_value
                        break
            
            if not found_data:
                st.warning(f"シート '{target_point}' 内に {date_str} と JSON を含む行が見つかりませんでした。")
                st.info("シートの先頭数行の生データ:")
                st.write(df.head(5))
                return

            # 4. JSON部分の切り出し
            json_start_idx = found_data.find('{')
            json_str_raw = found_data[json_start_idx:]
            
            # 5. 特殊なJSON形式の補正
            # キーをダブルクォートで囲み、シングルクォートを置換
            # 提示された形式に合わせて re.sub を調整
            formatted_json = json_str_raw.replace("'", '"')
            # キー名（英字:）を "キー名": に変換
            formatted_json = re.sub(r'(\s*)(\w+):', r'\1"\2":', formatted_json)
            
            # 最後のカンマなど、JSONとして不正な文字があれば削るための処理
            formatted_json = formatted_json.strip()
            if formatted_json.endswith('}'): # 念のため
                pass 

            day_data = json.loads(formatted_json)
            
            # トップレベルの構造が {data: [...]} かチェック
            if "data" in day_data and isinstance(day_data["data"], list):
                day_data = day_data["data"][0]

            # --- 6. 潮汐計算 ---
            target_hour = target_dt.hour
            tide_cm = day_data['hourly'][target_hour]

            # フェーズ判定
            events = day_data['events']
            current_time_val = target_hour + (target_dt.minute / 60.0)
            
            parsed_events = []
            for ev in events:
                time_part = ev['time'].replace(' ', '')
                h, m = map(int, time_part.split(':'))
                parsed_events.append({"time": h + (m/60.0), "type": ev['type']})
            
            past = [e for e in parsed_events if e['time'] <= current_time_val]
            future = [e for e in parsed_events if e['time'] > current_time_val]
            
            phase = "判定中"
            if past and future:
                if past[-1]['type'] == 'low': phase = "上げ潮"
                else: phase = "下げ潮"

            # --- 7. 結果表示 ---
            st.success(f"✅ {date_str} のデータを解析しました")
            c1, c2 = st.columns(2)
            c1.metric("推定潮位", f"{tide_cm} cm")
            c2.metric("潮汐状態", phase)

        except json.JSONDecodeError as e:
            st.error(f"JSON形式が正しくありません: {e}")
            st.text("整形後のデータ:")
            st.code(formatted_json)
        except Exception as e:
            st.error(f"エラー: {e}")

if __name__ == "__main__":
    main()
