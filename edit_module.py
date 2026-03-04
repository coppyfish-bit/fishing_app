import streamlit as st
import pandas as pd

def show_edit_page(conn, url, weather_func, station_func, tide_func, moon_func, tide_name_func):
    st.subheader("🧪 潮位取得テストモード")
    
    # 1. スプレッドシート読み込み
    df = conn.read(spreadsheet=url, ttl="0s")
    if df.empty:
        st.error("スプレッドシートが空です。")
        return

    # 最新の1件を対象にする
    target_idx = df.index[-1]
    row = df.loc[target_idx]
    
    st.info(f"対象データ ID:{target_idx} | 日時: {row['datetime']} | 場所: {row['場所']}")

    if st.button("🚀 この日時の潮位を計算してみる"):
        with st.container(border=True):
            try:
                # --- 工程1: 日時の変換 ---
                raw_dt = str(row['datetime']).strip()
                dt_obj = pd.to_datetime(raw_dt)
                st.write(f"① 解析された日時: `{dt_obj}`")

                # --- 工程2: 観測所の特定 ---
                lat, lon = float(row['lat']), float(row['lon'])
                station = station_func(lat, lon)
                st.write(f"② 判定された観測所: `{station['name']}` (Code: {station['code']})")

                # --- 工程3: 潮汐データの取得 ---
                st.write("③ `tide_func` を実行中...")
                d_data = tide_func(station['code'], dt_obj)
                
                # --- 結果表示 ---
                st.write("---")
                st.write("### 📊 取得結果（生データ）")
                st.json(d_data)

                if d_data and d_data.get('cm') != 0:
                    st.success(f"✅ 成功！ 潮位は {d_data['cm']}cm です。")
                else:
                    st.error("❌ 失敗: 潮位が 0cm です。JSONにデータがないか、日時がマッチしていません。")
                    
                    # 2026年問題の切り分け
                    if dt_obj.year == 2026:
                        st.warning("⚠️ 検索対象が 2026年 です。参照先のJSONファイルが2026年に対応しているか確認が必要です。")

            except Exception as e:
                st.exception(e)

    st.divider()
    st.write("※このコードは確認専用です。確認が終わったら元のコードに戻してください。")
