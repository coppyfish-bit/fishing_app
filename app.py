import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 設定 ---
# 共有設定済みのスプレッドシートURL
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1x7pDDkRpf4EO2x-T-T68vqoVc3i0WUXz07kG0sW3G6k/edit"

def main():
    st.set_page_config(page_title="Tide Read Test", layout="centered")
    st.title("🔍 潮汐データ読み取りテスト")

    # GSheets接続
    conn = st.connection("gsheets", type=GSheetsConnection)

    # 地点（タブ名）を選択
    target_point = st.selectbox("読み込む地点（タブ名）", ["HS", "KUMAMOTO"])
    target_dt = st.datetime_input("シミュレート日時", datetime.now())

    if st.button("📡 データを読み込んで解析"):
        try:
            # 1. 指定されたタブを読み込み
            # ttl=0 でキャッシュを無効化し、常に最新のシートを読みます
            df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=target_point, ttl=0)
            
            # 2. 列名の不一致を強制解決 (1行目を「日付」「時刻」「潮位」とみなす)
            # 4列目以降に「タイプ」などがある場合も考慮
            new_columns = ["日付", "時刻", "潮位"]
            remaining_cols = [f"col_{i}" for i in range(len(df.columns) - 3)]
            df.columns = new_columns + (["タイプ"] if len(df.columns) > 3 else remaining_cols)
            
            # 3. データのクレンジング
            # 日付と時刻を文字列として正規化
            df['日付'] = df['日付'].astype(str).str.strip()
            df['時刻'] = df['時刻'].astype(str).str.strip()
            
            # 4. 日付でフィルタリング
            date_str = target_dt.strftime('%Y-%m-%d')
            # 2026-01-01 でも 2026/01/01 でも引っかかるように調整
            date_query = date_str.replace('-', '[/-]') 
            df_day = df[df['日付'].str.contains(date_query, regex=True)].copy()

            if df_day.empty:
                st.warning(f"シート '{target_point}' 内に {date_str} のデータが見つかりませんでした。")
                st.write("シート内の日付の例:", df['日付'].unique()[:3])
            else:
                # 5. 最も近い時刻のデータを特定
                # 時刻を計算用に変換
                df_day['time_obj'] = pd.to_datetime(df_day['時刻'], format='%H:%M', errors='coerce')
                target_time_obj = datetime.strptime(target_dt.strftime('%H:%M'), '%H:%M')
                
                # 無効な時刻行を除外
                df_day = df_day.dropna(subset=['time_obj'])
                
                # 最も近い行を取得
                idx = (df_day['time_obj'] - target_time_obj).abs().idxmin()
                res = df_day.loc[idx]

                # 6. 結果表示
                st.success(f"✅ {target_point} のデータ読み取りに成功")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("取得潮位", f"{res['潮位']} cm")
                col2.metric("参照時刻", res['時刻'])
                col3.metric("フェーズ", res.get('タイプ', 'データなし'))

                st.write("---")
                st.write("▼ 読み込んだ当日の全データ（確認用）")
                st.dataframe(df_day[['日付', '時刻', '潮位', 'タイプ']])

        except Exception as e:
            st.error(f"エラーが発生しました: {e}")
            st.info("スプレッドシートの1行目が '日付', '時刻', '潮位' の順になっているか確認してください。")

if __name__ == "__main__":
    main()
