import streamlit as st
import pandas as pd
import requests
import traceback

# AIとの会話は学習に使用したり外部に漏れたりしません。釣果情報も共有しません。

def show_edit_page(conn, url, weather_func, station_func, tide_func, moon_func, tide_name_func):
    st.subheader("🧪 潮位取得：完全デバッグモード")
    
    # 1. スプレッドシート読み込み
    df = conn.read(spreadsheet=url, ttl="0s")
    if df.empty:
        st.error("スプレッドシートが空です。")
        return

    # 最新の1件をテスト対象にする
    target_idx = df.index[-1]
    row = df.loc[target_idx]
    
    st.info(f"検証対象データ ID:{target_idx}\n- 日時: {row['datetime']}\n- 場所: {row['場所']}\n- 座標: {row['lat']}, {row['lon']}")

    if st.button("🚀 潮位取得プロセスを実行"):
        try:
            # --- 手順1: 日時と座標の準備 ---
            dt = pd.to_datetime(str(row['datetime']).strip())
            lat, lon = float(row['lat']), float(row['lon'])
            st.write(f"① 解析日時: `{dt}` (Year: {dt.year})")

            # --- 手順2: 観測所の特定 ---
            station = station_func(lat, lon)
            st.write(f"② 判定観測所: `{station['name']}` (Code: `{station['code']}`)")

            # --- 手順3: URL生成 ---
            user = "coppyfish-bit"
            repo = "fishing_app"
            target_url = f"https://raw.githubusercontent.com/{user}/{repo}/main/data/{dt.year}/{station['code']}.json"
            st.write(f"③ 生成URL: `{target_url}`")

            # --- 手順4: HTTPリクエスト ---
            res = requests.get(target_url)
            st.write(f"④ HTTPステータス: `{res.status_code}`")
            
            if res.status_code != 200:
                st.error("❌ ファイルが見つかりません。リポジトリ名やフォルダ構成を再確認してください。")
                return

            # --- 手順5: JSONパースと解析 ---
            st.write("⑤ `get_tide_details` を実行します...")
            
            # ここで get_tide_details(res, dt) を実行
            # ※ get_tide_details側で res.json() を行う想定
            data = res.json()
            
            # 日付マッチングのデバッグ
            target_date_clean = dt.strftime("%Y-%m-%d").replace("-0", "-").replace("-", "").replace(" ", "")
            st.write(f"🔍 検索キー: `{target_date_clean}`")
            
            day_info = None
            for item in data.get('data', []):
                json_date_clean = str(item.get('date', '')).replace("-", "").replace(" ", "")
                if json_date_clean == target_date_clean:
                    day_info = item
                    break
            
            if day_info:
                st.success(f"✅ 日付一致！データを発見しました。")
                st.json(day_info)
                
                # 補間計算のテスト
                hourly = [int(v) for v in day_info['hourly']]
                h, mi = dt.hour, dt.minute
                t1, t2 = hourly[h], hourly[(h+1)%24]
                current_cm = int(round(t1 + (t2 - t1) * (mi / 60.0)))
                st.metric("算出潮位", f"{current_cm} cm")
            else:
                st.warning("⚠️ JSON内に該当日付が見つかりません。")
                st.write("JSON内の日付サンプル:", [d.get('date') for d in data.get('data', [])[:3]])

        except Exception as e:
            st.error(f"❌ 実行エラー: {e}")
            st.code(traceback.format_exc())

    st.divider()
    st.caption("このモードは確認専用です。正しく計算されることが確認できたら元のコードに戻してください。")
