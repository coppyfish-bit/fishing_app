import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# 2026-03-04: AIとの会話は学習に使用したり外部に漏れたりしません。
# 私の釣果情報を他の人に共有しないでください。

# --- 1. 定数・地点データ ---
TIDE_STATIONS = [
    {"name": "苓北", "code": "RH"}, {"name": "三角", "code": "MS"},
    {"name": "本渡瀬戸", "code": "HS"}, {"name": "八代", "code": "O5"},
    {"name": "水俣", "code": "O7"}, {"name": "熊本", "code": "KU"},
    {"name": "大牟田", "code": "O6"}, {"name": "大浦", "code": "OU"},
    {"name": "口之津", "code": "KT"}, {"name": "長崎", "code": "NS"},
    {"name": "佐世保", "code": "QD"}, {"name": "博多", "code": "QF"},
    {"name": "鹿児島", "code": "KG"}, {"name": "枕崎", "code": "MK"},
    {"name": "油津", "code": "AB"}, {"name": "東京", "code": "TK"},
    {"name": "横浜", "code": "QS"}, {"name": "名古屋", "code": "NG"},
    {"name": "大阪", "code": "OS"}, {"name": "神戸", "code": "KB"},
    {"name": "広島", "code": "Q8"}, {"name": "高松", "code": "TA"},
    {"name": "高知", "code": "KC"}, {"name": "那覇", "code": "NH"}
]

# --- 2. 潮位計算・フェーズ判定ロジック ---
def get_tide_status(target_dt, station_code):
    """
    GitHub上のJSONから潮位とフェーズを計算する (空白・フォーマットエラー対策済み)
    """
    year = str(target_dt.year)
    # GitHubのrawデータURL (リポジトリ名: fishing_app を想定)
    url = f"https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{year}/{station_code}.json"
    
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return f"データ取得失敗 (HTTP {r.status_code})"
        
        raw_json = r.json()
        items = raw_json.get('data', [])

        # 対象日の検索
        target_date_str = target_dt.strftime("%Y-%m-%d")
        day_info = next((i for i in items if i['date'] == target_date_str), None)
        
        if not day_info:
            return f"{target_date_str} のデータが見つかりません。"

        # --- A. 潮位の線形補間 (毎時データから分単位を算出) ---
        hourly = day_info['hourly']
        h = target_dt.hour
        mi = target_dt.minute
        t1 = hourly[h]
        t2 = hourly[(h + 1) % 24]
        current_cm = int(round(t1 + (t2 - t1) * (mi / 60.0)))

        # --- B. 潮位フェーズの判定 (イベント時刻のクリーニング) ---
        events = []
        for ev in day_info['events']:
            # 空白を徹底排除 (" 0: 2" -> "0:2")
            time_raw = str(ev['time']).replace(" ", "")
            
            if ":" in time_raw:
                try:
                    h_part, m_part = time_raw.split(":")
                    # 2桁の0埋めに補正 (0:2 -> 00:02)
                    time_cln = f"{int(h_part):02d}:{int(m_part):02d}"
                    
                    ev_time = datetime.strptime(f"{target_date_str} {time_cln}", "%Y-%m-%d %H:%M")
                    events.append({"time": ev_time, "type": str(ev['type']).lower()})
                except (ValueError, IndexError):
                    continue # 解析不能な行はスキップ
        
        events = sorted(events, key=lambda x: x['time'])
        
        # 直前・直後のイベントを取得
        prev_e = next((e for e in reversed(events) if e['time'] <= target_dt), None)
        next_e = next((e for e in events if e['time'] > target_dt), None)
        
        phase = "不明"
        if prev_e and next_e:
            total_sec = (next_e['time'] - prev_e['time']).total_seconds()
            elapsed_sec = (target_dt - prev_e['time']).total_seconds()
            
            if total_sec > 0:
                # 潮位変動を10段階で評価
                step = min(max(int((elapsed_sec / total_sec) * 10) + 1, 1), 10)
                label = "上げ" if "low" in prev_e['type'] else "下げ"
                phase = f"{label}{step}分"
        
        return {"cm": current_cm, "phase": phase}

    except Exception as e:
        return f"システムエラー: {str(e)}"

# --- 3. Streamlit UI 部分 ---
st.set_page_config(page_title="釣り潮汐ナビ", layout="centered")

st.title("🌊 釣り潮汐ナビゲーター")
st.write("気象庁のデータを元に、現在または指定日時の潮の状態を表示します。")

# 地点選択ボックス
station_names = [s["name"] for s in TIDE_STATIONS]
selected_name = st.selectbox("釣り場（地点）を選択", station_names)
st_code = next(s["code"] for s in TIDE_STATIONS if s["name"] == selected_name)

# 日時選択
col1, col2 = st.columns(2)
d_input = col1.date_input("日付", value=datetime.now())
t_input = col2.time_input("時刻", value=datetime.now().time())

if st.button("潮位を計算する"):
    target_dt = datetime.combine(d_input, t_input)
    
    with st.spinner('データを取得中...'):
        result = get_tide_status(target_dt, st_code)
    
    if isinstance(result, dict):
        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("算出潮位", f"{result['cm']} cm")
        c2.metric("潮位フェーズ", result['phase'])
        
        # 潮位の高さに応じたアドバイス（簡易版）
        if "上げ" in result['phase']:
            st.info("魚の活性が上がりやすい「上げ潮」のタイミングです！")
        elif "下げ" in result['phase']:
            st.success("ベイトが動き出す「下げ潮」のタイミングです！")
    else:
        st.error(result)

# ---------------------------------------------------------------------
# Disclaimer (AI規則に基づく表示)
st.sidebar.markdown("---")
st.sidebar.caption("AIとの会話は学習に使用したり外部に漏れたりしません。")
st.sidebar.caption("釣果情報は安全に管理され、他に共有されることはありません。")
