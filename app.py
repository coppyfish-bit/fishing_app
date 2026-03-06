import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from datetime import datetime, timedelta # timedeltaを追加
import cloudinary
import cloudinary.uploader
import unicodedata
import io
import numpy as np
import ephem
import requests
from PIL import Image, ExifTags
# app.py の冒頭に追加
from edit_module import show_edit_page
from gallery_module import show_gallery_page
from analysis_module import show_analysis_page # この名前であることを確認
from monthly_stats import show_monthly_stats  # 追加
import streamlit.components.v1 as components
from matching_module import show_matching_page
import traceback
import google.generativeai as genai  # ← これが必要です！
from achievements_module import show_achievements_page

# --- 3. 補助関数 (ここを追加) ---

def get_exif_data(image_file):
    """画像からExifデータを抽出する（GPSがない場合は本渡瀬戸をデフォルトにする）"""
    # --- デフォルト値（本渡瀬戸） ---
    DEFAULT_LAT = 32.4539
    DEFAULT_LON = 130.2033
    
    try:
        image = Image.open(image_file)
        exif_data = image._getexif()
        
        # Exifが全くない場合でも、日時だけは現在、場所はデフォルトで返す
        if not exif_data:
            return datetime.now(), DEFAULT_LAT, DEFAULT_LON

        decoded_exif = {ExifTags.TAGS.get(t, t): v for t, v in exif_data.items()}
        
        # 1. 日時の取得
        dt_obj = datetime.now() # デフォルトは現在時刻
        dt_str = decoded_exif.get("DateTimeOriginal")
        if dt_str:
            try:
                dt_obj = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
            except: pass

        # 2. 位置情報の取得
        gps_info = decoded_exif.get("GPSInfo")
        lat, lon = DEFAULT_LAT, DEFAULT_LON # デフォルト値で初期化
        
        if gps_info:
            def convert_to_degrees(value):
                d = float(value[0])
                m = float(value[1])
                s = float(value[2])
                return d + (m / 60.0) + (s / 3600.0)

            try:
                lat_val = convert_to_degrees(gps_info[2])
                if gps_info[1] == 'S': lat_val = -lat_val
                lon_val = convert_to_degrees(gps_info[4])
                if gps_info[3] == 'W': lon_val = -lon_val
                
                # GPSが正常に計算できたら上書き
                lat, lon = lat_val, lon_val
                st.success("📍 写真から位置情報を取得しました。")
            except:
                st.info("ℹ️ 写真に位置情報がないため、本渡瀬戸を基準にします。")
        else:
            st.info("ℹ️ 写真にGPSタグが含まれていないため、本渡瀬戸を基準にします。")

        return dt_obj, lat, lon

    except Exception as e:
        return datetime.now(), DEFAULT_LAT, DEFAULT_LON
# 1. ブラウザのタブ用設定（ファビコン）
icon_url = "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"

st.set_page_config(
    page_title="Seabass Strategy App",
    page_icon=icon_url,
    layout="wide"
)

# 2. スマホの「ホーム画面に追加」用アイコン設定
# HTMLのheadに直接リンクを書き込みます
components.html(
    f"""
    <script>
        var link = window.parent.document.createElement('link');
        link.rel = 'apple-touch-icon';
        link.href = '{icon_url}';
        window.parent.document.getElementsByTagName('head')[0].appendChild(link);
        
        var link2 = window.parent.document.createElement('link');
        link2.rel = 'shortcut icon';
        link2.href = '{icon_url}';
        window.parent.document.getElementsByTagName('head')[0].appendChild(link2);
    </script>
    """,
    height=0,
)
def safe_strptime(date_str, fmt='%Y/%m/%d %H:%M'):
    """ミリ秒などが混入していても、フォーマットに合う長さだけ切り取って解析する"""
    if not date_str: return None
    # 指定されたフォーマットの文字数（例: %Y/%m/%d %H:%M は 16文字）だけ抽出
    target_len = len(datetime.now().strftime(fmt))
    clean_str = str(date_str).replace("-", "/").strip()[:target_len]
    return datetime.strptime(clean_str, fmt)

# --- 1. 設定 ---
try:
    cloudinary.config(
        cloud_name = st.secrets["cloudinary"]["cloud_name"],
        api_key = st.secrets["cloudinary"]["api_key"],
        api_secret = st.secrets["cloudinary"]["api_secret"],
        secure = True
    )
