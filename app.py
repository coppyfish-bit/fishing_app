import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime, timedelta
import requests
import math

# --- 1. 各種関数定義 ---

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

# --- 1. 風向を漢字に変換する関数 ---
def get_wind_direction(deg):
    if deg is None: return ""
    # 360度を16方位（22.5度刻み）で割る
    directions = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", 
                  "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
    idx = int((deg + 11.25) / 22.5) % 16
    return directions[idx]

# --- 2. 気象データ取得関数（風向対応版） ---
def get_weather_data(lat, lon, dt):
    try:
        start_date = (dt - timedelta(days=2)).strftime('%Y-%m-%d')
        end_date = dt.strftime('%Y-%m-%d')
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": float(lat),
            "longitude": float(lon),
            "start_date": start_date,
            "end_date": end_date,
            # winddirection_10m を追加
            "hourly": "temperature_2m,windspeed_10m,winddirection_10m,precipitation",
            "timezone": "Asia/Tokyo"
        }
        res = requests.get(url, params=params, timeout=10).json()
        
        if "hourly" not in res: return None, None, None, None

        target_hour_idx = ((dt.date() - (dt - timedelta(days=2)).date()).days * 24) + dt.hour
        target_hour_idx = max(0, min(target_hour_idx, len(res['hourly']['temperature_2m']) - 1))
        
        temp = res['hourly']['temperature_2m'][target_hour_idx]
        wind_s = res['hourly']['windspeed_10m'][target_hour_idx]
        wind_d_deg = res['hourly']['winddirection_10m'][target_hour_idx] # 角度
        wind_d_str = get_wind_direction(wind_d_deg) # 漢字に変換
        
        precip_list = res['hourly']['precipitation'][:target_hour_idx+1]
        precip_48h = sum(precip_list[-48:])
        
        return temp, wind_s, wind_d_str, round(precip_48h, 1)
    except:
        return None, None, None, None

def get_tide_name(dt):
    base_date = datetime(2023, 1, 22)
    diff = (dt - base_date).days % 30
    tide_map = {0:"大潮", 1:"大潮", 14:"大潮", 15:"大潮", 29:"大潮",
                2:"中潮", 3:"中潮", 4:"中潮", 16:"中潮", 17:"中潮", 18:"中潮",
                5:"小潮", 6:"小潮", 7:"小潮", 19:"小潮", 20:"小潮", 21:"小潮",
                8:"長潮", 22:"長潮", 9:"若潮", 23:"若潮"}
    return tide_map.get(diff, "中潮")

# --- 3. 潮汐詳細（10段階表示） ---
def get_tide_details(dt):
    base_new_moon = datetime(2023, 1, 22, 5, 53) 
    lunar_cycle = 29.530588
    diff_days = (dt - base_new_moon).total_seconds() / 86400
    moon_age = round(diff_days % lunar_cycle, 1)
    
    # 満潮から次の満潮まで約12.42時間、半分で6.21時間
    hour_cycle = (dt.hour + dt.minute/60) % 12.42
    
    # 6.21時間を10分割して判定
    step = 6.21 / 10
    if hour_cycle < 6.21:
        s = int(hour_cycle / step)
        phase = f"下げ{s}分" if 0 < s < 10 else ("満潮" if s==0 else "干潮")
    else:
        s = int((hour_cycle - 6.21) / step)
        phase = f"上げ{s}分" if 0 < s < 10 else ("干潮" if s==0 else "満潮")
    
    # ...（潮位計算などは前回同様）
    return {"潮位_cm": int(100 + 80 * math.cos(math.pi * (hour_cycle / 6.21))), 
            "月齢": moon_age, "潮位フェーズ": phase}
    
    tide_cm = int(100 + 80 * math.cos(math.pi * (hour_cycle / 6.21)))
    return {
        "潮位_cm": tide_cm,
        "月齢": moon_age,
        "潮位フェーズ": phase,
        "直前の満潮_時刻": (dt - timedelta(hours=hour_cycle)).strftime("%H:%M"),
        "直前の干潮_時刻": (dt - timedelta(hours=(hour_cycle-6.21 if hour_cycle>6.21 else hour_cycle+6.21))).strftime("%H:%M"),
        "次の満潮まで_分": int((12.42 - hour_cycle) * 60),
        "次の干潮まで_分": int((6.21 - hour_cycle) * 60 if hour_cycle < 6.21 else (18.63 - hour_cycle) * 60)
    }

