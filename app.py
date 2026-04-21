import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import json
import re
from datetime import datetime

# --- 設定 ---
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1x7pDDkRpf4EO2x-T-T68vqoVc3i0WUXz07kG0sW3G6k/edit"

def main():
    st.set_page_config(page_title="Tide Force Parser", layout="wide")
    st.title("🌊 潮汐データ解析 (最終デバッグ版)")

    conn = st.connection("gsheets", type=GSheetsConnection)

    target_point = st.selectbox("地点コード", ["HS", "KUMAMOTO"])
    target_dt = st.datetime_input("釣行日時", datetime.now())

    if st.button("📡 データを強制解析"):
        try:
            # 1. スプレッドシート読み込み (キャッシュを完全に切り、全行読む)
            df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=target_point, ttl=0, header=None)
            
            if df.empty:
                st.error("シートが空です。データが正しく貼り付けられているか確認してください。")
                return

            # 2. 検索用の日付パターンを複数用意
            d = target_dt
            patterns = [
                d.strftime('%Y-%m-%d'),  # 2026-01-01
                d.strftime('%Y/%m/%d'),  # 2026/01/01
                f'"{d.year}-{d.month:02d}-{d.day:02d}"', # "2026-01-01"
                f'"{d.year}/{d.month:02d}/{d.day:02d}"'  # "2026/01/01"
            ]
            
            found_row_text = None
            for index, row in df.iterrows():
                cell_text = str(row[0])
                # いずれかの日付パターンが含まれているか
                if any(p in cell_text for p in patterns):
                    found_row_text = cell_text
                    break
            
            if not found_row_text:
                st.warning(f"シート '{target_point}' 内に該当する日付のデータが見つかりません。")
                st.info("【確認用】シートの最初の1行の内容を表示します:")
                st.code(df.iloc[0, 0][:500] + "...") # 先頭500文字を表示
                return

            # 3. JSON部分を無理やり切り出す
            # 最初の '{' から 最後の '}' までを抽出
            start_idx = found_row_text.find('{')
            end_idx = found_row_text.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                st.error("JSONの波括弧 { } が見つかりませんでした。")
                return
            
            json_str = found_row_text[start_idx:end_idx+1]

            # 4. JSONの超強力補正 (JavaScript風の未クォートキーに対応)
            # 全角スペースの削除
            json_str = json_str.replace('　', ' ')
            # シングルクォートをダブルクォートへ
            json_str = json_str.replace("'", '"')
            # キー名（例 data:）をダブルクォートで囲む
            json_str = re.sub(r'([{,])\s*(\w+)\s*:', r'\1"\2":', json_str)
            
            # 5. パース実行
            data_obj = json.loads(json_str)
            
            # {data: [{...}]} 構造の処理
            if "data" in data_obj and isinstance(data_obj["data"], list):
                day_data = data_obj["data"][0]
            else:
                day_data = data_obj

            # 6. 潮位の取得
            hour = target_dt.hour
            tide_cm = day_data['hourly'][hour]
            
            st.success(f"✅ 解析成功: {target_dt.strftime('%Y-%m-%d %H時')}")
            
            # 結果表示
            col1, col2 = st.columns(2)
            col1.metric("推定潮位", f"{tide_cm} cm")
            
            # フェーズ（上げ・下げ）の簡易計算
            next_hour_tide = day_data['hourly'][(hour + 1) % 24]
            phase = "上げ潮" if next_hour_tide > tide_cm else "下げ潮"
            col2.metric("潮の状態", phase)

        except Exception as e:
            st.error(f"解析に失敗しました: {e}")
            if 'json_str' in locals():
                st.subheader("解析しようとしたテキスト:")
                st.code(json_str[:1000])

if __name__ == "__main__":
    main()
