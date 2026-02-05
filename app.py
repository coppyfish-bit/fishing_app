import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime, timedelta
import requests
import math

# --- 1. 各種関数 (GPS変換・気象・潮汐) ---
def get_geotagging(exif):
    if not exif: return None
    geotagging = {}
    for tag, value in exif.items():
        decoded = TAGS.get(tag, tag)
        if decoded == "GPSInfo":
            for t in value:
                sub_decoded = GPSTAGS.get(t, t)
                geotagging[sub_decoded] = value[t]
    return geotagging

def get_decimal_from_dms(dms, ref):
    degrees = dms[0]
    minutes = dms[1] / 60.0
    seconds = dms[2] / 3600.0
    if ref in ['S', 'W']:
        degrees = -degrees
        minutes = -minutes
        seconds = -seconds
    return round(degrees + minutes + seconds, 6)

def get_coordinates(geotags):
    try:
        lat = get_decimal_from_dms(geotags['GPSLatitude'], geotags['GPSLatitudeRef'])
        lon = get_decimal_from_dms(geotags['GPSLongitude'], geotags['GPSLongitudeRef'])
        return lat, lon
    except:
        return None, None
    
def get_weather_data(lat, lon, dt):
    try:
        start_date = (dt - timedelta(days=2)).strftime('%Y-%m-%d')
        end_date = dt.strftime('%Y-%m-%d')
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": lat, "longitude": lon,
            "start_date": start_date, "end_date": end_date,
            # wind_direction_10m を追加
            "hourly": "temperature_2m,windspeed_10m,wind_direction_10m,precipitation",
            "timezone": "Asia/Tokyo"
        }
        response = requests.get(url, params=params)
        data = response.json()

        # データが空っぽでないかチェック
        if "hourly" not in data:
            return "", "", "", "" # 戻り値を4つに増やす

        idx = (len(data['hourly']['temperature_2m']) - 25) + dt.hour
        idx = max(0, min(idx, len(data['hourly']['temperature_2m']) - 1))
        
        temp = data['hourly']['temperature_2m'][idx]
        wind_s = data['hourly']['windspeed_10m'][idx]
        
        # --- 風向きの取得と変換を追加 ---
        wind_deg = data['hourly'].get('wind_direction_10m', [0])[idx]
        wind_dir = get_wind_direction(wind_deg) # 方位文字列に変換
        # -----------------------------

        precip_list = data['hourly']['precipitation'][:idx+1]
        precip_48h = sum(precip_list[-48:])
        
        # 風向き(wind_dir)を含めた4つの値を返す
        return temp, wind_s, round(precip_48h, 1), wind_dir
    except Exception as e:
        return "", "", "", ""
        
def get_wind_direction(degrees):
    """度数を16方位の文字列に変換"""
    directions = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", 
                  "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
    idx = int((degrees + 11.25) / 22.5) % 16
    return directions[idx]

