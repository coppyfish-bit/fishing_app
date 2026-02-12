import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime, timedelta
import requests
import math
import io
import cloudinary
import cloudinary.uploader
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
import base64

def get_geotagging(exif):
    # GPSInfoのタグIDは 34853 です
    gps_info = exif.get(34853)
    if not gps_info:
        return None
    
    # お示しいただいたデータ構造に合わせて、直接インデックスで取得します
    # 1:LatitudeRef, 2:Latitude, 3:LongitudeRef, 4:Longitude
    geotagging = {
        'GPSLatitudeRef': gps_info.get(1) or gps_info.get("1"),
        'GPSLatitude':    gps_info.get(2) or gps_info.get("2"),
        'GPSLongitudeRef': gps_info.get(3) or gps_info.get("3"),
        'GPSLongitude':   gps_info.get(4) or gps_info.get("4")
    }
    
    # 必要なデータが揃っているかチェック
    if not geotagging['GPSLatitude'] or not geotagging['GPSLongitude']:
        return None
        
    return geotagging

def get_decimal_from_dms(dms, ref):
    if not dms or not ref:
        return None
    
    try:
        # お示しいただいたデータは [32.0, 28.0, 34.96] のようなリスト形式
        # 各要素を確実に float に変換します
        d = float(dms[0])
        m = float(dms[1])
        s = float(dms[2])
        
        decimal = d + (m / 60.0) + (s / 3600.0)
        
        # 南緯(S)や西経(W)の場合はマイナスにする
        if ref in ['S', 'W']:
            decimal = -decimal
            
        return decimal
    except Exception as e:
        # 計算エラーが起きた場合に備えてログを出す（任意）
        # st.error(f"DMS変換エラー: {e}")
        return None
def calculate_distance(lat1, lon1, lat2, lon2):
    if None in [lat1, lon1, lat2, lon2]: return 999.0
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))


def get_best_station(lat, lon, place_name):
    """
    場所名または座標から、最も適切な気象庁観測所を返す
    """
    # 観測所マスタ（ご提示いただいたデータ）
    STATIONS = [
        {"name": "本渡瀬戸", "lat": 32.26, "lon": 130.13, "code": "HS"},
        {"name": "苓北",     "lat": 32.28, "lon": 130.20, "code": "RH"},
        {"name": "口之津",   "lat": 32.36, "lon": 130.12, "code": "KT"},
        {"name": "八代",     "lat": 32.31, "lon": 130.34, "code": "O5"},
    ]

    # 1. 場所名（キーワード）による優先判定
    # 名前から判断できる場合は、計算せずに特定の観測所を返す
    p_name = place_name if place_name else ""
    if any(k in p_name for k in ["苓北", "富岡", "都呂々", "通詞"]):
        return next(s for s in STATIONS if s["name"] == "苓北")
    if any(k in p_name for k in ["本渡", "瀬戸", "下浦", "栖本"]):
        return next(s for s in STATIONS if s["name"] == "本渡瀬戸")
    if any(k in p_name for k in ["八代", "鏡", "日奈久", "不知火"]):
        return next(s for s in STATIONS if s["name"] == "八代")
    if any(k in p_name for k in ["口之津", "島原", "南島原", "加津佐"]):
        return next(s for s in STATIONS if s["name"] == "口之津")

    # 2. 座標による距離計算（キーワードにヒットしなかった場合）
    # 現在の座標(lat, lon)に最も近い観測所を探す
    best_s = STATIONS[0]
    min_dist = float('inf')

    for s in STATIONS:
        # 三平方の定理で簡易距離を計算
        dist = ((lat - s["lat"])**2 + (lon - s["lon"])**2)**0.5
        if dist < min_dist:
            min_dist = dist
            best_s = s

    return best_s
    
