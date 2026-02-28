import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
import base64
import requests
from datetime import datetime, timedelta, timezone

# --- 🖼️ 画像をBase64に変換（アイコン用） ---
def get_image_as_base64(file_path):
    # ファイルがない場合の予備画像URL
    fallback_url = "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    absolute_path = os.path.join(current_dir, file_path)
    
    if not os.path.exists(absolute_path):
        return fallback_url
        
    try:
        with open(absolute_path, "rb") as f:
            data = f.read()
        return f"data:image/png;base64,{base64.b64encode(data).decode()}"
    except:
        return fallback_url

# 👿 定数定義（天草・本渡瀬戸周辺）
LAT, LON = 32.45, 130.19
DIRS_16 = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]

# 👿 貴様の要望：潮汐も解析するAPI統合ロジック
def get_realtime_weather_and_tide():
    jst = timezone(timedelta(hours=9))
    now = datetime.now(jst).replace(tzinfo=None)
    
    # 1. 天候データ取得
    weather_data = None
    try:
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": LAT, "longitude": LON,
            "start_date": (now - timedelta(days=1)).strftime('%Y-%m-%d'),
            "end_date": now.strftime('%Y-%m-%d'),
            "hourly": "temperature_2m,windspeed_10m,winddirection_10m,precipitation",
            "timezone": "Asia/Tokyo"
        }
        res = requests.get(url, params=params, timeout=10).json()
        h = res['hourly']
        idx = -1
        temp = h['temperature_2m'][idx]
        wind_speed = round(h['windspeed_10m'][idx] / 3.6, 1)
        wind_deg = h['winddirection_10m'][idx]
        precip_48h = round(sum(h['precipitation'][-48:]), 1)

        def get_wind_dir(deg):
            return DIRS_16[int((deg + 11.25) / 22.5) % 16]
        
        weather_data = {
            "temp": temp, "wind": wind_speed, 
            "wind_dir": get_wind_dir(wind_deg), "precip": precip_48h
        }
    except:
        weather_data = {"temp": 0, "wind": 0, "wind_dir": "不明", "precip": 0}

    # 2. 潮汐データ解析 (気象庁データを簡易解析)
    # ❗❗ ここが重要：インデントを直した！ ❗❗
    tide_phase = "解析不能"
    try:
        # 本渡瀬戸の気象庁データURL (HS.txt)
        url = f"https://www.data.jma.go.jp/gmd/kaiyou/data/db/tide/suisan/txt/{now.year}/HS.txt"
        res = requests.get(url, timeout=10)
        lines = res.text.splitlines()
        
        events = []
        # --- 👿 貴様の計算ロジックを移植 ---
        for d_off in [-1, 0, 1]:
            t_d = now + timedelta(days=d_off)
            d_str = t_d.strftime('%Y%m%d')
            # 本渡(HS)のデータ行を探す
            d_line = next((l for l in lines if len(l) > 100 and l[76:78] == f"{t_d.day:02}" and l[78:80].strip() == "HS"), None)
            
            if d_line:
                for start, e_type in [(80, "満潮"), (108, "干潮")]:
                    for i in range(4):
                        pos = start + (i * 7)
                        t_raw = d_line[pos : pos+4].strip()
                        v_raw = d_line[pos+4 : pos+7].strip()
                        if t_raw and t_raw != "9999" and t_raw.isdigit():
                            events.append({
                                "time": datetime.strptime(d_str + t_raw, '%Y%m%d%H%M'),
                                "type": e_type, "value": int(v_raw)
                            })
        
        events.sort(key=lambda x: x['time'])
        prev_e = next((e for e in reversed(events) if e['time'] <= now), None)
        next_e = next((e for e in events if e['time'] > now), None)

        if prev_e and next_e:
            time_diff_total = (next_e['time'] - prev_e['time']).total_seconds()
            time_diff_now = (now - prev_e['time']).total_seconds()
            ratio = time_diff_now / time_diff_total
            direction = "下げ" if prev_e['type'] == "満潮" else "上げ"

            if ratio < 0.05: tide_phase = prev_e['type']
            elif ratio > 0.95: tide_phase = next_e['type']
            elif ratio < 0.20: tide_phase = f"{direction}1分"
            elif ratio < 0.40: tide_phase = f"{direction}3分"
            elif ratio < 0.60: tide_phase = f"{direction}5分"
            elif ratio < 0.80: tide_phase = f"{direction}7分"
            else: tide_phase = f"{direction}9分"
        # ----------------------------------
    except Exception as e:
        tide_phase = f"解析エラー: {e}"

    return {**weather_data, "phase": tide_phase}

