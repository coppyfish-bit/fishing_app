import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import re
from datetime import datetime

# --- 設定 ---
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1x7pDDkRpf4EO2x-T-T68vqoVc3i0WUXz07kG0sW3G6k/edit"

def main():
    st.set_page_config(page_title="Tide Data Parser", layout="centered")
    st.title("🌊 潮汐データ解析 (A列集約型)")

    conn = st.connection("gsheets", type=GSheetsConnection)

    # 地点と日時の選択
    target_point = st.selectbox("地点コード", ["HS", "KUMAMOTO"])
    target_dt = st.datetime_input("釣行日時", datetime.now())

    if st.button("📡 データを読み込んで解析"):
        try:
            # 1. スプレッドシート読み込み（ヘッダーなし、A列のみ取得）
            df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=target_point, ttl=0, header=None)
            
            # 2. ターゲットの日付文字列 (例: 2026-01-01)
            date_str = target_dt.strftime('%Y-%m-%d')
            
            # 3. A列(0番目の列)から、日付を含む行を検索
            # セルの中に日付が含まれている行を特定します
            mask = df[0].astype(str).str.contains(date_str)
            row = df[mask]
            
            if row.empty:
                st.warning(f"シート '{target_point}' 内に {date_str} の行が見つかりません。")
                return

            # 4. A列の文字列からJSON部分を抽出
            # セルの内容例: 2026-01-01 HS {data: ...} のような形を想定
            full_text = row.iloc[0, 0]
            
            # 文字列の中から最初の '{' から最後までの部分をJSONとして抽出
            json_start_idx = full_text.find('{')
            if json_start_idx == -1:
                st.error("セル内に JSON形式 ({ ... }) のデータが見つかりませんでした。")
                return
            
            json_str_raw = full_text[json_start_idx:]
            
            # 5. JSONの整形と読み込み
            # JS形式のキー名（クォートなし）やシングルクォートを、Pythonのjsonライブラリが読める形式に補正
            # (正規表現でキーをダブルクォートで囲む処理)
            formatted_json = re.sub(r'(\w+):', r'"\1":', json_str_raw).replace("'", '"')
            
            day_data = json.loads(formatted_json)
            # もしトップレベルが {data: [...]} のリスト形式なら、最初の要素を取得
            if "data" in day_data:
                day_data = day_data["data"][0]

            # --- 6. 潮汐計算 ---
            target_hour = target_dt.hour
            target_min = target_dt.minute
            current_time_val = target_hour + (target_min / 60.0)

            # 現在の潮位
            tide_cm = day_data['hourly'][target_hour]

            # フェーズ判定
            events = day_data['events']
            parsed_events = []
            for ev in events:
                # "13: 4" のようなスペース混じりを解消してパース
                time_part = ev['time'].replace(' ', '')
                h, m = map(int, time_part.split(':'))
                parsed_events.append({"time": h + (m/60.0), "type": ev['type'], "cm": ev['cm']})
            
            # 前後のイベントを特定
            past_events = [e for e in parsed_events if e['time'] <= current_time_val]
            future_events = [e for e in parsed_events if e['time'] > current_time_val]
            
            phase = "潮止まり付近"
            if past_events and future_events:
                last_ev = past_events[-1]
                next_ev = future_events[0]
                if last_ev['type'] == 'low' and next_ev['type'] == 'high':
                    phase = "上げ潮"
                elif last_ev['type'] == 'high' and next_ev['type'] == 'low':
                    phase = "下げ潮"

            # --- 7. 結果表示 ---
            st.success("✅ 解析完了")
            
            col1, col2 = st.columns(2)
            col1.metric("推定潮位", f"{tide_cm} cm")
            col2.metric("潮汐状態", phase)
            
            with st.expander("生データの確認"):
                st.code(json.dumps(day_data, indent=2, ensure_ascii=False))

        except Exception as e:
            st.error(f"解析エラー: {e}")
            st.info("A列のデータが正しいJSON形式を含んでいるか確認してください。")

if __name__ == "__main__":
    main()