def display_tide_graph(lat, lon, date_str, hit_time_str, tide_val, tide_phase):
    try:
        # 1. ヒット時刻を数値化
        if hit_time_str and str(hit_time_str) != 'nan':
            h, m = map(int, str(hit_time_str).split(':')[:2])
            hit_h = h + m/60
        else:
            hit_h = 12.0

        # 2. 表示範囲（前後6時間）
        start_h = hit_h - 6
        end_h = hit_h + 6
        hours = np.linspace(start_h, end_h, 48)
        
        # 3. 【修正】シミュレーションではなく、シートの潮位(tide_val)を基準にする
        # 潮位フェーズが「下げ」なら右下がり、「上げ」なら右上がりの波を作る
        base_level = float(tide_val) if str(tide_val).isdigit() else 150
        direction = -1 if "下" in str(tide_phase) else 1
        
        # ヒット時を中心に、潮位フェーズに合わせた傾斜をつける
        tide_curve = direction * 50 * np.sin(2 * np.pi * (hours - hit_h) / 12.42) + base_level
        
        # 4. グラフ描画
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=hours, y=tide_curve,
            mode='lines', fill='tozeroy',
            line=dict(color='#007BFF', width=3),
            hovertemplate='%{x:.1f}時: %{y:.1f}cm<extra></extra>'
        ))

        # HIT! 地点（シートの潮位をそのまま使う）
        fig.add_trace(go.Scatter(
            x=[hit_h], y=[base_level],
            mode='markers+text',
            text=["HIT!"], textposition="top center",
            marker=dict(color='red', size=18, symbol='star'),
        ))

        fig.update_layout(
            height=200, margin=dict(l=10, r=10, t=30, b=10),
            xaxis=dict(title="時間", tickvals=np.arange(np.floor(start_h), np.ceil(end_h) + 1, 2), gridcolor='lightgray'),
            yaxis=dict(visible=False),
            showlegend=False,
            title=dict(text=f"📌 {tide_phase} (潮位:{tide_val}cm)", font=dict(size=14))
        )
        
        # スマホでのスクロールを優先する設定
        st.plotly_chart(fig, use_container_width=True, config={'staticPlot': True})

    except Exception as e:
        st.error(f"グラフ作成エラー: {e}")
        
try:
    cloudinary.config(
        cloud_name = st.secrets["cloudinary"]["cloud_name"],
        api_key = st.secrets["cloudinary"]["api_key"],
        api_secret = st.secrets["cloudinary"]["api_secret"],
        secure = True
    )
except Exception as e:
    st.error("Cloudinaryの設定が読み込めません。")
    
def get_moon_age(dt):
    base_new_moon = datetime(2023, 1, 22, 5, 53)
    lunar_cycle = 29.530588
    diff_days = (dt - base_new_moon).total_seconds() / 86400
    return round(diff_days % lunar_cycle, 1)

def get_wind_direction_label(degree):
    if degree is None: return ""
    labels = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
    return labels[int((degree + 11.25) / 22.5) % 16]

def get_weather_data(lat, lon, dt):
    try:
        # 当日以降はforecast、過去はarchiveを使用
        is_past = dt.date() < datetime.now().date()
        url = "https://archive-api.open-meteo.com/v1/archive" if is_past else "https://api.open-meteo.com/v1/forecast"
        
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": dt.strftime('%Y-%m-%d'),
            "end_date": dt.strftime('%Y-%m-%d'),
            "hourly": "temperature_2m,windspeed_10m,winddirection_10m,precipitation",
            "timezone": "Asia/Tokyo"
        }
        res = requests.get(url, params=params, timeout=10).json()
        h = res.get('hourly', {})
        idx = dt.hour
        
        return (
            h.get('temperature_2m', [None]*24)[idx],
            h.get('windspeed_10m', [None]*24)[idx],
            h.get('winddirection_10m', [None]*24)[idx],
            h.get('precipitation', [None]*24)[idx]
        )
    except:
        return None, None, None, None