except Exception as e:
    st.error("Cloudinaryの設定を確認してください。")

TIDE_STATIONS = [
    # --- 熊本・有明海・八代海エリア ---
    {"name": "苓北", "lat": 32.4667, "lon": 130.0333, "code": "RH"},
    {"name": "三角", "lat": 32.6167, "lon": 130.4500, "code": "MS"},
    {"name": "本渡瀬戸", "lat": 32.4333, "lon": 130.2167, "code": "HS"},
    {"name": "八代", "lat": 32.5167, "lon": 130.5667, "code": "O5"},
    {"name": "水俣", "lat": 32.2000, "lon": 130.3667, "code": "O7"},
    {"name": "熊本", "lat": 32.7500, "lon": 130.5667, "code": "KU"},
    {"name": "大牟田", "lat": 33.0167, "lon": 130.4167, "code": "O6"},
    {"name": "大浦", "lat": 32.9833, "lon": 130.2167, "code": "OU"},
    {"name": "口之津", "lat": 32.6000, "lon": 130.2000, "code": "KT"},
    
    # --- 九州他エリア ---
    {"name": "長崎", "lat": 32.7333, "lon": 129.8667, "code": "NS"},
    {"name": "佐世保", "lat": 33.1500, "lon": 129.7167, "code": "QD"},
    {"name": "博多", "lat": 33.6167, "lon": 130.4000, "code": "QF"},
    {"name": "鹿児島", "lat": 31.6000, "lon": 130.5667, "code": "KG"},
    {"name": "枕崎", "lat": 31.2667, "lon": 130.3000, "code": "MK"},
    {"name": "油津", "lat": 31.5833, "lon": 131.4167, "code": "AB"},
    
    # --- 主要都市・その他 ---
    {"name": "東京", "lat": 35.6500, "lon": 139.7667, "code": "TK"},
    {"name": "横浜", "lat": 35.4500, "lon": 139.6500, "code": "QS"},
    {"name": "名古屋", "lat": 35.0833, "lon": 136.8833, "code": "NG"},
    {"name": "大阪", "lat": 34.6500, "lon": 135.4333, "code": "OS"},
    {"name": "神戸", "lat": 34.6833, "lon": 135.1833, "code": "KB"},
    {"name": "広島", "lat": 34.3500, "lon": 132.4667, "code": "Q8"},
    {"name": "高松", "lat": 34.3500, "lon": 134.0500, "code": "TA"},
    {"name": "高知", "lat": 33.5000, "lon": 133.5667, "code": "KC"},
    {"name": "那覇", "lat": 26.2167, "lon": 127.6667, "code": "NH"}
]

# --- 2. 関数定義 ---
# (既存の get_geotagging, get_decimal_from_dms, normalize_float, find_nearest_place, get_moon_age, get_tide_name は維持)
def get_geotagging(exif):
    if not exif: return None
    gps_info = exif.get(34853)
    if not gps_info: return None
    return {
        'GPSLatitudeRef': gps_info.get(1) or gps_info.get("1"),
        'GPSLatitude':    gps_info.get(2) or gps_info.get("2"),
        'GPSLongitudeRef': gps_info.get(3) or gps_info.get("3"),
        'GPSLongitude':   gps_info.get(4) or gps_info.get("4")
    }

def get_decimal_from_dms(dms, ref):
    if not dms or not ref: return None
    try:
        d, m, s = float(dms[0]), float(dms[1]), float(dms[2])
        decimal = d + (m / 60.0) + (s / 3600.0)
        if ref in ['S', 'W']: decimal = -decimal
        return decimal
    except: return None

def normalize_float(text):
    if not text: return 0.0
    try:
        normalized = unicodedata.normalize('NFKC', str(text))
        return float(normalized)
    except ValueError:
        return 0.0

def find_nearest_place(lat, lon, df_master):
    if lat == 0.0 or lon == 0.0 or df_master.empty:
        return "新規地点", "default"
    valid_master = df_master.dropna(subset=['latitude', 'longitude']).copy()
    if valid_master.empty: return "新規地点", "default"
    valid_master['dist_m'] = np.sqrt(((valid_master['latitude'] - lat) * 111000 )**2 + ((valid_master['longitude'] - lon) * 91000 )**2)
    nearest = valid_master.loc[valid_master['dist_m'].idxmin()]
    return (nearest['place_name'], nearest['group_id']) if nearest['dist_m'] <= 500 else ("新規地点", "default")