def get_tide_details(dt):
    # (月齢計算などはそのまま)
    base_new_moon = datetime(2023, 1, 22, 5, 53) 
    lunar_cycle = 29.530588
    diff_days = (dt - base_new_moon).total_seconds() / 86400
    moon_age = round(diff_days % lunar_cycle, 1)
    
    # 潮位サイクルの計算 (12.42時間周期 / 片道6.21時間)
    hour_cycle = (dt.hour + dt.minute/60) % 12.42
    
    # 10段階判定ロジック
    if hour_cycle < 0.62:
        phase = "満潮"
    elif hour_cycle < 5.59:
        # 下げを9分割 (1〜9)
        num = int((hour_cycle / 6.21) * 10)
        phase = f"下げ{num}分"
    elif hour_cycle < 6.83:
        phase = "干潮"
    elif hour_cycle < 11.8:
        # 上げを9分割 (1〜9)
        # 上げは 6.21〜12.42時間の間なので、そこからの経過分を計算
        num = int(((hour_cycle - 6.21) / 6.21) * 10)
        phase = f"上げ{num}分"
    else:
        phase = "満潮"
    
    # (潮位cm計算と干満時刻算出はそのまま)
    tide_cm = int(100 + 80 * math.cos(math.pi * (hour_cycle / 6.21)))
    prev_h_tide = (dt - timedelta(hours=hour_cycle)).strftime("%H:%M")
    prev_l_tide = (dt - timedelta(hours=(hour_cycle-6.21 if hour_cycle>6.21 else hour_cycle+6.21))).strftime("%H:%M")

    return {
        "潮位_cm": tide_cm,
        "月齢": moon_age,
        "潮位フェーズ": phase,
        "直前の満潮_時刻": prev_h_tide,
        "直前の干潮_時刻": prev_l_tide,
        "次の満潮まで_分": int((12.42 - hour_cycle) * 60),
        "次の干潮まで_分": int((6.21 - hour_cycle) * 60 if hour_cycle < 6.21 else (18.63 - hour_cycle) * 60)
    }
    
    # 潮位(cm)のシミュレーション
    tide_cm = int(100 + 80 * math.cos(math.pi * (hour_cycle / 6.21)))
    
    # 干満時刻の算出（簡易）
    prev_h_tide = (dt - timedelta(hours=hour_cycle)).strftime("%H:%M")
    prev_l_tide = (dt - timedelta(hours=(hour_cycle-6.21 if hour_cycle>6.21 else hour_cycle+6.21))).strftime("%H:%M")

    return {
        "潮位_cm": tide_cm,
        "月齢": moon_age,
        "潮位フェーズ": phase,
        "直前の満潮_時刻": prev_h_tide,
        "直前の干潮_時刻": prev_l_tide,
        "次の満潮まで_分": int((12.42 - hour_cycle) * 60),
        "次の干潮まで_分": int((6.21 - hour_cycle) * 60 if hour_cycle < 6.21 else (18.63 - hour_cycle) * 60)
    }

def get_tide_name(dt):
    base_date = datetime(2023, 1, 22)
    diff = (dt - base_date).days % 30
    tide_map = {0:"大潮", 1:"大潮", 14:"大潮", 15:"大潮", 29:"大潮",
                2:"中潮", 3:"中潮", 4:"中潮", 16:"中潮", 17:"中潮", 18:"中潮",
                5:"小潮", 6:"小潮", 7:"小潮", 19:"小潮", 20:"小潮", 21:"小潮",
                8:"長潮", 22:"長潮", 9:"若潮", 23:"若潮"}
    return tide_map.get(diff, "中潮")

# --- 2. 初期設定とデータ読み込み ---
st.set_page_config(page_title="Pro Fishing Log", layout="wide")
st.title("🎣 全自動GPSログ ＆ 釣り場マスター")

default_dt = datetime.now()
auto_lat, auto_lon = 35.0, 135.0

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    df = conn.read(spreadsheet=url, ttl="5m")
    m_df = conn.read(spreadsheet=url, worksheet="place_master", ttl="10m")
    place_options = sorted(m_df["place_name"].unique().tolist())
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# --- 3. 新規地点のマスター登録機能 ---
with st.expander("📍 新しい釣り場をマスターに事前登録"):
    with st.form("master_form"):
        new_place = st.text_input("釣り場名 (例: 志賀島 沖堤防)")
        col1, col2 = st.columns(2)
        with col1:
            m_lat = st.number_input("緯度", value=33.6, format="%.6f")
        with col2:
            m_lon = st.number_input("経度", value=130.4, format="%.6f")
        
        if st.form_submit_button("マスターに保存"):
            if new_place and new_place not in m_df["place_name"].values:
                new_row = pd.DataFrame([{"place_name": new_place, "latitude": m_lat, "longitude": m_lon}])
                updated_m_df = pd.concat([m_df, new_row], ignore_index=True)
                conn.update(spreadsheet=url, worksheet="place_master", data=updated_m_df)
                st.success(f"✅ 「{new_place}」を登録しました。プルダウンから選択可能になります。")
                st.cache_data.clear()
                st.rerun()