def get_tide_details(lat, lon, dt, place_name=""):
    station = get_best_station(lat, lon, place_name)
    dt = dt.replace(tzinfo=None)
    st_code = str(station['code'])
    
    # 試行するURLリスト（大文字・小文字両対応）
    urls = [
        f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{dt.year}/{st_code.upper()}.txt",
        f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{dt.year}/{st_code.lower()}.txt"
    ]
    
    for url in urls:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                continue
            
            lines = response.text.splitlines()
            
            # 日付の照合用文字列を作成
            # データ内の形式例: "26 1 1HS" (年2桁 空白 月 空白 日 地点)
            # 非常に不安定なため、末尾から検索して日付と地点コードが一致する行を探す
            target_line = None
            date_marker = f"{str(dt.year)[2:]}{dt.month:2}{dt.day:2}{st_code.upper()}"
            
            for line in lines:
                # 行の72文字目付近から日付情報が始まります
                if date_marker.replace(" ", "") in line.replace(" ", ""):
                    target_line = line
                    break
            
            if not target_line:
                continue

            # --- 1. 毎時潮位の解析 (0-23時 各3桁固定) ---
            hour = dt.hour
            # 0時(0-3文字目), 1時(3-6文字目)...
            tide_part = target_line[hour*3 : (hour*3)+3].strip()
            tide_cm = int(tide_part) if tide_part else 0

            # --- 2. 満潮・干潮時刻の解析 (フェーズ判定用) ---
            events = []
            # 満潮: 80文字目から 7桁(時刻4+潮位3) × 4回
            for i in range(4):
                start = 80 + (i * 7)
                t_str = target_line[start : start+4].strip()
                if t_str and t_str != "9999":
                    events.append({"type": "満潮", "time": datetime(dt.year, dt.month, dt.day, int(t_str[:2]), int(t_str[2:]))})
            
            # 干潮: 108文字目から 7桁(時刻4+潮位3) × 4回
            for i in range(4):
                start = 108 + (i * 7)
                t_str = target_line[start : start+4].strip()
                if t_str and t_str != "9999":
                    events.append({"type": "干潮", "time": datetime(dt.year, dt.month, dt.day, int(t_str[:2]), int(t_str[2:]))})
            
            events.sort(key=lambda x: x["time"])
            
            # 潮位フェーズの判定
            phase = "判定中"
            next_ev = next((e for e in events if e["time"] > dt), None)
            if next_ev:
                phase = "上げ潮" if next_ev["type"] == "満潮" else "下げ潮"
            else:
                prev_ev = events[-1] if events else None
                if prev_ev:
                    phase = "下げ潮" if prev_ev["type"] == "満潮" else "上げ潮"

            return {
                "潮位フェーズ": phase,
                "潮位_cm": tide_cm,
                "観測所": station["name"]
            }

        except Exception as e:
            continue

    return {"潮位フェーズ": "取得失敗", "潮位_cm": 0, "観測所": station["name"]}
        
def get_tide_name(dt):
    base_new_moon = datetime(2023, 1, 22, 5, 53)
    lunar_cycle = 29.530588
    age = ((dt - base_new_moon).total_seconds() / 86400) % lunar_cycle
    if age < 3.0 or age > 26.5: return "大潮"
    elif age < 7.0: return "中潮"
    elif age < 11.0: return "小潮"
    elif age < 13.0: return "長潮"
    elif age < 14.0: return "若潮"
    elif age < 18.0: return "大潮"
    elif age < 22.0: return "中潮"
    else: return "小潮"

def find_nearest_place(current_lat, current_lon, master_df, threshold_m=500):
    if master_df is None or master_df.empty: return None, None
    nearest_place, min_dist = None, float('inf')
    for _, row in master_df.iterrows():
        dist = calculate_distance(current_lat, current_lon, row['latitude'], row['longitude'])
        if dist < min_dist:
            min_dist, nearest_place = dist, row
    if min_dist <= (threshold_m / 1000):
        return nearest_place['place_name'], nearest_place['group_id']
    return None, None

def update_spreadsheet(df):
    """
    アプリ上で編集・削除した後のDataFrameをスプレッドシートに丸ごと上書きする
    """
    try:
        # スプレッドシートを開く
        sh = gc.open_by_key(st.secrets["gcp_service_account"]["spreadsheet_id"])
        worksheet = sh.get_worksheet(0)
        
        # 既存の内容を消去して、新しいデータを書き込む
        worksheet.clear()
        # ヘッダーとデータをリスト形式に変換して書き込み
        set_with_dataframe(worksheet, df)
        st.success("スプレッドシートを更新しました！")
    except Exception as e:
        st.error(f"更新に失敗しました: {e}")