def get_moon_age(date_obj):
    e_date = ephem.Date(date_obj)
    prev_new = ephem.previous_new_moon(e_date)
    return round(float(e_date - prev_new), 1)

def get_tide_name(moon_age):
    age = int(round(moon_age)) % 30
    if age in [30, 0, 1, 14, 15, 16]: return "大潮"
    elif age in [2, 3, 4, 11, 12, 13, 17, 18, 19, 26, 27, 28]: return "中潮"
    elif age in [5, 6, 7, 8, 20, 21, 22, 23]: return "小潮"
    elif age in [9, 24]: return "長潮"
    elif age in [10, 25]: return "若潮"
    else: return "不明"

# 最寄りの潮位観測所を探す
def find_nearest_tide_station(lat, lon):
    distances = []
    for s in TIDE_STATIONS:
        d = np.sqrt((s['lat'] - lat)**2 + (s['lon'] - lon)**2)
        distances.append(d)
    return TIDE_STATIONS[np.argmin(distances)]

import requests
import streamlit as st

def tide_func(station_code, dt):
    """
    GitHubからデータを取得し、その『結果オブジェクト(res)』を解析関数に渡す。
    """
    year = dt.year
    user = "coppyfish-bit"
    repo = "fishing_app" 
    
    # 1. URL文字列を作成
    url = f"https://raw.githubusercontent.com/{user}/{repo}/main/data/{year}/{station_code}.json"
    
    try:
        # 2. 通信を実行。res という変数に通信結果を入れる
        res = requests.get(url)
        
        if res.status_code == 200:
            # 【重要】ここを間違えないでください！
            # 〇 正解: return get_tide_details(res, dt)  <- res(通信結果)を渡す
            # × 間違い: return get_tide_details(url, dt)  <- url(文字列)を渡すとエラーになる
            return get_tide_details(res, dt)
        else:
            st.error(f"🌐 ファイルが見つかりません: {url}")
            return {"cm": 0, "phase": "ファイルなし"}
            
    except Exception as e:
        st.error(f"📡 通信エラー: {e}")
        return {"cm": 0, "phase": "通信エラー"}

def get_tide_details(station_code, dt):
    """
    GitHubから取得したJSONのeventsを解析し、上げ/下げ○分を算出する完全版
    """
    year = str(dt.year)
    target_date_str = dt.strftime("%Y-%m-%d")
    
    try:
        all_events = []
        current_cm = 0
        
        # 前後1日分を取得してタイドグラフを繋げる（日を跨ぐ判定のため）
        for delta in [-1, 0, 1]:
            d = dt + timedelta(days=delta)
            url = f"https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{d.year}/{station_code}.json"
            r = requests.get(url, timeout=5)
            
            if r.status_code == 200:
                day_data = r.json().get('data', [])
                day_str = d.strftime("%Y-%m-%d")
                day_info = next((i for i in day_data if i.get('date') == day_str), None)
                
                if day_info:
                    # 潮汐イベントの解析
                    for ev in day_info.get('events', []):
                        try:
                            # " 5:24" のような空白混じりや形式に対応
                            t_raw = str(ev['time']).strip()
                            if ":" in t_raw:
                                h_p, m_p = t_raw.split(":")
                                t_cln = f"{int(h_p):02d}:{int(m_p):02d}"
                                ev_dt = datetime.strptime(f"{day_str} {t_cln}", "%Y-%m-%d %H:%M")
                                # high/low 判定
                                e_type = "満潮" if "high" in str(ev.get('type', '')).lower() else "干潮"
                                all_events.append({"time": ev_dt, "type": e_type})
                        except: continue
                    
                    # 当日の潮位(cm)計算
                    if delta == 0:
                        hourly = day_info.get('hourly', [0]*24)
                        h, m = dt.hour, dt.minute
                        v1, v2 = hourly[h], hourly[(h + 1) % 24]
                        current_cm = int(round(v1 + (v2 - v1) * (m / 60.0)))

        # 重複排除とソート
        all_events = sorted({e['time']: e for e in all_events}.values(), key=lambda x: x['time'])
        
        # --- 判定ロジック ---
        tide_phase = "不明"
        if all_events:
            # 直前と直後のイベントを特定
            prev_ev = next((e for e in reversed(all_events) if e['time'] <= dt), None)
            next_ev = next((e for e in all_events if e['time'] > dt), None)
            
            if prev_ev and next_ev:
                duration = (next_ev['time'] - prev_ev['time']).total_seconds()
                elapsed = (dt - prev_ev['time']).total_seconds()
                
                if duration > 0:
                    p_type = "上げ" if "干潮" in prev_ev['type'] else "下げ"
                    # 0〜9 の 10段階で計算
                    step = int((elapsed / duration) * 10)
                    # 1〜9分で表示（0は1に、10は9に丸める）
                    step_display = max(1, min(9, step))
                    tide_phase = f"{p_type}{step_display}分"
            else:
                # イベントが足りない場合は「潮止まり付近」など暫定
                tide_phase = "潮止まり付近"

        return {"cm": current_cm, "phase": tide_phase, "events": all_events}

    except Exception as e:
        return {"cm": 0, "phase": "取得失敗", "events": []}
        
