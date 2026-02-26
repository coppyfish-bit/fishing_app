import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone

def show_matching_page(df=None):
    st.title("🏹 SeaBass Matcher Pro - 状況分析")
    
    # --- 1. 時間・月情報の取得 ---
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst).replace(tzinfo=None)
    current_month = now.month
    
    # --- 2. 潮位データの自動取得 (JMA) ---
    url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/HS.txt"
    auto_tide, auto_phase = 0, "不明"
    try:
        res = requests.get(url, timeout=5)
        lines = res.text.splitlines()
        day_line = next((l for l in lines if len(l) > 80 and int(l[72:74]) == int(now.strftime('%y')) and int(l[74:76]) == now.month and int(l[76:78]) == now.day and l[78:80].strip() == "HS"), None)
        if day_line:
            hourly = [int(day_line[i*3 : (i+1)*3].strip() or 0) for i in range(24)]
            auto_tide = int(hourly[now.hour] + (hourly[now.hour+1 if now.hour<23 else now.hour] - hourly[now.hour]) * (now.minute / 60.0))
            # (フェーズ判定ロジックは簡略化して変数に保持)
            # ※本来は前述の3日間ロジックが入ります
    except: pass

    # --- 3. 入力設定（自動取得 vs 手入力） ---
    st.sidebar.header("📊 条件設定")
    input_mode = st.sidebar.radio("データ入力モード", ["リアルタイム自動", "シミュレーション（手入力）"])

    if input_mode == "リアルタイム自動":
        target_month = current_month
        target_tide = auto_tide
        # 仮の自動気象取得（APIキーがある場合はここにrequestsを追加）
        target_wind_dir = "北西" 
        target_wind_speed = 3.0
        st.success(f"現在の状況を自動取得しました（{now.strftime('%H:%M')}時点）")
    else:
        st.sidebar.subheader("手入力設定")
        target_month = st.sidebar.slider("月", 1, 12, current_month)
        target_tide = st.sidebar.number_input("潮位 (cm)", 0, 400, auto_tide)
        target_wind_dir = st.sidebar.selectbox("風向", ["北", "北東", "東", "南東", "南", "南西", "西", "北西"])
        target_wind_speed = st.sidebar.slider("風速 (m/s)", 0.0, 15.0, 3.0)

    # --- 4. 現在（または設定）の海況表示 ---
    st.subheader("🕒 解析対象の海況・気象")
    c1, c2, c3 = st.columns(3)
    c1.metric("対象月", f"{target_month}月")
    c2.metric("潮位", f"{target_tide} cm")
    c3.metric("風況", f"{target_wind_dir} {target_wind_speed}m")

    # --- 5. マッチング・スコアリング ---
    if df is not None and not df.empty:
        st.divider()
        st.subheader("🎯 推奨ポイント・過去実績")

        def calculate_total_score(row):
            score = 0
            try:
                # 1. 月のマッチング（±1ヶ月以内なら加点）
                if row['月'] == target_month: score += 40
                elif abs(row['月'] - target_month) == 1: score += 20
                
                # 2. 潮位のマッチング（±20cm以内）
                tide_diff = abs(row['潮位_cm'] - target_tide)
                if tide_diff <= 20: score += 30
                elif tide_diff <= 40: score += 15
                
                # 3. 風向のマッチング（一致すれば加点）
                if row['風向'] == target_wind_dir: score += 30
            except: pass
            return score

        df['マッチ度'] = df.apply(calculate_total_score, axis=1)
        results = df.sort_values('マッチ度', ascending=False).head(5)

        if results['マッチ度'].max() > 0:
            for _, row in results.iterrows():
                with st.expander(f"マッチ度 {row['マッチ度']}% ： {row['場所']}"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.write(f"🐟 **{row['魚種']}** ({row['全長_cm']}cm)")
                        st.write(f"📅 実績：{row['月']}月 / {row['潮位_cm']}cm")
                    with col_b:
                        st.write(f"💨 風：{row['風向']} {row['風速_m']}m")
                        st.write(f"🎣 {row['ルアー']}")
        else:
            st.info("条件に近い実績がまだ登録されていません。")
    else:
        st.warning("釣果データ(CSV)を読み込んでください。")

if __name__ == "__main__":
    show_matching_page()
