import pandas as pd
import requests
from datetime import timedelta
import streamlit as st

# AIとの会話は学習に使用したり外部に漏れたりしません。釣果情報も共有しません。

def get_tide_details(res_dummy, dt):
    """
    【完全デバッグモード】
    画面上に取得プロセスを表示し、2025年/2026年の両データ構造を解析します。
    """
    try:
        st.info(f"🔍 解析開始: {dt.strftime('%Y-%m-%d %H:%M')}")

        # 1. 地点コードの抽出
        station_code = "HS"  # デフォルト
        if isinstance(res_dummy, str) and "/data/" in res_dummy:
            # URL例: .../data/2026/HS.json -> HS を取得
            station_code = res_dummy.split('/')[-1].replace('.json', '')
        
        st.write(f"📍 判定地点コード: **{station_code}**")

        combined_events = []
        hourly_data = []
        
        # 前後3日分（前日・当日・翌日）をチェック
        target_days = [dt - timedelta(days=1), dt, dt + timedelta(days=1)]
        
        for d in target_days:
            year = d.year
            url = f"https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{year}/{station_code}.json"
            
            try:
                r = requests.get(url, timeout=10)
                if r.status_code != 200:
                    st.warning(f"⚠️ {year}年のデータ取得に失敗 (HTTP {r.status_code}): {url}")
                    continue
                
                raw_json = r.json()
                
                # --- 2025年(リスト直下)と2026年(dataキー)の構造判別 ---
                if isinstance(raw_json, dict) and 'data' in raw_json:
                    items = raw_json['data']
                    st.write(f"📂 {year}年: 2026年型(辞書)として解析中...")
                else:
                    items = raw_json
                    st.write(f"📂 {year}年: 2025年型(リスト)として解析中...")
                
                # 日付の正規化 (YYYYMMDD) で検索
                search_target = d.strftime("%Y%m%d")
                day_info = None
                for item in items:
                    # date: "2025-10-24" などの記号を除去
                    clean_date = str(item.get('date', '')).replace("-", "").replace(" ", "")
                    if clean_date == search_target:
                        day_info = item
                        break
                
                if day_info:
                    st.success(f"✅ {year}/{d.month}/{d.day} のデータ行を発見しました")
                    # イベント(干満)の抽出
                    for ev in day_info.get('events', []):
                        t_str = str(ev.get('time', '')).strip()
                        if ":" in t_str:
                            ev_dt = pd.to_datetime(f"{d.strftime('%Y-%m-%d')} {t_str}")
                            combined_events.append({"time": ev_dt, "type": ev.get('type', '').lower()})
                    
                    # 当日の潮位(hourly)の抽出
                    if d.date() == dt.date():
                        hourly_raw = day_info.get('hourly', [])
                        hourly_data = [int(v) for v in hourly_raw if str(v).strip().replace('-','').isdigit()]
                        st.write(f"📈 潮位データ(hourly)を {len(hourly_data)} 件読み込みました")
                else:
                    st.error(f"❌ {year}/{d.month}/{d.day} の日付がファイル内に見つかりません")

            except Exception as e:
                st.error(f"💥 {year}年の処理中にエラー: {e}")

        # 2. 潮位の計算 (1時間ごとのデータから線形補間)
        current_cm = 0
        if len(hourly_data) >= 24:
            h, mi = dt.hour, dt.minute
            t1 = hourly_data[h]
            t2 = hourly_data[(h+1)%24]
            current_cm = int(round(t1 + (t2 - t1) * (mi / 60.0)))
            st.metric("現在の計算潮位", f"{current_cm} cm")

        # 3. 10分割フェーズの判定
        events = sorted([dict(t) for t in {tuple(d.items()) for d in combined_events}], key=lambda x: x['time'])
        phase_str = "不明"
        prev_ev, next_ev = None, None

        for i in range(len(events)):
            if events[i]['time'] <= dt: prev_ev = events[i]
            if events[i]['time'] > dt:
                next_ev = events[i]
                break

        if prev_ev and next_ev:
            total_dur = (next_ev['time'] - prev_ev['time']).total_seconds() / 60
            elapsed = (dt - prev_ev['time']).total_seconds() / 60
            if total_dur > 0:
                ten_parts = min(max(int((elapsed / total_dur) * 10) + 1, 1), 10)
                label = "上げ" if "low" in prev_ev['type'] else "下げ"
                phase_str = f"{label}{ten_parts}分"
                st.write(f"🌊 フェーズ判定結果: **{phase_str}**")
        else:
            st.warning("⚠️ 前後の干満イベントが不足しているためフェーズを特定できません")

        return {
            "cm": current_cm, 
            "phase": phase_str, 
            "events": events, 
            "hourly": hourly_data
        }

    except Exception as e:
        st.error(f"💣 致命的なエラー: {e}")
        return {"cm": 0, "phase": "解析失敗", "events": [], "hourly": []}
