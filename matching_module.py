import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.title("🌊 潮位データ取得デバッグ（本渡瀬戸）")

# 1. 取得設定
now = datetime.now()
st.info(f"現在時刻 (システム): {now.strftime('%Y-%m-%d %H:%M:%S')}")

# 気象庁の本渡(HS)データURL
url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/HS.txt"

if st.button("🔍 データを取得して解析実行"):
    try:
        # --- ステップ1: 生データのダウンロード ---
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            st.success("✅ 気象庁サーバーへの接続に成功しました。")
        else:
            st.error(f"❌ 接続失敗 (Status Code: {res.status_code})")
            st.stop()

        # --- ステップ2: 今日のデータ行を抽出 ---
        lines = res.text.splitlines()
        # 気象庁フォーマット: 72-74年, 74-76月, 76-78日, 78-80地点コード
        target_y, target_m, target_d = int(now.strftime('%y')), now.month, now.day
        
        day_line = None
        for line in lines:
            if len(line) < 100: continue
            try:
                line_y = int(line[72:74])
                line_m = int(line[74:76])
                line_d = int(line[76:78])
                line_code = line[78:80]
                
                if line_y == target_y and line_m == target_m and line_d == target_d and line_code == "HS":
                    day_line = line
                    break
            except: continue

        if day_line:
            st.write("### 📄 解析結果")
            st.markdown("**抽出された生データ行:**")
            st.code(day_line, language="text")

            # --- ステップ3: 1時間ごとの潮位をテーブル化 ---
            hourly_tides = [int(day_line[i*3 : (i+1)*3].strip() or 0) for i in range(24)]
            df_tides = pd.DataFrame([hourly_tides], columns=[f"{i}時" for i in range(24)])
            st.write("**📊 1時間ごとの潮位 (cm):**")
            st.table(df_tides)

            # --- ステップ4: 「最も近い」潮位の判定ロジック ---
            current_hour = now.hour
            current_min = now.minute
            
            if current_min >= 30 and current_hour < 23:
                target_hour = current_hour + 1
                reason = "30分を過ぎているため、次の正時を採用"
            else:
                target_hour = current_hour
                reason = "30分未満のため、現在の正時を採用"
            
            selected_tide = hourly_tides[target_hour]
            
            st.metric(label=f"判定された現在の潮位 ({target_hour}時のデータ)", 
                      value=f"{selected_tide} cm", 
                      delta=reason, delta_color="off")

            # --- ステップ5: 満干潮イベントのデバッグ ---
            st.write("**🌊 満干潮イベントの解析:**")
            events = []
            # 満潮(80〜107列), 干潮(108〜135列)
            for start, e_type in [(80, "満潮"), (108, "干潮")]:
                for i in range(4):
                    pos = start + (i * 7)
                    t_str = day_line[pos : pos+4].strip()
                    if t_str and t_str != "9999":
                        events.append({"時刻": f"{t_str[:2]}:{t_str[2:]}", "タイプ": e_type})
            st.json(events)

        else:
            st.warning(f"指定された日付 ({target_y}/{target_m}/{target_d}) の地点 'HS' が見つかりませんでした。")

    except Exception as e:
        st.error(f"プログラム実行中にエラーが発生しました: {e}")