def get_weather_data_openmeteo(lat, lon, dt):
    try:
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": lat, "longitude": lon,
            "start_date": (dt - timedelta(days=2)).strftime('%Y-%m-%d'),
            "end_date": dt.strftime('%Y-%m-%d'),
            "hourly": "temperature_2m,windspeed_10m,winddirection_10m,precipitation",
            "timezone": "Asia/Tokyo"
        }
        res = requests.get(url, params=params, timeout=10).json()
        h = res['hourly']
        
        # 配列の最後から現在時刻に最も近いインデックスを特定
        # 48時間以上のデータが返ってくるため、末尾付近から計算
        idx = (len(h['temperature_2m']) - 25) + dt.hour
        
        temp = h['temperature_2m'][idx]
        wind_speed = round(h['windspeed_10m'][idx] / 3.6, 1) # km/h -> m/s 変換
        wind_deg = h['winddirection_10m'][idx]
        
        # 過去48時間の合計降水量
        precip_48h = round(sum(h['precipitation'][:idx+1][-48:]), 1)

        # 16方位変換
        def get_wind_dir(deg):
            dirs = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
            return dirs[int((deg + 11.25) / 22.5) % 16]
        
        return temp, wind_speed, get_wind_dir(wind_deg), precip_48h
    except Exception as e:
        return None, None, "不明", 0.0
        
