import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
from datetime import datetime

# --- 設定 ---
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1x7pDDkRpf4EO2x-T-T68vqoVc3i0WUXz07kG0sW3G6k/edit"

def main():
    st.set_page_config(page_title="Tide JSON Parser", layout="centered")
    st.title("🌊 潮汐データ解析テスト (JSONベタ貼り対応)")

    conn = st.connection("gsheets", type=GSheetsConnection)

    # 地点と日時の選択
    target_point = st.selectbox("地点コード", ["HS", "KUMAMOTO"])
    target_dt = st.datetime_input("釣行日時", datetime.now())

    if st.button("📡 スプレッドシートから取得・解析"):
        try:
            # 1. スプレッドシート読み込み（ヘッダーなし前提で列番号指定）
            df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=target_point, ttl=0, header=None)
            
            # A列(0):日付, B列(1):地点, C列(2):JSONテキスト と仮定
            date_str = target_dt.strftime('%Y-%m-%d')
            
            # 2. 該当日付の行を探す
            row = df[df[0].astype(str).str.contains(date_str)]
            
            if row.empty:
                st.warning(f"{date_str} のデータが見つかりません。")
                return

            # 3. C列(2)に入っているJSON文字列を解析
            raw_json_str = row.iloc[0, 2] # 3列目を取得
            # シングルクォートをダブルクォートに直すなどの整形が必要な場合があるため
            json_str = raw_json_str.replace("'", '"') 
            day_data = json.loads(json_str)
            
            # --- 潮汐計算 ---
            target_hour = target_dt.hour
            target_min = target_dt.minute
            current_time_val = target_hour + (target_min / 60.0)

            # 1. 現在の潮位（hourlyデータから取得）
            tide_cm = day_data['hourly'][target_hour]

            # 2. フェーズ判定（eventsデータから満干潮を探す）
            events = day_data['events']
            # 時刻を数値化して比較
            parsed_events = []
            for ev in events:
                h, m = map(int, ev['time'].split(':'))
                parsed_events.append({"time": h + (m/60.0), "type": ev['type'], "cm": ev['cm']})
            
            # 前後のイベントを探す
            past_events = [e for e in parsed_events if e['time'] <= current_time_val]
            future_events = [e for e in parsed_events if e['time'] > current_time_val]
            
            phase = "不明"
            if past_events and future_events:
                last_ev = past_events[-1]
                next_ev = future_events[0]
                if last_ev['type'] == 'low' and next_ev['type'] == 'high':
                    phase = "上げ潮"
                elif last_ev['type'] == 'high' and next_ev['type'] == 'low':
                    phase = "下げ潮"
            
            # --- 結果表示 ---
            st.success("✅ データの解析に成功しました")
            
            c1, c2 = st.columns(2)
            c1.metric("推定潮位", f"{tide_cm} cm")
            c2.metric("潮汐状態", phase)
            
            with st.expander("詳細なイベント情報"):
                st.write(f"直前のイベント: {past_events[-1] if past_events else 'なし'}")
                st.write(f"次回のイベント: {future_events[0] if future_events else 'なし'}")

        except Exception as e:
            st.error(f"解析エラー: {e}")
            st.info("スプレッドシートのC列に正しいJSON形式でデータが入っているか確認してください。")

if __name__ == "__main__":
    main()