# --- 3. 接続の初期化 (ここで conn を作る) ---
try:
    # 接続オブジェクトの作成
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    
    # 【節約術】Session State を使って読み込み回数を減らす
    # 1分間（60s）はAPIを叩かず、手元のデータ(session_state)を使います
    if "df" not in st.session_state:
        st.session_state.df = conn.read(spreadsheet=url, ttl="60s")
    
    # 場所マスターも同様に保持
    if "m_df" not in st.session_state:
        st.session_state.m_df = conn.read(spreadsheet=url, worksheet="place_master", ttl="60s")

    # 共通変数として使いやすくしておく
    df = st.session_state.df
    m_df = st.session_state.m_df

except Exception as e:
    st.error(f"接続の初期化に失敗しました: {e}")
    st.stop()  # ここで止めれば、これ以降の NameError は起きません
    
# --- 2. メイン UI 制御 ---
st.set_page_config(page_title="Fishing AI Log", layout="centered")
st.title("🎣 釣果統合ログシステム")

# --- タブの作成 ---
tab1, tab2, tab3 = st.tabs(["📝 釣果登録", "🔧 履歴の修正・削除","🖼️ ギャラリー"])

# ==========================================
# タブ1: 釣果登録
# ==========================================
with tab1:
    # --- 1. データの読み込み ---
    try:
        # 接続と設定の再読み込み（セッション状態を活用）
        conn = st.connection("gsheets", type=GSheetsConnection)
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        # メインデータ
        if "df" not in st.session_state:
            st.session_state.df = conn.read(spreadsheet=url, ttl="5m")
        # 場所マスター
        if "m_df" not in st.session_state:
            st.session_state.m_df = conn.read(spreadsheet=url, worksheet="place_master", ttl="10m")
        
        df = st.session_state.df
        m_df = st.session_state.m_df
    except Exception as e:
        st.error(f"スプレッドシート接続エラー: {e}")
        st.stop()

