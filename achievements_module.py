import streamlit as st
import pandas as pd
import numpy as np

def show_achievements_page(df):
    st.title("🏆 HUNTER RANK & MISSIONS")
    st.caption("釣果データから自動的に実績を解除します。")

    if df is None or df.empty:
        st.info("データがありません。まずは釣果を記録しましょう。")
        return

    # 前処理
    df_calc = df.copy()
    df_calc['datetime_parsed'] = pd.to_datetime(df_calc['datetime'], errors='coerce')
    df_calc = df_calc.dropna(subset=['datetime_parsed'])
    df_calc['date_only'] = df_calc['datetime_parsed'].dt.date

    # 釣り人の選択
    user_col = '釣り人' if '釣り人' in df_calc.columns else '場所'
    user_list = sorted(df_calc[user_col].unique()) 
    selected_user = st.selectbox("👤 チャレンジャーを選択", user_list)
    df_user = df_calc[df_calc[user_col] == selected_user]

    # --- 実績ロジック ---
    missions = [
        {"id": "suz_100", "name": "伝説の化身", "desc": "スズキ 100cmオーバー捕獲", "icon": "🌌", "cond": lambda d: any((d['魚種'].str.contains("スズキ|シーバス")) & (d['全長_cm'] >= 100))},
        {"id": "suz_90", "name": "神域の鱸", "desc": "スズキ 90cmオーバー捕獲", "icon": "🔱", "cond": lambda d: any((d['魚種'].str.contains("スズキ|シーバス")) & (d['全長_cm'] >= 90))},
        {"id": "red_70", "name": "真紅の重戦車", "desc": "真鯛 70cmオーバー捕獲", "icon": "🚩", "cond": lambda d: any((d['魚種'].str.contains("タイ|マダイ")) & (d['全長_cm'] >= 70))},
        {"id": "tsunuke", "name": "ツ抜け達成", "desc": "1日で同じ魚種を10匹以上登録", "icon": "🔢", "cond": lambda d: any(d.groupby(['date_only', '魚種']).size() >= 10)},
        {"id": "tide_master", "name": "潮の支配者", "desc": "上げ・下げ・満・干全ての潮汐で釣果", "icon": "🌀", "cond": lambda d: all(any(d['潮位フェーズ'].str.contains(p, na=False)) for p in ["上げ", "下げ", "満潮", "干潮"])},
        {"id": "all_weather", "name": "全天候型釣り師", "desc": "晴れ・曇り・雨全ての天候で釣果", "icon": "🌈", "cond": lambda d: all(any(d['天気'].str.contains(w, na=False)) for w in ["晴", "曇", "雨"])},
        {"id": "lure_variety", "name": "ルアー・コレクター", "desc": "5種類以上の異なる名称のルアーで釣果", "icon": "🎨", "cond": lambda d: d['ルアー'].nunique() >= 5},
    ]

    shames = [
        {"id": "barashi_king", "name": "バラシの帝王", "desc": "魚種に『バラシ』が5回以上", "icon": "💸", "cond": lambda d: d['魚種'].str.contains("バラシ", na=False).sum() >= 5},
        {"id": "uma", "name": "UMA目撃者", "desc": "バラシの備考に『デカすぎ』等と記載", "icon": "🐉", "cond": lambda d: d[d['魚種'].str.contains("バラシ", na=False)]['備考'].str.contains("デカすぎ|動かない|怪物", na=False).any()},
        {"id": "eso_curse", "name": "エソの呪い", "desc": "エソを通算5匹以上登録", "icon": "🐍", "cond": lambda d: d['魚種'].str.contains("エソ", na=False).sum() >= 5},
        {"id": "lost_saint", "name": "ルアー殉職", "desc": "備考に『ロスト』等が5回以上", "icon": "🕯️", "cond": lambda d: d['備考'].str.contains("ロスト|殉職|奉納", na=False).sum() >= 5},
        {"id": "micro", "name": "針がデカすぎた", "desc": "5cm以下の魚を登録", "icon": "🤏", "cond": lambda d: any((d['全長_cm'] > 0) & (d['全長_cm'] <= 5))},
        {"id": "sanpo", "name": "ただの散歩", "desc": "備考に『異常なし』が3回以上", "icon": "🚶", "cond": lambda d: d['備考'].str.contains("異常なし|異常無し|ホゲ", na=False).sum() >= 3},
    ]

    # 判定・表示
    unlocked_m = [m for m in missions if m["cond"](df_user)]
    unlocked_s = [s for s in shames if s["cond"](df_user)]
    percent = int((len(unlocked_m) / len(missions)) * 100)
    
    # ランク判定
    rank, color = ("NOVICE", "#888")
    if percent >= 100: rank, color = ("ANGLER GOD", "#fff")
    elif percent >= 70: rank, color = ("LEGEND", "#ff4b4b")
    elif percent >= 40: rank, color = ("GOLD", "#ffca00")
    elif percent >= 20: rank, color = ("SILVER", "#c0c0c0")

    # ヘッダーUI
    st.markdown(f"""
        <div style="background: #0e1117; border: 3px solid {color}; padding: 25px; border-radius: 20px; text-align: center; box-shadow: 0 0 20px {color}33;">
            <h3 style="margin: 0; color: {color}; letter-spacing: 5px;">RANK: {rank}</h3>
            <div style="font-size: 4rem; font-weight: 900; margin: 5px 0; color: #fff;">{percent}%</div>
            <div style="background: rgba(255,255,255,0.05); border-radius: 10px; height: 15px; width: 100%;">
                <div style="background: linear-gradient(90deg, {color}, #fff); width: {percent}%; height: 100%; border-radius: 10px;"></div>
            </div>
            <p style="margin-top: 10px; color: #888;">{selected_user} の戦績 | 正:{len(unlocked_m)} 逆:{len(unlocked_s)}</p>
        </div>
    """, unsafe_allow_html=True)

    # 実績グリッド
    st.write("### ✨ GLORIOUS MISSIONS")
    cols = st.columns(2)
    for i, m in enumerate(missions):
        with cols[i % 2]:
            show_card(m, m["id"] in [x["id"] for x in unlocked_m], color)

    st.write("### 💀 HALL OF SHAME")
    cols_s = st.columns(2)
    for i, s in enumerate(shames):
        with cols_s[i % 2]:
            show_card(s, s["id"] in [x["id"] for x in unlocked_s], "#ff4b4b" if s["id"] in [x["id"] for x in unlocked_s] else "#444", is_shame=True)

def show_card(ach, is_met, color, is_shame=False):
    opacity = "1.0" if is_met else "0.2"
    bg = "rgba(0, 255, 208, 0.1)" if is_met and not is_shame else "rgba(255, 75, 75, 0.1)" if is_met and is_shame else "#161b22"
    st.markdown(f"""
        <div style="border: 1px solid {color}; background: {bg}; padding: 12px; border-radius: 10px; margin-bottom: 8px; opacity: {opacity}; height: 75px; display: flex; align-items: center; gap: 10px;">
            <div style="font-size: 1.8rem;">{ach['icon']}</div>
            <div style="line-height: 1.2;">
                <div style="font-weight: bold; color: #fff; font-size: 0.9rem;">{ach['name']}</div>
                <div style="font-size: 0.7rem; color: #888;">{ach['desc']}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)