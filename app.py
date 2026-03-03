import streamlit as st
import requests
import re
from datetime import datetime, timedelta
import pandas as pd

# --- 設定 ---
st.set_page_config(page_title="Tide 3-Day Analyzer", layout="wide")
st.title("🌊 三日分（前・今・次）連結・潮位解析装置")

def get_day_events_full(date, code):
    """指定した日付の全イベントを抽出（エラーハンドリング強化版）"""
    url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{date.year}/{code}.txt"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code != 200: return []
        
        lines = res.text.splitlines()
        yy, mm, dd = date.strftime('%y'), str(date.month), str(date.day)
        # 本渡瀬戸(HS)等のスペース区切りに対応した正規表現
        pattern = rf"{yy}\s+{mm}\s+{dd}\s*{code}"
        
        line = next((l for l in lines if re.search(pattern, l)), None)
        if not line: return []
        
        nums = re.findall(r'-?\d+', line)
        if len(nums) < 27: return []

        event_data = nums[27:] # 年月日地点記号の後の数値
        day_events = []
        date_str = date.strftime('%Y%m%d')
        
        # 満潮(最初の4ペア)
        for i in range(0, 8, 2):
            if i+1 < len(event_data) and event_data[i] != "9999":
                t_str, cm = event_data[i], event_data[i+1]
                ev_t = datetime.strptime(date_str + t_str.zfill(4), '%Y%m%d%H%M')
                day_events.append({"time": ev_t, "type": "満潮", "cm": cm})
        
        # 干潮(次の4ペア)
        for i in range(8, 16, 2):
            if i+1 < len(event_data) and event_data[i] != "9999":
                t_str, cm = event_data[i], event_data[i+1]
                ev_t = datetime.strptime(date_str + t_str.zfill(4), '%Y%m%d%H%M')
                day_events.append({"time": ev_t, "type": "干潮", "cm": cm})
        
        return day_events
    except Exception as e:
        st.error(f"{date.strftime('%Y/%m/%d')} の解析に失敗: {e}")
        return []

# --- UI部 ---
with st.sidebar:
    st.header("🔍 解析条件")
    station_code = st.text_input("地点コード (例: HS, MS, RH)", "HS")
    # 現在の時刻を基準にする
    base_dt = datetime.now()
    st.write(f"基準時刻: {base_dt.strftime('%Y/%m/%d %H:%M')}")
    execute = st.button("🔥 三日間連結解析を実行", use_container_width=True)

if execute:
    # 1. 前日・当日・翌日のデータを取得して統合
    all_combined_events = []
    dates_to_fetch = [base_dt - timedelta(days=1), base_dt, base_dt + timedelta(days=1)]
    
    with st.spinner('三日分の魔導書を解読中...'):
        for d in dates_to_fetch:
            all_combined_events.extend(get_day_events_full(d, station_code))
    
    # 2. 時系列に並べ替え
    all_combined_events.sort(key=lambda x: x['time'])
    
    # 3. 直前(Prev)と直後(Next)を特定
    prev_ev = next((e for e in reversed(all_combined_events) if e['time'] <= base_dt), None)
    next_ev = next((e for e in all_combined_events if e['time'] > base_dt), None)

    # --- 結果表示 ---
    st.markdown("### 🎯 直近の潮汐状況")
    c1, c2 = st.columns(2)
    
    with c1:
        if prev_ev:
            st.metric("🎯 直前のイベント", f"{prev_ev['type']}", 
                      f"{prev_ev['time'].strftime('%m/%d %H:%M')} ({prev_ev['cm']}cm)")
        else:
            st.warning("直前のイベントが見つかりません")

    with c2:
        if next_ev:
            st.metric("⌛ 次のイベント", f"{next_ev['type']}", 
                      f"{next_event_time := next_ev['time'].strftime('%m/%d %H:%M')} ({next_ev['cm']}cm)")
        else:
            st.warning("翌日のイベントがまだ公開されていないか、見つかりません")

    # 4. 全イベントをテーブル表示（確認用）
    st.markdown("---")
    st.markdown("### 📋 三日間の全潮汐スケジュール")
    df = pd.DataFrame(all_combined_events)
    if not df.empty:
        df['時刻'] = df['time'].dt.strftime('%m/%d %H:%M')
        st.table(df[['時刻', 'type', 'cm']].rename(columns={'type': '種別', 'cm': '潮位(cm)'}))