# --- 📸 写真アップロード設定 ---
    # デザイン（青色ボタン）
    st.markdown("""
        <style>
        div[data-testid="stFileUploader"] section button {
            background-color: #007BFF !important;
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
# --- 2. ファイルアップロードとEXIF解析 ---
    uploaded_file = st.file_uploader("📸 写真を選択", type=['jpg', 'jpeg'], key="main_uploader")
    
    # 【修正ポイント】ここで定義した変数を最後まで使う
    final_lat = 32.5
    final_lon = 130.0
    default_dt = datetime.now()

    if uploaded_file:
        img = Image.open(uploaded_file)
        exif = img._getexif()
        if exif:
            # --- デバッグ用コードここから ---
            st.write("🔍 EXIF解析ログ:")
            st.write(f"- EXIFタグの総数: {len(exif)}")
            # GPSInfoのタグIDは 34853 です
            if 34853 in exif:
                st.success("✅ 画像内にGPSタグ（34853）を発見しました！")
                st.write("- GPSInfoの中身:", exif[34853])
            else:
                st.error("❌ この画像にはGPS情報が書き込まれていません。")
            # --- デバッグ用コードここまで ---
        if exif:
            geotags = get_geotagging(exif)
            if geotags:
                # DMS形式から十進法へ変換
                lat_res = get_decimal_from_dms(geotags.get('GPSLatitude'), geotags.get('GPSLatitudeRef'))
                lon_res = get_decimal_from_dms(geotags.get('GPSLongitude'), geotags.get('GPSLongitudeRef'))
                if lat_res:
                    final_lat = lat_res
                    final_lon = lon_res
            
            # 日時も取得
            dt_str = exif.get(36867)
            if dt_str:
                try: default_dt = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S')
                except: passpass

    # --- 3. 場所の判定と入力（修正版） ---
    detected_name, detected_id = find_nearest_place(final_lat, final_lon, m_df)
    
    st.markdown("### 📍 釣り場")

    # A: 登録済みリスト（初期値を「選択なし」にする）
    place_to_id = dict(zip(m_df['place_name'], m_df['group_id'])) if not m_df.empty else {}
    manual_sel = st.selectbox(
        "過去の登録地点から選ぶ", 
        ["-- リストから選ぶ場合はこちら --"] + list(place_to_id.keys()),
        key="place_manual_select_v4"
    )

    # B: 入力・表示欄
    if manual_sel != "-- リストから選ぶ場合はこちら --":
        final_place_name = manual_sel
        final_group_id = place_to_id[manual_sel]
        is_new_place = False
        st.info(f"✅ 過去の地点を選択中: {final_place_name}")
    else:
        # 自動判定された名前があれば表示、なければ空欄
        default_val = detected_name if detected_name else ""
        final_place_name = st.text_input("釣り場名（修正・新規入力可）", value=default_val)
        
        if detected_name and final_place_name == detected_name:
            final_group_id = detected_id
            is_new_place = False
            st.success(f"📌 GPSから「{detected_name}」と判定しました")
        else:
            final_group_id = int(m_df["group_id"].max() + 1) if not m_df.empty else 1
            is_new_place = True
            if final_place_name:
                st.warning(f"🆕 「{final_place_name}」を新規登録します")
# --- 4. 魚種登録（重複を削除し、1つに統合） ---
    st.subheader("🐟 魚種")
    fish_options = ["ボウズ","スズキ", "ヒラスズキ", "ターポン", "タチウオ", "コチ", "ヒラメ","カサゴ", "クロダイ", "キビレ","キジハタ","マダイ","その他（手入力）"]
    
    # 選択肢と手入力をスッキリ並べる
    selected_fish = st.selectbox("魚種を選択", fish_options, key="fish_sel_final")
    
    # 「その他」を選んだ時や、補足したい時だけ入力する欄
    manual_fish_name = st.text_input("魚種名（手入力・補足）", placeholder="例：アカハタ、またはサイズ補足など", key="fish_manual_final")

    # 最終的な保存名を決定（手入力があればそちらを優先）
    final_fish_name = manual_fish_name if manual_fish_name else selected_fish

# --- 5. 全長入力 ---
    st.markdown("""
        <style>
        div[data-testid="stNumberInput"] input {
            font-size: 40px !important;
            height: 70px !important;
            font-weight: bold !important;
            color: #FF4B4B !important;
            text-align: center !important;
        }
        div[data-testid="stNumberInput"] input::placeholder {
            font-size: 18px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    final_length = st.number_input(
        "全長 (cm)", 
        min_value=0.0, max_value=300.0, value=None, 
        placeholder="ここをタップして入力",
        step=0.1, format="%.1f", key="final_len_input_fixed"
    )

    # --- 6. その他入力項目 ---
    st.markdown("---")
    lure_sel = st.text_input("ルアー名", placeholder="例：カゲロウ125MD", key="lure_name_final")
    lure_extra = st.text_input("詳細・カラー (任意)", key="lure_color_final")
    lure_in = lure_sel + (f" ({lure_extra})" if lure_extra else "")

    angler = st.selectbox("👤 釣り人", ["長元", "川口", "山川"], key="angler_final")
    memo_in = st.text_area("メモ", placeholder="ヒットパターンなど", key="memo_final")

    # 日時入力（写真から取得したdefault_dtを初期値に）
    c1, c2 = st.columns(2)
    with c1: date_in = st.date_input("日付", default_dt.date())
    with c2: time_in = st.time_input("時刻", default_dt.time())

    # --- 7. 保存処理（1つの青いボタンに統合） ---
    st.markdown("""
        <style>
        div.stButton > button[kind="primary"] {
            background-color: #007BFF !important;
            color: white !important;
            height: 60px !important;
            font-size: 20px !important;
            font-weight: bold !important;
            border-radius: 10px !important;
        }
        </style>
    """, unsafe_allow_html=True)

# --- ボタンが押された時の処理 ---
if st.button("🚀 釣果を記録する", type="primary", use_container_width=True, key="blue_submit_btn"):
    drive_url = "https://via.placeholder.com/400x300.png?text=No+Image"
    
    # 1. 画像のアップロード処理
    if uploaded_file is not None:
        try:
            with st.spinner('📸 画像をアップロード中...'):
                uploaded_file.seek(0) 
                res = cloudinary.uploader.upload(
                    uploaded_file, 
                    folder="fishing_app",
                    transformation=[
                        {'width': 800, 'crop': "limit"},
                        {'quality': "auto", 'fetch_format': "auto"}
                    ]
                )
                drive_url = res.get("secure_url")
        except Exception as e:
            st.error(f"❌ 画像アップロード失敗: {e}")
            st.stop()
        
    # 2. データの保存処理
    with st.spinner('📊 データを解析・保存中...'):
        try:
            # --- 【重要】日時の確定 ---
            target_dt = datetime.combine(date_in, time_in)
            
            # --- 【重要】緯度・経度の最終決定 ---
            # 手動選択がある場合はマスターの座標を、なければ判定された座標を使用
            if manual_sel != "-- 自動判定・新規入力 --" and not m_df.empty:
                place_info = m_df[m_df['place_name'] == manual_sel].iloc[0]
                lat_val = place_info['latitude']
                lon_val = place_info['longitude']
            else:
                lat_val = final_lat
                lon_val = final_lon

            # --- 【重要】外部データの取得 ---
            # 1. 潮汐名の取得（大潮・小潮など）
            t_name = get_tide_name(target_dt)
            
            # 2. 潮汐詳細の取得（気象庁データ解析）
            # HSなどの地点コード小文字変換に対応した関数を呼び出す
            t_info = get_tide_details(lat_val, lon_val, target_dt, final_place_name)
            
            # 3. 気象データの取得（Open-Meteo）
            temp, wind_s, wind_d, prec = get_weather_data(lat_val, lon_val, target_dt)

            # --- 3. 保存用データセットの作成 ---
            save_data = {
                "filename": drive_url, 
                "datetime": target_dt.strftime('%Y-%m-%d %H:%M'),
                "date": date_in.strftime('%Y-%m-%d'), 
                "time": time_in.strftime('%H:%M'),
                "lat": lat_val, 
                "lon": lon_val, 
                "気温": temp, 
                "風速": wind_s, 
                "風向": get_wind_direction_label(wind_d) if wind_d is not None else "不明", 
                "降水量": prec,
                "潮位_cm": t_info.get("潮位_cm", 0), 
                "月齢": get_moon_age(target_dt), 
                "潮名": t_name,
                "潮位フェーズ": t_info.get("潮位フェーズ", "不明"), 
                "場所": final_place_name, 
                "魚種": final_fish_name, 
                "全長_cm": final_length if final_length else 0.0,
                "ルアー": lure_in, 
                "備考": memo_in, 
                "group_id": final_group_id, 
                "観測所": t_info.get("観測所", "不明"), 
                "釣り人": angler
            }

            # --- 4. スプレッドシートへの書き込み ---
            cols = ["filename", "datetime", "date", "time", "lat", "lon", "気温", "風速", "風向", "降水量", "潮位_cm", "月齢", "潮名", "潮位フェーズ", "場所", "魚種", "全長_cm", "ルアー", "備考", "group_id", "観測所", "釣り人"]
            new_row_df = pd.DataFrame([save_data])[cols]
            
            # メインシートの更新
            current_df = conn.read(spreadsheet=url, ttl=0)
            updated_df = pd.concat([current_df, new_row_df], ignore_index=True)
            conn.update(spreadsheet=url, data=updated_df)
            
            # 新規地点の場合、場所マスターも自動更新
            if is_new_place:
                new_m = pd.DataFrame([{
                    "group_id": final_group_id, 
                    "place_name": final_place_name, 
                    "latitude": lat_val, 
                    "longitude": lon_val
                }])
                try:
                    current_m = conn.read(spreadsheet=url, worksheet="place_master", ttl=0)
                    updated_m = pd.concat([current_m, new_m], ignore_index=True)
                    conn.update(spreadsheet=url, worksheet="place_master", data=updated_m)
                except:
                    st.warning("⚠️ 場所マスターの更新に失敗しました（シートが存在しない可能性があります）")

            # --- 5. 完了通知と画面リセット ---
            st.success("🎉 釣果を保存しました！")
            st.balloons()
            
            # キャッシュをクリアして最新データを反映させる
            st.cache_data.clear()
            time.sleep(2)
            st.rerun()

        except Exception as e:
            st.error(f"❌ 保存エラー: {e}")
            # デバッグ用にエラーの詳細を表示
            import traceback
            st.code(traceback.format_exc())
# タブ2: 釣果の修正・削除
# ==========================================
with tab2:
    st.subheader("📸 釣果履歴（直近5件展開）")

    # API制限対策：手動リロードボタン
    if st.button("🔄 最新の履歴に更新", key="reload_history", use_container_width=True):
        st.cache_data.clear()
        if 'df' in st.session_state:
            del st.session_state.df
        st.rerun()

    # タブ2全体を包む大きな try ブロック
    try:
        # セッション状態からデータを取得
        df = st.session_state.get('df', None)
        
        if df is None or df.empty:
            st.info("履歴がまだありません。")
        else:
            # 削除時のインデックスのズレを防ぐため、コピーを作成
            target_df = df.copy()
            # 表示用に新しい順（最新が上）にする
            display_df = target_df.iloc[::-1]
            
            for i, (original_index, row) in enumerate(display_df.iterrows()):
                # 直近5件だけ最初から開く
                is_expanded = True if i < 5 else False
                
                # 表示用ラベルの作成
                d_val = row.get('date', '不明')
                f_val = row.get('魚種', '不明')
                s_val = row.get('全長_cm', row.get('全長', '0'))
                expander_label = f"📌 {d_val} | {f_val} | {s_val}cm"
                
                with st.expander(expander_label, expanded=is_expanded):
                    # --- 1. 画像と潮汐グラフ表示 ---
                    img_url = str(row.get('filename', '')).strip()
                    if img_url.startswith('http'):
                        st.image(img_url, use_container_width=True)
                        
                        # シートから潮汐データを取得してグラフ表示
                        current_lat = row.get('lat', 32.5)
                        current_lon = row.get('lon', 130.0)
                        current_tide = row.get('潮位_cm', 0)
                        current_phase = row.get('潮位フェーズ', '不明')
                        current_time = row.get('time', row.get('時刻', '12:00'))
                        current_date = row.get('date', '2026-01-01')
                        
                        display_tide_graph(
                            lat=current_lat, 
                            lon=current_lon, 
                            date_str=str(current_date), 
                            hit_time_str=str(current_time),
                            tide_val=current_tide,
                            tide_phase=current_phase
                        )
                    else:
                        st.caption("📷 画像なし")
                    
                    # --- 2. 修正用入力フォーム ---
                    # サイズ入力（数値変換エラー対策付き）
                    try:
                        f_s_val = float(s_val)
                    except:
                        f_s_val = 0.0

                    new_size = st.number_input(
                        "📏 サイズ (cm)", 
                        value=f_s_val, 
                        step=0.1, 
                        format="%.1f",
                        key=f"edit_size_{original_index}"
                    )

                    angler_list = ["長元", "川口", "山川"]
                    current_angler = row.get('釣り人', '長元')
                    new_angler = st.selectbox(
                        "👤 釣り人", 
                        angler_list, 
                        index=angler_list.index(current_angler) if current_angler in angler_list else 0,
                        key=f"edit_angler_{original_index}"
                    )

                    new_lure = st.text_input(
                        "🎣 ルアー", 
                        value=str(row.get('ルアー', '')), 
                        key=f"edit_lure_{original_index}"
                    )

                    new_memo = st.text_area(
                        "📝 備考", 
                        value=str(row.get('備考', '')), 
                        key=f"edit_memo_{original_index}"
                    )

                    # --- 3. ボタンエリア ---
                    st.write("")
                    col_btn1, col_btn2 = st.columns(2)
                    
                    with col_btn1:
                        if st.button("🆙 修正保存", key=f"update_btn_{original_index}", type="primary", use_container_width=True):
                            with st.spinner('修正中...'):
                                try:
                                    df.at[original_index, '全長_cm'] = new_size
                                    df.at[original_index, '釣り人'] = new_angler
                                    df.at[original_index, 'ルアー'] = new_lure
                                    df.at[original_index, '備考'] = new_memo
                                    conn.update(spreadsheet=url, data=df)
                                    st.success("修正しました！")
                                    st.cache_data.clear()
                                    if 'df' in st.session_state: del st.session_state.df
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"修正失敗: {e}")

                    with col_btn2:
                        if st.button("🗑️ 削除する", key=f"del_btn_{original_index}", use_container_width=True):
                            with st.spinner('削除中...'):
                                try:
                                    updated_df = df.drop(original_index)
                                    conn.update(spreadsheet=url, data=updated_df)
                                    st.success("削除しました")
                                    st.cache_data.clear()
                                    if 'df' in st.session_state: del st.session_state.df
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"削除失敗: {e}")

    except Exception as e:
        st.error(f"タブ2でエラーが発生しました: {e}")
