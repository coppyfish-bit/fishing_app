import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import re
from datetime import datetime

# --- 設定 ---
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1x7pDDkRpf4EO2x-T-T68vqoVc3i0WUXz07kG0sW3G6k/edit"

def main():
    st.set_page_config(page_title="Tide Direct Reader", layout="centered")
    st.title("🌊 スプレッドシート直接解析 (A列結合型)")

    # GSheets接続
    conn = st.connection("gsheets", type=GSheetsConnection)

    # 地点（タブ名）と日時の選択
    target_point = st.selectbox("地点コード", ["HS", "KUMAMOTO"])
    target_dt = st.datetime_input("釣行日時", datetime.now())

    if st.button("📡 スプレッドシートを直接読み込む"):
        try:
            # 1. A列の全データを取得（ヘッダーなし）
            df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=target_point, ttl=0, header=None)
            
            # 2. A列の全行を一つの文字列に合体させる
            # 画像のように行が分かれている場合、これをしないとJSONとして成立しません
            full_text = "".join(df[0].astype(str).tolist())
            
            # 3. 日付で対象のブロックを探す
            date_str = target_dt.strftime('%Y-%m-%d')
            
            # JSONの「塊」を抽出するための正規表現
            # {"date":"2026-01-01" ... } のようなパターンを探します
            # ※ A列に複数の日のデータが連続して入っている場合に対応
            pattern = r'\{[^{]*"date"\s*:\s*"' + date_str + r'"[^}]*\}'
            match = re.search(pattern, full_text)

            if not match:
                # 正規表現でダメな場合、簡易的な切り出しを試行
                search_term = f'"date":"{date_str}"'
                if search_term in full_text:
                    start_idx = full_text.find('{', full_text.rfind('{', 0, full_text.find(search_term)))
                    end_idx = full_text.find('}', start_idx) + 1
                    json_str = full_text[start_idx:end_idx]
                else:
                    st.warning(f"{date_str} のデータが見つかりません。")
                    return
            else:
                json_str = match.group()

            # 4. JSONの形式補正（クォートなしキーへの対応）
            # キー名をダブルクォートで囲む
            json_str = re.sub(r'(\w+):', r'"\1":', json_str).replace("'", '"')
            
            # 5. パースして潮位を取り出す
            day_data = json.loads(json_str)
            
            hour = target_dt.hour
            tide_cm = day_data['hourly'][hour]
            
            # 結果表示
            st.success(f"✅ {date_str} のデータを読み込みました")
            
            c1, c2 = st.columns(2)
            c1.metric("推定潮位", f"{tide_cm} cm")
            
            # 簡易フェーズ判定（次の時間との比較）
            next_hour = (hour + 1) % 24
            next_tide = day_data['hourly'][next_hour]
            phase = "上げ潮" if next_tide > tide_cm else "下げ潮"
            c2.metric("潮の状態", phase)

            with st.expander("抽出されたJSONを確認"):
                st.code(json.dumps(day_data, indent=2, ensure_ascii=False))

        except Exception as e:
            st.error(f"解析エラー: {e}")
            st.info("スプレッドシートの共有設定と、データの形式を再確認してください。")

if __name__ == "__main__":
    main()
