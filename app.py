import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime, timedelta
import requests

# --- 1. 座標変換・取得関数 ---

def get_geotagging(exif):
    """EXIFからGPS情報を辞書形式で抽出"""
    if not exif:
        return None
    geotagging = {}
    for tag, value in exif.items():
        decoded = TAGS.get(tag, tag)
        if decoded == "GPSInfo":
            for t in value:
                sub_decoded = GPSTAGS.get(t, t)
                geotagging[sub_decoded] = value[t]
    return geotagging

def get_decimal_from_dms(dms, ref):
    """度分秒形式を10進数に変換"""
    degrees = dms[0]
    minutes = dms[1] / 60.0
    seconds = dms[2] / 3600.0
    if ref in ['S', 'W']:
        degrees = -degrees
        minutes = -minutes
        seconds = -seconds
    return round(degrees + minutes + seconds, 6)

def get_coordinates(geotags):
    """緯度と経度の10進数を取得"""
    try:
        lat = get_decimal_from_dms(geotags['GPSLatitude'], geotags['GPSLatitudeRef'])
        lon = get_decimal_from_dms(geotags['GPSLongitude'], geotags['GPSLongitudeRef'])
        return lat, lon
    except:
        return None, None

# --- 2. 気象・潮汐関数 (以前のものを流用) ---

def get_weather_data(lat, lon, dt):
    try:
        start_date = (dt - timedelta(days=2)).strftime('%Y-%m-%d')
        end_date = dt.strftime('%Y-%m-%d')
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": lat, "longitude": lon,
            "start_date": start_date, "end_date": end_date,
            "hourly": "temperature_2m,windspeed_10m,precipitation",
            "timezone": "Asia/Tokyo"
        }
        data = requests.get(url, params=params).json()
        idx = (len(data['hourly']['temperature_2m']) - 25) + dt.hour
        temp = data['hourly']['temperature_2m'][idx]
        wind_s = data['hourly']['windspeed_10m'][idx]
        precip_48h = sum(data['hourly']['precipitation'][:idx+1][-48:])
        return temp, wind_s, round(precip_48h, 1)
    except:
        return None, None, None

def get_tide_name(dt):
    base_date = datetime(2023, 1, 22)
    diff = (dt - base_date).days % 30
    tide_map = {0:"大潮", 1:"大潮", 14:"大潮", 15:"大潮", 29:"大潮",
                2:"中潮", 3:"中潮", 4:"中潮", 16:"中潮", 17:"中潮", 18:"中潮",
                5:"小潮", 6:"小潮", 7:"小潮", 19:"小潮", 20:"小潮", 21:"小潮",
                8:"長潮", 22:"長潮", 9:"若潮", 23:"若潮"}
    return tide_map.get(diff, "中潮")

# --- 3. アプリメイン処理 ---

st.set_page_config(page_title="Fishing GPS App", layout="wide")
st.title("🎣 GPS・気象・潮汐 全自動ログ")

# 初期値
default_dt = datetime.now()
auto_lat, auto_lon = 35.0, 135.0

# データの読み込み
conn = st.connection("gsheets", type=GSheetsConnection)
url = st.secrets["connections"]["gsheets"]["spreadsheet"]
df = conn.read(spreadsheet=url, ttl="5m")
m_df = conn.read(spreadsheet=url, worksheet="place_master", ttl="10m")

# --- 4. 写真解析セクション ---
uploaded_file = st.file_uploader("📸 写真をアップロード（位置・日時を自動取得）", type=['jpg', 'jpeg'])

if uploaded_file:
    img = Image.open(uploaded_file)
    exif = img._getexif()
    if exif:
        # 日時の自動取得
        for tag_id, value in exif.items():
            if TAGS.get(tag_id) == 'DateTimeOriginal':
                default_dt = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
        
        # GPSの自動取得
        geotags = get_geotagging(exif)
        if geotags:
            lat, lon = get_coordinates(geotags)
            if lat and lon:
                auto_lat, auto_lon = lat, lon
                st.success(f"📍 位置を特定しました: {auto_lat}, {auto_lon}")
                st.info(f"⏰ 日時を特定しました: {default_dt}")

# --- 5. 入力フォーム ---
with st.form("fishing_form"):
    c1, c2 = st.columns(2)
    with c1:
        date_in = st.date_input("📅 日付", value=default_dt.date())
        time_in = st.time_input("⏰ 時刻", value=default_dt.time())
    with c2:
        lat_in = st.number_input("Lat (緯度)", value=auto_lat, format="%.6f")
        lon_in = st.number_input("Lon (経度)", value=auto_lon, format="%.6f")
    
    place_name = st.text_input("📍 場所名（未入力でも保存可）", placeholder="〇〇突堤")
    fish_in = st.text_input("🐟 魚種")
    length_in = st.slider("📏 全長 (cm)", 0.0, 150.0, 40.0)
    lure_in = st.text_input("🎣 ルアー")
    memo_in = st.text_area("📝 備考")
    
    submit = st.form_submit_button("🚀 データを解析して保存")

# --- 6. 保存処理 ---
if submit:
    with st.spinner('解析中...'):
        target_dt = datetime.combine(date_in, time_in)
        temp, wind_s, precip = get_weather_data(lat_in, lon_in, target_dt)
        tide = get_tide_name(target_dt)
        
        save_data = {
            "filename": uploaded_file.name if uploaded_file else "",
            "datetime": target_dt.strftime('%Y-%m-%d %H:%M'),
            "date": date_in.strftime('%Y-%m-%d'),
            "time": time_in.strftime('%H:%M'),
            "lat": lat_in,
            "lon": lon_in,
            "気温": temp, "風速": wind_s, "降水量": precip, "潮名": tide,
            "場所": place_name, "魚種": fish_in, "全長_cm": length_in,
            "ルアー": lure_in, "備考": memo_in
        }
        
        new_df = pd.concat([df, pd.DataFrame([save_data])], ignore_index=True)
        conn.update(spreadsheet=url, data=new_df)
        st.success(f"✅ 保存完了！当時の潮は「{tide}」、気温は「{temp}℃」でした。")
        st.cache_data.clear()
