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
def get_tide_details(res, dt):
    """
    GitHubのJSONレスポンス(res)から、指定日時(dt)の潮位を解析する。
    日時文字列に空白が含まれる異常系にも対応。
    """
    try:
        data = res.json()
        # --- ここからデバッグ用 ---
        st.write(f"📂 JSON内のデータ件数: {len(data.get('data', []))}件")
        if len(data.get('data', [])) > 0:
            first_date = data['data'][0].get('date')
            last_date = data['data'][-1].get('date')
            st.write(f"📅 データの範囲: {first_date} ～ {last_date}")
        # --- ここまで ---
        target_date_str = dt.strftime("%Y-%m-%d")
        
        # 1. 該当日のデータを検索 (日付文字列の前後空白をトリム)
        day_info = next((i for i in data['data'] if i['date'].strip() == target_date_str), None)
        
        if not day_info:
            return {"cm": 0, "phase": "不明", "events": [], "hourly": []}

        # 2. 毎時潮位の取得
        hourly = day_info['hourly']
        
        # 3. 現在時刻(dt)の潮位を線形補間
        h = dt.hour
        mi = dt.minute
        h2 = (h + 1) % 24
        
        t1 = hourly[h]
        t2 = hourly[h2]
        
        # 分単位で補間計算
        current_cm = int(round(t1 + (t2 - t1) * (mi / 60.0)))

        # 4. イベント(満潮・干潮)のパース (空白対策)
        event_times = []
        for ev in day_info['events']:
            # "10: 6" -> "10:6" への置換とPandasによる柔軟なパース
            ev_time_str = ev['time'].replace(" ", "")
            # target_date_strと結合してフル日時で解釈
            ev_dt = pd.to_datetime(f"{target_date_str} {ev_time_str}")
            event_times.append({"time": ev_dt, "type": ev['type']})
        
        event_times = sorted(event_times, key=lambda x: x['time'])

        # 5. 潮位フェーズの計算
        phase_text = "不明"
        prev_ev = next((e for e in reversed(event_times) if e['time'] <= dt), None)
        next_ev = next((e for e in event_times if e['time'] > dt), None)

        if prev_ev and next_ev:
            duration = (next_ev['time'] - prev_ev['time']).total_seconds()
            elapsed = (dt - prev_ev['time']).total_seconds()
            if duration > 0:
                step = max(1, min(9, int((elapsed / duration) * 10)))
                p_type = "上げ" if "干" in prev_ev['type'] else "下げ"
                phase_text = f"{p_type}{step}分"
        elif prev_ev:
            p_type = "上げ" if "干" in prev_ev['type'] else "下げ"
            phase_text = f"{p_type}潮"

        return {
            "cm": current_cm, 
            "phase": phase_text, 
            "events": event_times, 
            "hourly": hourly
        }

    except Exception as e:
        # ログにエラーを表示（実際のアプリ画面には出さず、内部的に0を返す）
        print(f"DEBUG: 潮汐解析エラー: {e}")
        return {"cm": 0, "phase": "不明", "events": [], "hourly": []}
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
    tabs = st.tabs(["記録", "編集", "ギャラリー", "分析", "統計", "戦略", "マッチング", "デーモン佐藤"])
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
    
        uploaded_file = st.file_uploader("魚の写真を選択してください", type=["jpg", "jpeg", "png"], )
        
        if uploaded_file:
            img_for_upload = Image.open(uploaded_file)
            exif = img_for_upload._getexif()
            
            # 1. 写真解析（一度だけ実行）
            if exif:
                # 日時抽出
                for tag_id, value in exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                    if tag_name == 'DateTimeOriginal':
                        try:
                            clean_val = str(value).strip()[:16].replace(":", "/", 2)
                            st.session_state.target_time_str = item['time'].replace(' ', '') # 余計な空白を消す
                        except: pass
                
                # 座標・場所抽出
                geo = get_geotagging(exif)
                if geo:
                    lat = get_decimal_from_dms(geo['GPSLatitude'], geo['GPSLatitudeRef'])
                    lon = get_decimal_from_dms(geo['GPSLongitude'], geo['GPSLongitudeRef'])
                    if lat and lon:
                        st.session_state.lat, st.session_state.lon = lat, lon
                        p_name, g_id = find_nearest_place(lat, lon, df_master)
                        st.session_state.detected_place = p_name
                        st.session_state.group_id = g_id
    
            st.success(f"📸 解析完了: {st.session_state.detected_place} ({st.session_state.target_dt.strftime('%Y/%m/%d %H:%M')})")
    
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
        
# --- ファイルの最後（一番下）にこれを追記 ---
if __name__ == "__main__":
    main()






