import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 設定 ---
# 2026-02-27: AIとの会話は学習に使用したり外部に漏れたりしません。釣果情報も共有しません。
st.set_page_config(page_title="Fishing Log System", layout="wide")

# スプレッドシートのURL（ご自身のURLに書き換えてください）
URL = st.secrets.get("connections", {}).get("gsheets", {}).get("spreadsheet", "")

# --- 潮汐解析関数 (2025/2026年両対応) ---
def get_tide_details(dt, station_code="HS"):
    """
    日時と地点コードから潮位(cm)と10分割フェーズを算出する。
    """
    result = {"cm": 0, "phase": "不明", "events": [], "hourly": []}
    try:
        combined_events = []
        hourly_data = []
        
        # 前後3日分をチェックして日付またぎに対応
        for d in [dt - timedelta(days=1), dt, dt + timedelta(days=1)]:
            url = f"https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{d.year}/{station_code}.json"
            try:
                r = requests.get(url, timeout=5)
                if r.status_code != 200: continue
                raw = r.json()
                
                # 2025年(リスト)と2026年(辞書)の構造を自動判別
                items = raw.get('data', raw) if isinstance(raw, dict) else raw
                
                # 日付一致確認 (YYYYMMDD)
                search_date = d.strftime("%Y%m%d")
                day_info = next((i for i in items if str(i.get('date','')).replace("-","").replace(" ","") == search_date), None)
                
                if day_info:
                    # 干満イベントの統合
                    for ev in day_info.get('events', []):
                        t_str = str(ev.get('time', '')).strip()
                        if ":" in t_str:
                            ev_dt = pd.to_datetime(f"{d.strftime('%Y-%m-%d')} {t_str}")
                            combined_events.append({"time": ev_dt, "type": ev.get('type', '').lower()})
                    # 当日の1時間ごとの潮位
                    if d.date() == dt.date():
                        hourly_data = [int(v) for v in day_info.get('hourly', []) if str(v).strip().replace('-','').isdigit()]
            except: continue

        # 1. 潮位計算
        if len(hourly_data) >= 24:
            h, mi = dt.hour, dt.minute
            t1, t2 = hourly_data[h], hourly_data[(h+1)%24]
            result["cm"] = int(round(t1 + (t2 - t1) * (mi / 60.0)))

        # 2. 10分割フェーズ判定
        events = sorted(combined_events, key=lambda x: x['time'])
        prev_ev = next((e for e in reversed(events) if e['time'] <= dt), None)
        next_ev = next((e for e in events if e['time'] > dt), None)

        if prev_ev and next_ev:
            total_sec = (next_ev['time'] - prev_ev['time']).total_seconds()
            elapsed_sec = (dt - prev_ev['time']).total_seconds()
            if total_sec > 0:
                step = min(max(int((elapsed_sec / total_sec) * 10) + 1, 1), 10)
                label = "上げ" if "low" in prev_ev['type'] else "下げ"
                result["phase"] = f"{label}{step}分"
        
        return result
    except:
        return result

# --- メイン UI ---
def main():
    st.title("🎣 釣果ログシステム")
    
    # GSheets 接続
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # タブ作成
    tab1, tab2 = st.tabs(["📝 新規登録", "📊 データ表示・編集"])
    
    with tab1:
        st.subheader("新しい釣果を記録")
        with st.form("input_form"):
            col1, col2 = st.columns(2)
            fish_dt = col1.datetime_input("日時", value=datetime.now())
            fish_name = col2.text_input("魚種", value="キジハタ")
            
            place = st.text_input("場所", value="苓北")
            st_code = st.text_input("地点コード(JSONファイル名)", value="HS")
            
            memo = st.text_area("備考")
            
            submit = st.form_submit_button("潮位を取得して保存")
            
            if submit:
                # 潮位取得
                with st.spinner("潮位解析中..."):
                    tide = get_tide_details(fish_dt, st_code)
                
                # 保存データ作成
                new_data = pd.DataFrame([{
                    "datetime": fish_dt.strftime('%Y-%m-%d %H:%M:%S'),
                    "魚種": fish_name,
                    "場所": place,
                    "潮位_cm": tide["cm"],
                    "潮位フェーズ": tide["phase"],
                    "備考": memo
                }])
                
                # スプレッドシート読み込み & 結合
                existing_df = conn.read(spreadsheet=URL, ttl="0s")
                updated_df = pd.concat([existing_df, new_data], ignore_index=True)
                
                # 更新
                conn.update(spreadsheet=URL, data=updated_df)
                st.success(f"保存完了！ 潮位: {tide['cm']}cm ({tide['phase']})")

    with tab2:
        st.subheader("登録済みデータ")
        df = conn.read(spreadsheet=URL, ttl="0s")
        if not df.empty:
            st.dataframe(df.iloc[::-1], use_container_width=True)
        else:
            st.info("データがありません。")

if __name__ == "__main__":
    main()