# --- ここからタブ3 ---
with tab3:
    st.subheader("📸 釣果フォトギャラリー")
    # インデントを 'with' より4マス右に統一
    display_count = st.slider("表示件数", 5, 50, 10)
    
    if not df.empty:
        # 最新のデータから順に取得
        latest_data = df.sort_values(by=['date', 'time'], ascending=False).head(display_count)
        
        for idx, row in latest_data.iterrows():
            # --- 1. データの準備 ---
            img = str(row.get('filename', '')).strip()
            if not img.startswith('http'): 
                continue
            
            # 表示用テキストの作成
            fish_text = f"{row.get('魚種', '不明')} {row.get('全長_cm', '---')}cm"
            f_date = str(row.get('date'))
            f_time = str(row.get('time'))[:5]
            
            info_text = f"📅 {f_date} {f_time} / 📍 {row.get('場所', '---')}"
            tide_detail = f"🌊 {row.get('潮位_cm','--')}cm ({row.get('潮位フェーズ','--')})"
            env_info = f"🍃 {row.get('風向','--')} {row.get('風速','--')}m/s | 🎣 {row.get('ルアー','--')} | ☔ {row.get('降水量','--')}mm"

            # --- 2. 写真にデータを重ねて表示 (HTML) ---
            html_block = (
                f'<div style="position:relative; width:100%; border-radius:15px; overflow:hidden; margin-top:20px; box-shadow:0 4px 12px rgba(0,0,0,0.3);">'
                f'<img src="{img}" style="width:100%; display:block;">'
                # 左上：魚種タグ
                f'<div style="position:absolute; top:12px; left:12px; z-index:10; background:rgba(220,20,60,0.95); color:white; padding:5px 14px; border-radius:20px; font-weight:bold; font-size:15px;">'
                f'{fish_text}</div>'
                # 下部：グラデーションパネル
                f'<div style="position:absolute; bottom:0; left:0; right:0; z-index:5; background:linear-gradient(transparent, rgba(0,0,0,0.95) 50%); color:white; padding:40px 15px 15px 15px;">'
                f'<div style="font-size:15px; font-weight:bold; margin-bottom:8px; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);">{info_text}</div>'
                f'<div style="display:flex; flex-wrap:wrap; gap:10px; font-size:12px; font-weight:500;">'
                f'<div style="background:rgba(255,255,255,0.2); padding:3px 10px; border-radius:6px; border:0.5px solid rgba(255,255,255,0.3);">{tide_detail}</div>'
                f'<div style="background:rgba(255,255,255,0.2); padding:3px 10px; border-radius:6px; border:0.5px solid rgba(255,255,255,0.3);">{env_info}</div>'
                f'</div></div></div>'
            )
            st.markdown(html_block, unsafe_allow_html=True)

            # --- 3. 潮汐グラフを表示 ---
            display_tide_graph(
                lat=row.get('lat', 32.5),
                lon=row.get('lon', 130.0), 
                date_str=f_date, 
                hit_time_str=f_time,
                tide_val=row.get('潮位_cm', 150),
                tide_phase=row.get('潮位フェーズ', '---')
            )
            
            st.write("---")
    else:
        st.info("釣果データがありません。")






















































































































































































































































































