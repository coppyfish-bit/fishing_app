import streamlit as st
import requests
import pandas as pd
from datetime import datetime

def show_matching_page(df=None):
    """
    デバッグ専用: 
    既存のapp.pyからの呼び出し(show_matching_page)に対応しつつ、
    潮位取得のプロセスを画面に全表示します。
    """
    st.title("🌊 潮位取得プロセス・デバッグ")
    st.caption("本渡瀬戸（HS）の気象庁データ解析状況")

    # 1. 現在時刻の確認
    now = datetime.now()
    st.write(f"### 1. 時刻確認")
    st.write(f"現在時刻: `{now.strftime('%Y-%m-%d %H:%M:%S')}`")

    # 2. 気象庁データへのアクセス
    st.write(f"### 2. データ取得状況")
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/HS.txt"
    st.write(f"アクセス先URL: `{url}`")

    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            st.success("✅ 気象庁サーバーに接続成功")
            
            # 生データの解析
            lines = res.text.splitlines()
            target_y, target_m, target_d = int(now.strftime('%y')), now.month, now.day
            
            day_line = None
            for line in lines:
                if len(line) < 100: continue
                # 気象庁フォーマット解析
                try:
                    line_y = int(line[72:74])
                    line_m = int(line[74:76])
                    line_d = int(line[76:78])
                    line_code = line[78:80].strip()
                    
                    if line_y == target_y and line_m == target_m and line_d == target_d and line_code == "HS":
                        day_line = line
                        break
                except: continue

            if day_line:
                st.write("### 3. 解析データ詳細")
                st.info("今日のデータ行を正常に抽出しました。")
                st.code(day_line, language="text")

                # 潮位リストの抽出
                hourly_tides = [int(day_line[i*3 : (i+1)*3].strip() or 0) for i in range(24)]
                
                # テーブル表示
                st.write("**🕒 24時間の潮位推移 (cm)**")
                df_tide = pd.DataFrame([hourly_tides], columns=[f"{i}時" for i in range(24)])
                st.table(df_tide)

                # 最も近い時間の判定
                current_hour = now.hour
                current_min = now.minute
                if current_min >= 30 and current_hour < 23:
                    target_hour = current_hour + 1
                    reason = "30分以降のため、次の正時のデータを採用"
                else:
                    target_hour = current_hour
                    reason = "30分未満のため、現在の正時のデータを採用"

                st.metric(label=f"判定された潮位 ({target_hour}時基準)", 
                          value=f"{hourly_tides[target_hour]} cm",
                          delta=reason)

                # 満干潮イベント
                st.write("### 4. 潮汐イベント情報")
                events = []
                today_str = now.strftime('%Y%m%d')
                for start, e_type in [(80, "満潮"), (108, "干潮")]:
                    for i in range(4):
                        pos = start + (i * 7)
                        t_str = day_line[pos : pos+4].strip()
                        if t_str and t_str != "9999":
                            events.append({"時刻": f"{t_str[:2]}:{t_str[2:]}", "タイプ": e_type})
                st.json(events)
            else:
                st.error(f"❌ 今日のデータ行（HS, 日付:{target_m}/{target_d}）が見つかりませんでした。")
        else:
            st.error(f"❌ サーバー応答エラー: {res.status_code}")

    except Exception as e:
        st.error(f"⚠️ 予期せぬエラーが発生しました: {str(e)}")

# テスト実行用
if __name__ == "__main__":
    show_matching_page()
