import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta
import traceback

# --- 設定 ---
SPREADSHEET_URL = st.secrets.get("private_gsheets_url", "") # 自身のURLに書き換えてください

def get_tide_details(dt, station_code="HS"):
    """
    GitHubの HS.json から潮汐データを取得し、全項目を計算する
    """
    d = dt.date()
    # 2026年フォルダの HS.json を参照
    url = f"https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{d.year}/HS.json"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # 時刻の照合
        t_str = dt.strftime('%H:%M')
        times = sorted(data.keys())
        closest_t = min(times, key=lambda x: abs(datetime.strptime(x, '%H:%M') - datetime.strptime(t_str, '%H:%M')))
        tide_cm = float(data[closest_t])
        
        # --- 潮汐解析ロジック ---
        # 簡易的に前後12時間の極値（山・谷）を計算するロジック（実際はループで判定）
        # ここでは計算結果の辞書構造を正しく作ることが優先
        
        res = {
            "tide_cm": round(tide_cm, 1),
            "tide_name": "中潮",       # 本来は月齢から計算
            "moon_age": 12.5,          # 本来は日付から計算
            "tide_phase": "下げ7分",    # 潮位の変化から判定
            "next_h_min": 140,         # 次の満潮まで(分)
            "next_l_min": 320,         # 次の干潮まで(分)
            "p_high_t": "09:45",       # 直前の満潮時刻
            "p_low_t": "03:20"         # 直前の干潮時刻
        }
        return res

    except Exception as e:
        st.error(f"潮汐取得エラー: {e}")
        return None

def main():
    st.set_page_config(page_title="Fishing App - Tide Test", layout="wide")
    st.title("🌊 潮汐データ取得システム (HS.json版)")

    # 1. セッション状態の初期化
    if 'tide_cm' not in st.session_state:
        st.session_state.tide_cm = 0.0
    if 'tide_phase' not in st.session_state:
        st.session_state.tide_phase = "-"

    # 2. メイン操作エリア
    st.info("ボタンを押すと GitHub の `data/2026/HS.json` を読み込みます。")
    
    col1, col2 = st.columns(2)
    
    with col1:
        target_dt = st.datetime_input("取得対象日時", datetime.now())
        if st.button("🔴 潮汐情報を取得"):
            with st.spinner("取得中..."):
                tide_info = get_tide_details(target_dt, "HS")
                
                if tide_info:
                    st.success("取得成功！")
                    # session_state を一気に更新
                    st.session_state.tide_cm = tide_info["tide_cm"]
                    st.session_state.tide_name = tide_info["tide_name"]
                    st.session_state.tide_phase = tide_info["tide_phase"]
                    st.session_state.moon_age = tide_info["moon_age"]
                    st.session_state.next_high_m = tide_info["next_h_min"]
                    st.session_state.next_low_m = tide_info["next_l_min"]
                    st.session_state.prev_high_t = tide_info["p_high_t"]
                    st.session_state.prev_low_t = tide_info["p_low_t"]
                else:
                    st.error("データの取得に失敗しました。URLを確認してください。")

    with col2:
        st.write("### 📋 取得済みデータ一覧")
        # 取得した値を表示
        data_to_show = {
            "項目": ["潮位(cm)", "潮位フェーズ", "次の満潮まで(分)", "次の干潮まで(分)", "直前の満潮時刻", "直前の干潮時刻"],
            "現在の値": [
                st.session_state.get('tide_cm', '-'),
                st.session_state.get('tide_phase', '-'),
                st.session_state.get('next_high_m', '-'),
                st.session_state.get('next_low_m', '-'),
                st.session_state.get('prev_high_t', '-'),
                st.session_state.get('prev_low_t', '-')
            ]
        }
        st.table(pd.DataFrame(data_to_show))

    st.divider()
    
    # 3. 保存エリア（スプレッドシート連携用）
    st.subheader("💾 スプレッドシートへの保存確認")
    if st.button("この内容で保存（シミュレート）"):
        # 実際に保存する際のデータ構造
        save_data = {
            "日付": target_dt.strftime('%Y-%m-%d %H:%M'),
            "潮位_cm": st.session_state.tide_cm,
            "潮位フェーズ": st.session_state.tide_phase,
            "次の満潮まで_分": st.session_state.get('next_high_m'),
            "次の干潮まで_分": st.session_state.get('next_low_m'),
            "直前の満潮_時刻": st.session_state.get('prev_high_t'),
            "直前の干潮_時刻": st.session_state.get('prev_low_t')
        }
        st.json(save_data)
        st.info("※ここに `conn.create` を入れることでスプレッドシートに書き込まれます。")

if __name__ == "__main__":
    main()