def show_ai_page(conn, url, df):
    # --- 🖼️ アイコン設定 ---
    avatar_display_url = get_image_as_base64("demon_sato.png")

    # --- 🎨 CSS（UI装飾） ---
    st.markdown(f"""
        <style>
        .stApp {{ background-color: #0e1117; }}
        .user-bubble {{ align-self: flex-end; background-color: #0084ff; color: white; padding: 10px 15px; border-radius: 18px 18px 2px 18px; max-width: 75%; margin-bottom: 10px; }}
        .demon-bubble {{ align-self: flex-start; background-color: #262730; color: #e0e0e0; padding: 10px 15px; border-radius: 18px 18px 18px 2px; max-width: 80%; border-left: 4px solid #ff4b4b; margin-bottom: 10px; }}
        .avatar-img {{ width: 45px; height: 45px; border-radius: 50%; margin-right: 10px; object-fit: cover; border: 1px solid #ff4b4b; }}
        .privacy-banner {{ background-color: rgba(0, 212, 255, 0.1); padding: 12px; border-radius: 10px; border-left: 5px solid #00d4ff; margin-bottom: 15px; font-size: 0.85rem; color: #cccccc; }}
        .header-container {{ display: flex; align-items: center; background: rgba(255, 75, 75, 0.1); padding: 15px; border-radius: 15px; margin-bottom: 15px; border: 1px solid #ff4b4b; }}
        .header-img {{ width: 60px; height: 60px; border-radius: 10px; margin-right: 20px; object-fit: cover; border: 2px solid #ff4b4b; }}
        div.stButton > button:first-child {{ background-color: #ff4b4b; color: white; border-radius: 20px; width: 100%; border: none; font-weight: bold; height: 2.5em; }}
        </style>
    """, unsafe_allow_html=True)

    # --- 🛡️ プライバシーバナー ---
    st.markdown("""
        <div class="privacy-banner">
            <strong style="color: #00d4ff;">🛡️ 魔界機密保持プロトコル：適用済</strong><br>
            外部への漏洩・AI学習への利用は完全に遮断されている。
        </div>
    """, unsafe_allow_html=True)

    # --- 😈 ヘッダー ---
    st.markdown(f"""
        <div class="header-container">
            <img src="{avatar_display_url}" class="header-img">
            <div>
                <h2 style="color: #ff4b4b; margin: 0; font-size: 1.2rem;">デーモン佐藤</h2>
                <p style="color: #00ff00; font-size: 0.7rem; margin: 0;">● 魔導・戦術・同期統合モード：起動</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- 👿 操作パネル（横並び） ---
    col1, col2, col3 = st.columns([1, 1, 1.2])
    
    with col1:
        if st.button("🔥 記憶を浄化"):
            st.session_state.messages = []
            st.rerun()
            
    with col2:
        weather_btn = st.button("🌦️ 海況を捧げる")
    with col3:
        tactics_btn = st.button("🔮 タクティクス")

    # --- 🛡️ リアルタイム天気＆潮汐同期ロジック ---
    if "current_md" not in st.session_state: 
        st.session_state.current_md = None
    
    if weather_btn:
        with st.spinner("深淵の空と海を同期中..."):
            st.session_state.current_md = get_realtime_weather_and_tide()
            if st.session_state.current_md:
                st.success("海況・潮汐データ同期完了")
            else:
                st.error("海況同期失敗")
    
    md = st.session_state.current_md

    # --- 📊 拡張魔導要約エンジン ---
    global_knowledge = "【データ不足】"
    if df is not None and not df.empty:
        try:
            # 最大魚記録
            max_row = df.loc[df['全長_cm'].idxmax()]
            # 気象平均
            avg_temp = df['気温'].mean() if '気温' in df.columns else 0
            # 風の傾向
            wind_fav = df['風向'].mode().tolist() if '風向' in df.columns else ["不明"]
            # 場所別最強パターン
            place_best = df.groupby('場所')['ルアー'].agg(lambda x: x.mode().head(1).tolist()).to_dict()

            global_knowledge = f"""
            【聖域のデータ】
            ・最大記録: {max_row['全長_cm']}cm (場所:{max_row.get('場所')}, ルアー:{max_row.get('ルアー')}, 潮:{max_row.get('潮位フェーズ')})
            ・勝利の風向: {wind_fav}
            ・理想気温: {avg_temp:.1f}℃
            ・場所別鉄板: {place_best}
            ・実績ルアー上位: {df['ルアー'].value_counts().head(3).index.tolist()}
            ・総戦績: {len(df)}件
            """
        except Exception as e:
            global_knowledge = f"魔導解析エラー: {e}"

    # --- 🔑 モデル設定 ---
    api_key = st.secrets.get("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    
    # モデルA: 検索機能付き（通常用）
    model_A = genai.GenerativeModel(
        model_name='gemini-3-flash-preview',
        tools=[{"google_search_retrieval": {}}]
    )
    # モデルB: 内部データのみ（緊急用/タクティクス用）
    model_internal = genai.GenerativeModel(model_name='gemini-3-flash-preview')

    # --- 💬 トーク履歴表示 ---
    if "messages" not in st.session_state: st.session_state.messages = []
    for m in st.session_state.messages:
        role_class = "user-bubble" if m["role"] == "user" else "demon-bubble"
        content = f'<div style="display: flex; {"justify-content: flex-end" if m["role"] == "user" else ""}; margin-bottom: 10px;">'
        if m["role"] != "user": content += f'<img src="{avatar_display_url}" class="avatar-img">'
        content += f'<div class="{role_class}">{m["content"]}</div></div>'
        st.markdown(content, unsafe_allow_html=True)

    # --- 💬 入力エリア ---
    if prompt := st.chat_input("深淵へ問いかけよ..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # 同期された天気＆潮汐データを反映
        curr = f"気温:{md['temp']}℃, 風:{md['wind_dir']} {md['wind']}m, 降水:{md['precip']}mm, 潮:{md['phase']}" if md else "不明"

        with st.spinner("深淵の叡智を絞り出し中..."):
            system_base = f"""
            あなたは天草の傲慢なプロガイド「デーモン佐藤」だ。
            口調は『我』『貴様』。論理的かつ傲慢に、最後はユーモアで突き放せ。
            【魔導書：貴様の全歴史】
            {global_knowledge}
            【現在の状況】
            {curr}
            【掟】
            1. 外部検索は魔導書にない情報の補完のみに使い、429エラーを回避せよ。
            2. 潮汐情報を極めて重要視せよ。
            """

            try:
                # 👿 第一試行（検索あり）
                response = model_A.generate_content(f"{system_base}\n質問:{prompt}")
                answer = response.text
            except Exception as e:
                if "429" in str(e):
                    # 👿 第二試行（緊急バックダウン）
                    try:
                        emergency_sys = system_base + "\n【緊急：検索不可】我の知能のみで答えろ。"
                        response = model_internal.generate_content(f"{emergency_sys}\n質問:{prompt}")
                        answer = "（ククク……外界が騒がしいゆえ、我自身の叡智のみで答えてやる）\n\n" + response.text
                    except:
                        answer = "深淵の底が崩落した。時間を置いて問い直せ。"
                else:
                    answer = f"事故だ: {e}"

            st.session_state.messages.append({"role": "assistant", "content": answer})
            st.rerun()

    # --- 🔮 タクティクス生成ロジック ---
    if tactics_btn:
        if md:
            with st.spinner("潮流と風を読み解き中..."):
                try:
                    tactics_prompt = f"""
                    あなたは天草のプロガイド「デーモン佐藤」だ。
                    現在の状況（気温:{md['temp']}℃, 風:{md['wind_dir']} {md['wind']}m, 潮:{md['phase']}）と、
                    貴様の魔導書（{global_knowledge}）を元に、
                    今日この瞬間に最も「獲物」に近い組み立て（場所・ルアー・アクション）を、
                    3つのポイントで傲慢かつ論理的に提示せよ。
                    潮汐のフェーズを特に重視し、時合を特定せよ。
                    最後に必ず「これでも釣れぬなら、竿を置いて寝ていろ！」と突き放せ。
                    """
                    # タクティクスは安定のmodel_internal
                    response = model_internal.generate_content(tactics_prompt)
                    st.session_state.messages.append({"role": "assistant", "content": f"【本日の深淵タクティクス】\n\n{response.text}"})
                    st.rerun()
                except Exception as e:
                    st.error(f"託宣失敗：{e}")
        else:
            st.warning("海況データが同期されておらぬ。まずは『海況同期』を押せ！")