# --- 2. Streamlit UI部 ---

st.set_page_config(page_title="Fishing AI Log", layout="wide")
st.title("🎣 GPS・気象・潮汐 統合ログシステム")

default_dt = datetime.now()
auto_lat, auto_lon = 35.0, 135.0

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    df = conn.read(spreadsheet=url, ttl="5m")
    m_df = conn.read(spreadsheet=url, worksheet="place_master", ttl="10m")
    place_options = sorted(m_df["place_name"].unique().tolist())
except:
    st.error("スプレッドシートへの接続に失敗しました。")
    st.stop()

# 写真解析
uploaded_file = st.file_uploader("📸 写真を選択", type=['jpg', 'jpeg'])
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
            if lat: auto_lat, auto_lon = lat, lon
            st.success(f"📍 GPS/日時を取得しました")

# 入力フォーム
with st.form("main_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    with c1:
        date_in = st.date_input("日付", value=default_dt.date())
        time_in = st.time_input("時刻", value=default_dt.time())
    with c2:
        lat_in = st.number_input("緯度", value=auto_lat, format="%.6f")
        lon_in = st.number_input("経度", value=auto_lon, format="%.6f")
    
    place_name = st.text_input("場所名", value="")
    fish_in = st.text_input("魚種")
    length_in = st.slider("全長(cm)", 0.0, 150.0, 40.0)
    lure_in = st.text_input("ルアー")
    memo_in = st.text_area("備考")
    
    submit = st.form_submit_button("🚀 気象と潮汐を解析して保存")

# --- 6. 保存処理 ---
if submit:
    with st.spinner('気象と潮汐を解析中...'):
        target_dt = datetime.combine(date_in, time_in)
        
        # 1. 気象データを取得 (戻り値が4つ [気温, 風速, 風向, 降水] になっています)
        weather_res = get_weather_data(lat_in, lon_in, target_dt)
        
        # もしデータが取れなかった場合でも、空の値(None)で埋めてエラーを防ぐ
        if weather_res:
            temp, wind_s, wind_d, precip = weather_res
        else:
            temp, wind_s, wind_d, precip = None, None, None, None
        
        # 2. 潮汐データの取得
        tide_name = get_tide_name(target_dt)
        tide_info = get_tide_details(target_dt)
        
# --- 3. 保存処理 (if submit: の中) ---

if submit:
    with st.spinner('解析中...'):
        target_dt = datetime.combine(date_in, time_in)
        
        # 気象データの取得
        weather_data = get_weather_data(lat_in, lon_in, target_dt)
        temp, wind_s, precip = weather_data if weather_data else (None, None, None)
        
        # 潮汐データの取得
        tide_name = get_tide_name(target_dt)
        tide_info = get_tide_details(target_dt)
        
        # tide_info["キー"] ではなく tide_info.get("キー") を使うことでエラーを回避
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
            "潮位_cm": tide_info.get("潮位_cm"),
            "月齢": tide_info.get("月齢"),
            "潮位フェーズ": tide_info.get("潮位フェーズ"),
            "直前の満潮_時刻": tide_info.get("直前の満潮_時刻"),
            "直前の干潮_時刻": tide_info.get("直前の干潮_時刻"),
            "次の満潮まで_分": tide_info.get("次の満潮まで_分"),
            "次の干潮まで_分": tide_info.get("次の干潮まで_分"),
            "場所": place_name,
            "魚種": fish_in,
            "全長_cm": length_in,
            "ルアー": lure_in,
            "備考": memo_in
        }
        
        # 保存実行
        new_df = pd.concat([df, pd.DataFrame([save_data])], ignore_index=True)
        conn.update(spreadsheet=url, data=new_df)
        st.success("✅ 全てのデータを正常に保存しました！")
        st.cache_data.clear()
        st.rerun()