st.write("---")

# --- 4. 写真解析セクション ---
uploaded_file = st.file_uploader("📸 写真をアップロード（位置・日時を自動取得）", type=['jpg', 'jpeg'])

if uploaded_file:
    img = Image.open(uploaded_file)
    exif = img._getexif()
    if exif:
        for tag_id, value in exif.items():
            if TAGS.get(tag_id) == 'DateTimeOriginal':
                default_dt = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
        geotags = get_geotagging(exif)
        if geotags:
            lat, lon = get_coordinates(geotags)
            if lat and lon:
                auto_lat, auto_lon = lat, lon
                st.success(f"🎯 写真から位置( {auto_lat}, {auto_lon} )と日時を読み込みました！")

# --- 5. 釣果入力フォーム ---
with st.form("fishing_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    with c1:
        date_in = st.date_input("📅 日付", value=default_dt.date())
        time_in = st.time_input("⏰ 時刻", value=default_dt.time())
    with c2:
        # 写真から取得した値を初期値にするが、手動調整も可能
        lat_in = st.number_input("緯度", value=auto_lat, format="%.6f")
        lon_in = st.number_input("経度", value=auto_lon, format="%.6f")
    
    # 既存マスターから選ぶか、手動で場所名を入力するか
    place_selected = st.selectbox("📍 登録済み釣り場から選択", options=["-- 手動入力 --"] + place_options)
    place_manual = st.text_input("📍 新しい場所名（直接入力）", placeholder="写真の場所名を入力")
    
    final_place_name = place_selected if place_selected != "-- 手動入力 --" else place_manual
    
    fish_in = st.text_input("🐟 魚種", placeholder="シーバス")
    length_in = st.slider("📏 全長 (cm)", 0.0, 150.0, 40.0)
    lure_in = st.text_input("🎣 ルアー")
    memo_in = st.text_area("📝 備考")
    
    submit = st.form_submit_button("🚀 気象・潮汐を自動取得して保存")

# --- 6. 保存処理 ---
if submit:
    with st.spinner('気象と潮汐を解析中...'):
        target_dt = datetime.combine(date_in, time_in)
        
        # 1. 気象（既存）
        temp, wind_s, precip = get_weather_data(lat_in, lon_in, target_dt)
        
        # 2. 潮名（既存）
        tide_name = get_tide_name(target_dt)
        
        # 3. ★詳細潮汐（今回追加）
        tide_info = get_tide_details(target_dt)
        
        # 4. 全データの統合マッピング
        save_data = {
            "filename": uploaded_file.name if uploaded_file else "",
            "datetime": target_dt.strftime('%Y-%m-%d %H:%M'),
            "date": date_in.strftime('%Y-%m-%d'),
            "time": time_in.strftime('%H:%M'),
            "lat": lat_in,
            "lon": lon_in,
            "気温": temp,
            "風速": wind_s,
            "降水量": precip,
            "潮名": tide_name,
            "潮位_cm": tide_info["潮位_cm"],
            "月齢": tide_info["月齢"],
            "潮位フェーズ": tide_info["潮位フェーズ"],
            "直前の満潮_時刻": tide_info["直前の満潮_時刻"],
            "直前の干潮_時刻": tide_info["直前の干潮_時刻"],
            "次の満潮まで_分": tide_info["次の満潮まで_分"],
            "次の干潮まで_分": tide_info["次の干潮まで_分"],
            "場所": final_place_name,
            "魚種": fish_in,
            "全長_cm": length_in,
            "ルアー": lure_in,
            "備考": memo_in
        }
        
        # 5. スプレッドシート更新（既存）
        new_df = pd.concat([df, pd.DataFrame([save_data])], ignore_index=True)
        conn.update(spreadsheet=url, data=new_df)
        st.success(f"✅ 保存完了！当時の潮は {tide_name} ({tide_info['潮位フェーズ']}) でした。")
        st.cache_data.clear()
        st.rerun()







