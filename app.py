import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import traceback

def get_hondo_tide_standalone():
    """
    本渡(hondo)の2025年データを固定で取得し、現在時刻の潮汐情報を計算する単体関数
    """
    st.subheader("🛠 HS地点 潮汐取得テストユニット")
    
    if st.button("🔴 今すぐ本渡(HS)の潮汐を取得"):
        # 1. 設定値
        now = datetime.now()
        station_code = "hondo" 
        target_year = 2025 # 確実にデータがある2025年を参照
        url = f"https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{target_year}/{station_code}.json"
        
        st.info(f"🛰 通信開始: {url}")
        
        try:
            # 2. JSON取得
            res = requests.get(url, timeout=5)
            res.raise_for_status()
            data = res.json()
            
            # 3. 時刻の照合 (HH:mm)
            t_str = now.strftime('%H:%M')
            st.write(f"⏱ 照合時刻: {t_str}")
            
            # 4. 潮位の取得（一番近い時間を探す）
            times = sorted(data.keys())
            closest_t = min(times, key=lambda x: abs(datetime.strptime(x, '%H:%M') - datetime.strptime(t_str, '%H:%M')))
            tide_cm = float(data[closest_t])
            
            # 5. 【重要】本来の計算ロジック（簡易版）
            # ここで「次の満潮」などを計算するロジックをシミュレート
            # 本来はここで data をループして極値（山と谷）を探します
            
            # デバッグ用のダミー計算結果（構造の確認用）
            result = {
                "潮位_cm": tide_cm,
                "潮位フェーズ": "下げ5分(計算例)",
                "次の満潮まで_分": 145,
                "次の干潮まで_分": 320,
                "直前の満潮_時刻": "09:15",
                "直前の干潮_時刻": "03:40",
                "潮名": "中潮",
                "月齢": 12.4
            }
            
            # 6. 画面への表示
            st.success("✅ 取得・計算完了")
            
            # 結果をテーブル形式で表示
            res_df = pd.DataFrame([result])
            st.table(res_df)
            
            # 7. session_state への書き込み（app.pyの入力欄と連動させる場合）
            st.session_state.tide_cm = result["潮位_cm"]
            st.session_state.tide_phase = result["潮位フェーズ"]
            st.session_state.next_high_m = result["次の満潮まで_分"]
            st.session_state.next_low_m = result["次の干潮まで_分"]
            st.session_state.prev_high_t = result["直前の満潮_時刻"]
            st.session_state.prev_low_t = result["直前の干潮_時刻"]
            st.session_state.tide_name = result["潮名"]
            
            st.write("📌 `st.session_state` の各変数に値を格納しました。")

        except Exception as e:
            st.error(f"❌ エラー発生: {e}")
            st.code(traceback.format_exc())

# 実行
get_hondo_tide_standalone()
