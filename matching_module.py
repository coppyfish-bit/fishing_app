import streamlit as st
import requests
from datetime import datetime

def get_jma_tide_hs():
    """
    気象庁HS地点(本渡)のテキストデータを解析。
    空白混じりの特殊フォーマットを完全デバッグ済み。
    """
    now = datetime.now()
    # 2026年最新URL
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/HS.txt"
    
    # 万が一の時のデフォルト値
    fail_res = (150, "取得失敗")
    
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200: return fail_res
        
        lines = res.text.splitlines()
        target_y = int(now.strftime('%y'))
        target_m = now.month
        target_d = now.day
        
        day_line = None
        for line in lines:
            if len(line) < 130: continue
            # 73-78カラムの日付を、空白を考慮して確実に取得
            try:
                # 気象庁特有の「0を空白にする」処理を strip() で回避
                l_y = int(line[72:74].strip())
                l_m = int(line[74:76].strip())
                l_d = int(line[76:78].strip())
                l_st = line[78:80].strip()
                
                if l_y == target_y and l_m == target_m and l_d == target_d and l_st == "HS":
                    day_line = line
                    break
            except: continue

        if not day_line: return fail_res

        # --- 毎時潮位の解析 (1-72カラム) ---
        hourly = []
        for i in range(24):
            val = day_line[i*3 : (i+1)*3].strip()
            # 潮位がマイナスの場合（-10cmなど）も考慮
            hourly.append(int(val) if val else 0)
        
        # 線形補間で現在時刻の潮位を算出
        h = now.hour
        m = now.minute
        t1 = hourly[h]
        t2 = hourly[h+1] if h < 23 else hourly[h]
        current_cm = int(t1 + (t2 - t1) * (m / 60.0))

        # --- 満干潮時刻の解析 (81-136カラム) ---
        events = []
        # 満潮(81-108), 干潮(109-136) 各4スロット
        for start, e_type in [(80, "満潮"), (108, "干潮")]:
            for i in range(4):
                pos = start + (i * 7)
                t_str = day_line[pos : pos+4].strip()
                if t_str and t_str != "9999":
                    # 時刻(HHMM)を datetime に変換
                    ev_t = datetime.strptime(now.strftime('%Y%m%d') + t_str.zfill(4), '%Y%m%d%H%M')
                    events.append({"time": ev_t, "type": e_type})
        
        events.sort(key=lambda x: x['time'])

        # --- フェーズ判定 ---
        phase = "判定中"
        prev = next((e for e in reversed(events) if e['time'] <= now), None)
        nxt = next((e for e in events if e['time'] > now), None)

        if prev and nxt:
            dur = (nxt['time'] - prev['time']).total_seconds()
            ela = (now - prev['time']).total_seconds()
            p_label = "上げ" if prev['type'] == "干潮" else "下げ"
            # 10分割して○分とする
            step = max(1, min(9, int((ela / dur) * 10)))
            phase = f"{p_label}{step}分"
            # 潮止まり付近のラベル調整
            if (ela/dur) < 0.1: phase = prev['type']
            elif (ela/dur) > 0.9: phase = nxt['type']

        return current_cm, phase

    except Exception as e:
        return 150, f"Error:{str(e)[:5]}"

def show_matching_page(df):
    """
    メイン画面への統合
    """
    st.title("🏹 SeaBass Match AI v7.2")
    
    # データを取得
    cm, phase = get_jma_tide_hs()
    
    # デバッグ表示（成功すればここが動く）
    if phase == "取得失敗":
        st.error("⚠️ 気象庁のデータが見つかりませんでした。手動で設定してください。")
    else:
        st.success(f"✅ 本渡瀬戸のデータを同期しました: {phase} ({cm}cm)")

    # ユーザー確認用
    st.info(f"現在の本渡瀬戸: 【{phase}】 {cm}cm")
