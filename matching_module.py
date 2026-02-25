import streamlit as st
import requests
from datetime import datetime

def show_matching_page(df):
    """
    潮汐データ取得の徹底デバッグ用ページ
    """
    st.title("🔍 潮汐取得デバッグモード")
    
    now = datetime.now()
    station_code = "HS"
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/{station_code}.txt"
    
    st.write(f"### 1. リクエスト情報")
    st.write(f"- 取得URL: `{url}`")
    st.write(f"- 現在時刻: `{now.strftime('%Y-%m-%d %H:%M:%S')}`")

    try:
        res = requests.get(url, timeout=10)
        st.write(f"- ステータスコード: `{res.status_code}`")
        
        if res.status_code != 200:
            st.error("気象庁のサーバーにアクセスできません。")
            return

        lines = res.text.splitlines()
        st.write(f"- 総行数: `{len(lines)}` 行")

        # 今日の日付判定用
        target_y = int(now.strftime('%y'))
        target_m = now.month
        target_d = now.day
        
        day_line = None
        st.write(f"### 2. 行特定プロセス (Target: Y={target_y}, M={target_m}, D={target_d})")
        
        for i, line in enumerate(lines):
            if len(line) < 80: continue
            
            # 生データをそのまま抽出（スライス位置確認）
            raw_y = line[72:74]
            raw_m = line[74:76]
            raw_d = line[76:78]
            raw_st = line[78:80]

            try:
                l_y = int(raw_y.strip())
                l_m = int(raw_m.strip())
                l_d = int(raw_d.strip())
                
                # 地点と日付が一致する行を1つだけ詳しく表示
                if l_y == target_y and l_m == target_m and l_d == target_d:
                    st.success(f"一致する行を発見しました (Index: {i})")
                    st.code(line, language="text")
                    st.write(f"抽出値: 年=`{l_y}`, 月=`{l_m}`, 日=`{l_d}`, 地点=`{raw_st}`")
                    day_line = line
                    break
            except:
                continue

        if not day_line:
            st.error("今日の日付の行が見つかりませんでした。スライス位置か日付形式が違います。")
            return

        st.write(f"### 3. 解析テスト")
        
        # 毎時潮位
        hourly = []
        for i in range(24):
            val = day_line[i*3 : (i+1)*3].strip()
            hourly.append(int(val) if val else 0)
        st.write(f"- 解析した毎時潮位: `{hourly}`")

        # 満干潮時刻の変換テスト
        events = []
        st.write("- 時刻変換テスト:")
        for start, e_type in [(80, "満潮"), (108, "干潮")]:
            for i in range(4):
                pos = start + (i * 7)
                t_str = day_line[pos : pos+4].replace(" ", "0") # 空白を0に
                
                if t_str and t_str != "9999" and t_str != "0000":
                    try:
                        # 変換に失敗しやすい場所
                        ev_t = datetime.strptime(now.strftime('%Y%m%d') + t_str.zfill(4), '%Y%m%d%H%M')
                        events.append({"time": ev_t, "type": e_type})
                        st.write(f"  OK: `{t_str}` -> `{ev_t}` ({e_type})")
                    except Exception as e:
                        st.error(f"  NG: `{t_str}` 変換失敗 -> `{e}`")

        events.sort(key=lambda x: x['time'])
        st.write(f"- 最終イベントリスト: `{events}`")

    except Exception as e:
        st.exception(e)
