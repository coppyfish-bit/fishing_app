import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

def show_matching_page(df=None):
    st.title("🏹 SeaBass Matcher Pro")
    
    # --- 1. 日本時間の強制取得 (サーバー時刻のズレ防止) ---
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst).replace(tzinfo=None)
    
    st.info(f"🇯🇵 日本時刻で解析中: {now.strftime('%m/%d %H:%M')}")
    
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/HS.txt"

    try:
        res = requests.get(url, timeout=10)
        lines = res.text.splitlines()
        
        # --- 2. 現在潮位の分単位推測 (線形補間) ---
        target_y, target_m, target_d = int(now.strftime('%y')), now.month, now.day
        day_line = next((l for l in lines if len(l) > 80 and 
                         int(l[72:74]) == target_y and 
                         int(l[74:76]) == target_m and 
                         int(l[76:78]) == target_d and 
                         l[78:80].strip() == "HS"), None)

        current_tide_est = 0
        t1, t2 = 0, 0
        if day_line:
            hourly_tides = [int(day_line[i*3 : (i+1)*3].strip() or 0) for i in range(24)]
            h, m = now.hour, now.minute
            t1 = hourly_tides[h]
            t2 = hourly_tides[h+1] if h < 23 else hourly_tides[h]
            # 分単位の推測計算
            current_tide_est = int(t1 + (t2 - t1) * (m / 60.0))

        # --- 3. 3日間(昨日・今日・明日)の潮汐イベント抽出 ---
        events = []
        for d_offset in [-1, 0, 1]:
            t_date = now + timedelta(days=d_offset)
            ty, tm, td = int(t_date.strftime('%y')), t_date.month, t_date.day
            d_prefix = t_date.strftime('%Y%m%d')
            
            d_line = next((l for l in lines if len(l) > 80 and 
                           int(l[72:74]) == ty and int(l[74:76]) == tm and 
                           int(l[76:78]) == td and l[78:80].strip() == "HS"), None)
            
            if d_line:
                for start, e_type in [(80, "満潮"), (108, "干潮")]:
                    for i in range(4):
                        pos = start + (i * 7)
                        t_raw = d_line[pos : pos+4].strip()
                        if t_raw and t_raw != "9999" and t_raw.isdigit():
                            ev_t = datetime.strptime(d_prefix + t_raw, '%Y%m%d%H%M')
                            events.append({"time": ev_t, "type": e_type})
        
        # 重複を排除して時刻順にソート
        events = sorted([dict(t) for t in {tuple(d.items()) for d in events}], key=lambda x: x['time'])

        # --- 4. フェーズ判定ロジック ---
        prev_e = next((e for e in reversed(events) if e['time'] <= now), None)
        next_e = next((e for e in events if e['time'] > now), None)

        # 画面表示
        st.subheader("🕒 本渡瀬戸のリアルタイム海況")
        col1, col2 = st.columns(2)

        if day_line:
            with col1:
                st.metric("推測現在潮位", f"{current_tide_est} cm", delta=f"{t1} → {t2}")
                st.caption(f"現在の推移: {'下げ（下落中）' if t2 < t1 else '上げ（上昇中）'}")

        if prev_e and next_e:
            duration = (next_e['time'] - prev_e['time']).total_seconds()
            elapsed = (now - prev_e['time']).total_seconds()
            ratio = elapsed / duration
            progress = max(1, min(9, int(ratio * 10)))
            direction = "下げ" if prev_e['type'] == "満潮" else "上げ"
            
            # 潮止まり判定を5%に設定
            if ratio < 0.05: phase_label = f"{prev_e['type']}（止まり）"
            elif ratio > 0.95: phase_label = f"{next_e['type']}（止まり）"
            else: phase_label = f"{direction}{progress}分"

            with col2:
                st.metric("現在のフェーズ", phase_label)
                # 次の目標を表示
                display_next = next_e
                if ratio > 0.95: # 既に止まりに入っているならその次を出す
                    idx = events.index(next_e)
                    if idx + 1 < len(events): display_next = events[idx + 1]
                st.write(f"次は **{display_next['type']}** ({display_next['time'].strftime('%m/%d %H:%M')})")
            
            st.progress(ratio, text=f"潮汐進捗: {int(ratio*100)}%")

        # --- 5. 過去実績とのマッチングロジック (統合) ---
        st.divider()
        if df is not None and not df.empty:
            st.subheader("📍 推測条件に合う過去実績")
            
            # スコアリングロジック
            def calculate_match(row):
                score = 0
                try:
                    # 潮位が近い(±20cm)
                    if abs(row['潮位_cm'] - current_tide_est) <= 20: score += 50
                    # フェーズが一致
                    if str(row.get('潮位フェーズ')) == phase_label: score += 50
                except: pass
                return score

            df['マッチ度'] = df.apply(calculate_match, axis=1)
            ranking = df.sort_values('マッチ度', ascending=False).head(3)
            
            if ranking['マッチ度'].max() > 0:
                for i, row in ranking.iterrows():
                    with st.expander(f"マッチ度 {row['マッチ度']}% - {row['場所']}"):
                        st.write(f"📏 {row['魚種']} {row['全長_cm']}cm")
                        st.write(f"🎣 ルアー: {row['ルアー']}")
                        st.caption(f"実績時の潮位: {row['潮位_cm']}cm / フェーズ: {row['潮位フェーズ']}")
            else:
                st.write("現在の条件に近い過去実績はまだありません。")

    except Exception as e:
        st.error(f"解析エラー: {e}")

if __name__ == "__main__":
    show_matching_page()
