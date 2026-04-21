import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta

# --- 設定 ---
# スプレッドシートのURL（自身のものに書き換えてください）
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1x7pDDkRpf4EO2x-T-T68vqoVc3i0WUXz07kG0sW3G6k/edit"

# 地点コードと座標の対応表（ここに全国の地点を追加していきます）
# lat/lon はおおよその位置でOKです。現在地から一番近い地点が選ばれます。
LOCATIONS = {
    "HS": {"name": "本渡瀬戸", "lat": 32.45, "lon": 130.19},
    "KUMAMOTO": {"name": "熊本港", "lat": 32.76, "lon": 130.59},
    # "OITA": {"name": "大分港", "lat": 33.26, "lon": 131.67}, # 例
}

def get_nearest_point(lat, lon):
    """
    現在地（緯度・経度）から最も近い地点コードを返す
    """
    if lat is None or lon is None:
        return "HS" # 位置情報が取れない場合のデフォルト
    
    nearest_code = min(
        LOCATIONS.keys(),
        key=lambda k: (LOCATIONS[k]["lat"] - lat)**2 + (LOCATIONS[k]["lon"] - lon)**2
    )
    return nearest_code

def main():
    st.set_page_config(page_title="Fishing App - National Tide", layout="wide")
    st.title("🌊 全国対応・潮汐自動取得システム")

    # GSheets接続設定
    conn = st.connection("gsheets", type=GSheetsConnection)

    # 1. 位置情報と日時の設定
    # ※実際にはGPS連携ライブラリを使いますが、ここでは手入力・シミュレート用にします
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        st.subheader("📍 釣行地点の設定")
        # 簡易的な位置情報シミュレーター
        lat = st.number_input("現在地の緯度", value=32.45, format="%.5f")
        lon = st.number_input("現在地の経度", value=130.19, format="%.5f")
        
        target_point = get_nearest_point(lat, lon)
        st.success(f"判定された地点: **{LOCATIONS[target_point]['name']} ({target_point})**")

    with col_input2:
        st.subheader("📅 日時の設定")
        target_dt = st.datetime_input("釣行日時", datetime.now())

    st.divider()

    # 2. 潮汐取得ボタン
    if st.button("🚀 この地点の潮汐を取得"):
        try:
            # 指定された地点コード（タブ名）のシートを読み込む
            df = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=target_point)
            
            # 日付でフィルタリング
            date_str = target_dt.strftime('%Y-%m-%d')
            df_day = df[df['日付'] == date_str].copy()

            if df_day.empty:
                st.error(f"指定された日付 ({date_str}) のデータが '{target_point}' シートにありません。")
            else:
                # 時刻の検索
                target_time_str = target_dt.strftime('%H:%M')
                df_day['time_dt'] = pd.to_datetime(df_day['時刻'], format='%H:%M')
                target_time_dt = datetime.strptime(target_time_str, '%H:%M')
                
                # 最も近い時刻の行を特定
                idx = (df_day['time_dt'] - target_time_dt).abs().idxmin()
                res = df_day.loc[idx]

                # --- 潮汐解析ロジック（簡易版） ---
                # 前後の「タイプ」列を見て、上げ・下げや満干潮時刻を特定
                events = df_day[df_day['タイプ'].isin(['high', 'low'])].copy()
                
                # 画面表示
                st.subheader(f"📊 {LOCATIONS[target_point]['name']} の潮汐情報")
                
                res_cols = st.columns(4)
                res_cols[0].metric("現在の潮位", f"{res['潮位']} cm")
                res_cols[1].metric("時刻", target_time_str)
                
                # 5項目の表示
                st.table(pd.DataFrame({
                    "項目": ["潮位", "フェーズ", "地点コード", "参照時刻"],
                    "値": [f"{res['潮位']}cm", res.get('タイプ', '-'), target_point, res['時刻']]
                }))

                # セッションへの保存
                st.session_state.tide_cm = res['潮位']
                st.session_state.point_code = target_point
                st.info("📌 データをセッションに格納しました。そのまま記録保存が可能です。")

        except Exception as e:
            st.error(f"読み込みエラー: {e}")
            st.info("スプレッドシートのタブ名が地点コード（HSなど）と完全に一致しているか確認してください。")

if __name__ == "__main__":
    main()