def main():
    # 1. 接続設定（既存のコード）
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = "https://docs.google.com/spreadsheets/d/12hcg7hagi0oLq3nS-K27OqIjBYmzMYXh_FcoS8gFFyE/edit?gid=0#gid=0"
    
    # --- データの読み込みとキャッシュ (API 429エラー対策) ---
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    
    @st.cache_data(ttl=600)
    def get_all_data(_conn, _url):
        # メインデータと場所マスターを一度に取得
        d_main = _conn.read(spreadsheet=_url, ttl="10m")
        d_master = _conn.read(spreadsheet=_url, worksheet="place_master", ttl="24h")
        return d_main, d_master
    
    conn = st.connection("gsheets", type=GSheetsConnection)
    df, df_master = get_all_data(conn, url)
    
    # --- タブ設定 ---
    tabs = st.tabs(["記録", "編集", "ギャラリー", "分析", "統計", "戦略", "マッチング", "デーモン佐藤","🏆 実績解除"])
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = tabs
    with tab1:
        # --- ロゴとタイトルのデザイン ---
        st.markdown(f"""
            <div style="text-align: center; padding: 20px 0;">
                <img src="{icon_url}" style="width: 120px; filter: drop-shadow(0 0 10px rgba(0, 255, 208, 0.4));">
                <h1 style="color: #ffffff !important; font-size: 2rem; font-weight: 900; letter-spacing: 0.1rem; margin-top: 10px; border-bottom: none;">
                    Kinetic Tide <span style="color: #00ffd0;">Data</span>
                </h1>
                <p style="color: #888; font-size: 0.8rem; text-transform: uppercase;">Advanced Anglers Log System</p>
            </div>
            
            <style>
                /* 文字色のリセットと全体への適用防止 */
                .stApp {{
                    color: #e0e0e0;
                }}
                /* アップロードエリアのカスタマイズ */
                [data-testid="stFileUploader"] {{
                    border: 2px dashed rgba(0, 255, 208, 0.2) !important;
                    border-radius: 15px !important;
                    padding: 10px !important;
                }}
                /* ボタンのデザイン */
                .stButton>button {{
                    font-weight: 900 !important;
                    letter-spacing: 0.05rem;
                    border-radius: 12px !important;
                    background-color: #1e2630 !important;
                    border: 1px solid rgba(0, 255, 208, 0.3) !important;
                }}
                /* ラベルの色（青色にならないように指定） */
                .stMarkdown p, label, .stSelectbox label, .stTextInput label {{
                    color: #cccccc !important;
                }}
            </style>
        """, unsafe_allow_html=True)
    
        # --- 念のためここでセッション状態の初期化 ---
        if "length_val" not in st.session_state:
            st.session_state.length_val = 0.0
        if "lat" not in st.session_state: st.session_state.lat = 0.0
        if "lon" not in st.session_state: st.session_state.lon = 0.0
        if "detected_place" not in st.session_state: st.session_state.detected_place = "新規地点"
        if "group_id" not in st.session_state: st.session_state.group_id = "default"
        if "target_dt" not in st.session_state: st.session_state.target_dt = datetime.now()
    
        uploaded_file = st.file_uploader("魚の写真を選択してください", type=["jpg", "jpeg", "png"])
        
        if uploaded_file:
            # --- 1. Exifから日付と場所を抽出 ---
            # GPSがない場合は get_exif_data 内で本渡瀬戸の座標が返されます
            dt_found, lat_found, lon_found = get_exif_data(uploaded_file)
            
            # セッション状態を更新
            if dt_found: st.session_state.target_dt = dt_found
            st.session_state.lat = lat_found
            st.session_state.lon = lon_found

            # --- 2. 場所の自動判定を実行 ---
            # ここで Place_master のデータと照合し、500m以内ならその場所名をセットします
            p_name, g_id = find_nearest_place(st.session_state.lat, st.session_state.lon, df_master)
            
            st.session_state.detected_place = p_name
            st.session_state.group_id = g_id
            
            st.success(f"📍 場所を「{p_name}」と判定しました。")

            # --- 2. 【ここがデバッグ表示】写真の日付で取得できるかテスト ---
            st.markdown("---") # 区切り線
            st.subheader("🔍 写真の解析結果チェック")
            
            test_dt = st.session_state.target_dt
            # 最寄りの観測所を特定
            station_info = find_nearest_tide_station(st.session_state.lat, st.session_state.lon)
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.write(f"📅 **写真の日時:** {test_dt.strftime('%Y/%m/%d %H:%M')}")
                st.write(f"📍 **最寄りの観測所:** {station_info['name']}")
            
            # 実際にその日付で潮汐JSONを引いてみる
            t_test = get_tide_details(station_info['code'], test_dt)
            
            with col_b:
                if t_test:
                    st.success(f"✅ 潮汐データ取得成功！")
                    st.write(f"🌊 潮位: {t_test['cm']}cm")
                    st.write(f"📈 状態: {t_test['phase']}")
                else:
                    st.error("❌ 潮汐データが引けません")
                    # どこを見に行こうとしたかURLを表示させる
                    year_val = test_dt.year
                    code_val = station_info['code']
                    st.code(f"試行URL: https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{year_val}/{code_val}.json")

            st.markdown("---")
    
            # --- ここから入力エリア（一本化） ---
            with st.expander("📍 位置情報の確認", expanded=False):
                if st.session_state.lat != 0.0:
                    st.map(pd.DataFrame({'lat': [st.session_state.lat], 'lon': [st.session_state.lon]}), zoom=14)
    
            st.subheader("📝 釣果の詳細")
            
            # 魚種選択
            fish_options = ["スズキ", "ヒラスズキ", "ボウズ", "バラシ", "カサゴ", "ターポン", "タチウオ", "マダイ", "チヌ", "キビレ", "ブリ", "アジ", "（手入力）"]
            selected_fish = st.selectbox("🐟 魚種を選択", fish_options)
            final_fish_name = st.text_input("魚種名を入力") if selected_fish == "（手入力）" else selected_fish
    
            # --- 【場所選択の強化版ロジック】 ---
            st.markdown("---")
            # マスターから場所リストを取得
            master_places = sorted(df_master['place_name'].unique().tolist())
            place_options = ["自動判定に従う", "（手入力で新規登録）"] + master_places
    
            selected_place_option = st.selectbox(
                "📍 場所を選択・修正", 
                options=place_options,
                index=0,
                help="自動判定が間違っている場合は、リストから正しい場所を選んでください。"
            )
    
            if selected_place_option == "自動判定に従う":
                place_name = st.text_input("場所名を確認/修正", value=st.session_state.detected_place)
                target_group_id = st.session_state.group_id
            elif selected_place_option == "（手入力で新規登録）":
                place_name = st.text_input("新規場所名を入力", value="")
                target_group_id = "default"
            else:
                # リストから選んだ場合
                place_name = selected_place_option
                matched = df_master[df_master['place_name'] == selected_place_option]
                target_group_id = matched['group_id'].iloc[0] if not matched.empty else "default"
                st.info(f"「{place_name}」として記録します。")
            # ----------------------------------------
    
            # 全長入力
            st.markdown("---")
            c1, c2, c3 = st.columns([1, 2, 1])
            if c1.button("➖ 0.5", use_container_width=True):
                st.session_state.length_val = max(0.0, st.session_state.length_val - 0.5)
            length_text = c2.text_input("全長(cm)", value=str(st.session_state.length_val) if st.session_state.length_val > 0 else "")
            st.session_state.length_val = normalize_float(length_text)
            if c3.button("➕ 0.5", use_container_width=True):
                st.session_state.length_val += 0.5
            
            lure = st.text_input("🪝 ルアー/仕掛け")
            angler = st.selectbox("👤 釣り人", ["長元", "川口", "山川"])
            memo = st.text_area("🗒️ 備考")
    
    # --- 🚀 記録ボタンを Tab1 かつ uploaded_file がある時だけに限定 ---
            # インデントを uploaded_file の中に一歩入れます
            if st.button("🚀 釣果を記録する", use_container_width=True, type="primary"):
                try:
                    with st.spinner("📊 データ解析中..."):
                        target_dt = st.session_state.target_dt   
                        
                        # 1. 気象・場所情報
                        temp, wind_s, wind_d, rain_48 = get_weather_data_openmeteo(st.session_state.lat, st.session_state.lon, target_dt)
                        m_age = get_moon_age(target_dt)
                        t_name = get_tide_name(m_age)
                        station_info = find_nearest_tide_station(st.session_state.lat, st.session_state.lon)
                        
                        # 2. 潮汐データの取得（前後1日分を統合）
                        all_events = []
                        tide_cm = 0
                        for delta in [-1, 0, 1]:
                            d_data = get_tide_details(station_info['code'], target_dt + timedelta(days=delta))
                            if d_data:
                                if 'events' in d_data: 
                                    all_events.extend(d_data['events'])
                                if delta == 0: 
                                    tide_cm = d_data['cm']
    
                        # 重要：時間順に並べ、重複を排除
                        all_events = sorted({ev['time']: ev for ev in all_events}.values(), key=lambda x: x['time'])
    
                        # --- 3. 潮位フェーズ判定ロジック ---
                        search_dt = target_dt + timedelta(minutes=5)
                        past_lows = [e for e in all_events if e['time'] <= search_dt and '干' in e['type']]
                        prev_l = past_lows[-1]['time'] if past_lows else None
                        past_highs = [e for e in all_events if e['time'] <= search_dt and '満' in e['type']]
                        prev_h = past_highs[-1]['time'] if past_highs else None
    
                        next_l = next((e['time'] for e in all_events if e['time'] > search_dt and '干' in e['type']), None)
                        next_h = next((e['time'] for e in all_events if e['time'] > search_dt and '満' in e['type']), None)
    
                        prev_ev = next((e for e in reversed(all_events) if e['time'] <= search_dt), None)
                        next_ev = next((e for e in all_events if e['time'] > search_dt), None)
                        
                        tide_phase = "不明"
                        if prev_ev and next_ev:
                            duration = (next_ev['time'] - prev_ev['time']).total_seconds()
                            elapsed = (target_dt - prev_ev['time']).total_seconds()
                            if duration > 0:
                                elapsed = max(0, elapsed)
                                p_type = "上げ" if "干" in prev_ev['type'] else "下げ"
                                step = max(1, min(9, int((elapsed / duration) * 10)))
                                tide_phase = f"{p_type}{step}分"
    
                        val_next_high = int((next_h - target_dt).total_seconds() / 60) if next_h else ""
                        val_next_low = int((next_l - target_dt).total_seconds() / 60) if next_l else ""
    
                        # 4. 画像処理
                        img_final = Image.open(uploaded_file)
                        try:
                            exif_orient = img_final._getexif()
                            if exif_orient:
                                orient = next((k for k, v in ExifTags.TAGS.items() if v == 'Orientation'), None)
                                if orient in exif_orient:
                                    if exif_orient[orient] == 3: img_final = img_final.rotate(180, expand=True)
                                    elif exif_orient[orient] == 6: img_final = img_final.rotate(270, expand=True)
                                    elif exif_orient[orient] == 8: img_final = img_final.rotate(90, expand=True)
                        except: pass
    
                        img_final.thumbnail((800, 800), Image.Resampling.LANCZOS)
                        img_bytes = io.BytesIO()
                        img_final.convert('RGB').save(img_bytes, format='JPEG', quality=70, optimize=True)
                        img_bytes.seek(0)
    
                        # 5. 保存実行
                        res = cloudinary.uploader.upload(img_bytes, folder="fishing_app")
                        
                        save_data = {
                            "filename": res.get("secure_url"), 
                            "datetime": target_dt.strftime("%Y/%m/%d %H:%M"),
                            "date": target_dt.strftime("%Y/%m/%d"), 
                            "time": target_dt.strftime("%H:%M"),
                            "lat": float(st.session_state.lat), "lon": float(st.session_state.lon),
                            "気温": temp, "風速": wind_s, "風向": wind_d, "降水量": rain_48, 
                            "潮位_cm": tide_cm, "月齢": m_age, "潮名": t_name,
                            "次の満潮まで_分": val_next_high, "次の干潮まで_分": val_next_low,
                            "直前の満潮_時刻": prev_h.strftime('%Y/%m/%d %H:%M') if prev_h else "",
                            "直前の干潮_時刻": prev_l.strftime('%Y/%m/%d %H:%M') if prev_l else "",
                            "潮位フェーズ": tide_phase, "場所": place_name, "魚種": final_fish_name,
                            "全長_cm": float(st.session_state.length_val), "ルアー": lure, "備考": memo,
                            "group_id": target_group_id, "観測所": station_info['name'], "釣り人": angler
                        }
    
                        df_main = conn.read(spreadsheet=url)
                        new_row = pd.DataFrame([save_data])
                        updated_df = pd.concat([df_main, new_row], ignore_index=True)
                        conn.update(spreadsheet=url, data=updated_df)
                        
                        st.cache_data.clear() 
                        st.success("✅ 記録完了しました！")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                        # --- データの読み込み（ここですでに df を取得済み） ---
                        df, df_master = get_all_data(conn, url)
    
                except Exception as e:
                    st.error(f"❌ 保存失敗: {e}")

                    
    # ↓ ここから下の「with tab...」が、すべて同じ左端の高さにあるか確認してください
    with tab2:
        # 関数そのものを引数として渡すことで、モジュール側で計算を可能にします
        show_edit_page(
            conn, 
            url, 
            get_weather_data_openmeteo, 
            find_nearest_tide_station, 
            get_tide_details, 
            get_moon_age, 
            get_tide_name
        )
    
    with tab3:
        # 保存時にキャッシュをクリアする設定にしていれば、ここは ttl="10m" のままでも
        # 保存直後は最新が表示されます。念を入れるなら今のまま ttl="0s" でもOKです。
        df_for_gallery = conn.read(spreadsheet=url, ttl="0s")
        show_gallery_page(df_for_gallery)
    
    with tab4:
        show_analysis_page(df)
    
    with tab5:
        # 統計ページの表示
        show_monthly_stats(df)
        
    with tab6:
        from strategy_analysis import show_strategy_analysis
        show_strategy_analysis(df)
    
    with tab7:
        show_matching_page(df)

    with tab8:  # ここが tabs8 になっていたりしませんか？
        import ai_module
        ai_module.show_ai_page(conn, url, df) # 前回の修正で df を追加した形
        
    with tab9:
        show_achievements_page(df) # ← 半角スペース4つ分、右にずらす
            
# --- ファイルの最後（一番下）にこれを追記 ---
if __name__ == "__main__":
    main()








