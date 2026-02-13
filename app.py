import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from datetime import datetime
import cloudinary
import cloudinary.uploader
import unicodedata
import io
import numpy as np
import ephem
import requests # 天気取得用に追加

# --- 1. 設定 ---
try:
    cloudinary.config(
        cloud_name = st.secrets["cloudinary"]["cloud_name"],
        api_key = st.secrets["cloudinary"]["api_key"],
        api_secret = st.secrets["cloudinary"]["api_secret"],
        secure = True
    )
    OWM_API_KEY = st.secrets["openweathermap"]["api_key"]
except Exception as e:
    st.error("設定（Cloudinary/OpenWeatherMap）を確認してください。")

# --- 2. 関数定義 ---
# (既存の関数 get_geotagging, get_decimal_from_dms, normalize_float, find_nearest_place, get_moon_age, get_tide_name はそのまま)

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

# 【追加】天気取得関数
def get_weather(lat, lon):
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OWM_API_KEY}&units=metric&lang=ja"
        res = requests.get(url).json()
        
        # 風向きを16方位の文字列に変換
        def get_wind_dir(deg):
            dirs = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
            return dirs[int((deg + 11.25) / 22.5) % 16]

        weather_info = {
            "temp": res["main"]["temp"],
            "wind_speed": res["wind"]["speed"],
            "wind_dir": get_wind_dir(res["wind"]["deg"]),
            "rain": res.get("rain", {}).get("1h", 0) # 過去1時間の降水量（なければ0）
        }
        return weather_info
    except:
        return {"temp": 0, "wind_speed": 0, "wind_dir": "不明", "rain": 0}

# --- 3. 初期設定とセッション状態 ---
st.set_page_config(page_title="釣果記録アプリ", layout="centered")
st.title("🎣 釣果記録システム")

if "data_ready" not in st.session_state: st.session_state.data_ready = False
if "lat" not in st.session_state: st.session_state.lat = 0.0
if "lon" not in st.session_state: st.session_state.lon = 0.0
if "length_val" not in st.session_state: st.session_state.length_val = 0.0
if "detected_place" not in st.session_state: st.session_state.detected_place = "新規地点"
if "group_id" not in st.session_state: st.session_state.group_id = "default"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    df_master = conn.read(spreadsheet=url, worksheet="place_master")
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# --- 4. 画像アップロード ---
uploaded_file = st.file_uploader("📸 釣果写真をアップロード", type=["jpg", "jpeg"])

if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, use_container_width=True)
    if not st.session_state.data_ready:
        exif = img._getexif()
        geo = get_geotagging(exif)
        if geo:
            lat = get_decimal_from_dms(geo['GPSLatitude'], geo['GPSLatitudeRef'])
            lon = get_decimal_from_dms(geo['GPSLongitude'], geo['GPSLongitudeRef'])
            if lat and lon:
                st.session_state.lat, st.session_state.lon = lat, lon
                place, gid = find_nearest_place(lat, lon, df_master)
                st.session_state.detected_place, st.session_state.group_id = place, gid
                st.session_state.data_ready = True
        else:
            st.warning("⚠️ GPSが見つかりません。")
            st.session_state.data_ready = True

# --- 5. 入力セクション ---
if st.session_state.data_ready:
    with st.expander("📍 位置情報の確認", expanded=True):
        if st.session_state.lat != 0.0:
            st.map(pd.DataFrame({'lat': [st.session_state.lat], 'lon': [st.session_state.lon]}), zoom=14)
    
    st.subheader("📝 釣果の詳細")
    fish_options = ["スズキ", "ヒラスズキ", "ボウズ", "タチウオ", "ターポン", "カサゴ", "メバル", "マダイ", "チヌ", "キビレ", "ブリ", "アジ", "（手入力）"]
    selected_fish = st.selectbox("🐟 魚種を選択", fish_options)
    final_fish_name = st.text_input("魚種名を入力") if selected_fish == "（手入力）" else selected_fish

    st.markdown("---")
    st.write("📏 全長 (cm)")
    c1, c2, c3 = st.columns([1, 2, 1])
    if c1.button("➖ 0.5", use_container_width=True):
        st.session_state.length_val = max(0.0, st.session_state.length_val - 0.5); st.rerun()
    length_text = c2.text_input("全長入力", value=str(st.session_state.length_val) if st.session_state.length_val > 0 else "", placeholder="ここに全長を入力", label_visibility="collapsed")
    st.session_state.length_val = normalize_float(length_text)
    if c3.button("➕ 0.5", use_container_width=True):
        st.session_state.length_val += 0.5; st.rerun()

    st.markdown("---")
    force_new = st.checkbox("🆕 新しい場所として登録する")
    if force_new:
        place_name = st.text_input("📍 新しい場所名を入力してください", value="")
        target_group_id = "default"
    else:
        place_name = st.text_input("📍 場所名", value=st.session_state.detected_place)
        target_group_id = st.session_state.group_id

    lure = st.text_input("🪝 ルアー/仕掛け")
    angler = st.selectbox("👤 釣り人", ["長元", "川口", "山川"])
    memo = st.text_area("🗒️ 備考")

    if st.button("🚀 釣果を記録する", use_container_width=True, type="primary"):
        if place_name == "" or place_name == "新規地点":
            st.error("⚠️ 場所名を入力してください。")
        else:
            try:
                with st.spinner("📊 保存中..."):
                    now = datetime.now()
                    
                    # --- 月齢/潮名/天気を取得 ---
                    m_age = get_moon_age(now)
                    t_name = get_tide_name(m_age)
                    w_info = get_weather(st.session_state.lat, st.session_state.lon) # 【追加】

                    # マスター登録ロジック
                    if force_new or (st.session_state.detected_place == "新規地点"):
                        if not df_master.empty and place_name in df_master['place_name'].values:
                            target_group_id = df_master[df_master['place_name'] == place_name]['group_id'].values[0]
                        else:
                            new_gid = int(df_master['group_id'].max()) + 1 if not df_master.empty else 0
                            new_place_df = pd.DataFrame([{"group_id": new_gid, "place_name": place_name, "latitude": st.session_state.lat, "longitude": st.session_state.lon}])
                            conn.update(spreadsheet=url, worksheet="place_master", data=pd.concat([df_master, new_place_df], ignore_index=True))
                            target_group_id = new_gid

                    # 画像/データ保存
                    uploaded_file.seek(0)
                    res = cloudinary.uploader.upload(uploaded_file, folder="fishing_app")
                    
                    save_data = {
                        "filename": res.get("secure_url"), "datetime": now.strftime("%Y-%m-%d %H:%M"),
                        "date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M"),
                        "lat": float(st.session_state.lat), "lon": float(st.session_state.lon),
                        "気温": w_info["temp"], # 【自動化】
                        "風速": w_info["wind_speed"], # 【自動化】
                        "風向": w_info["wind_dir"], # 【自動化】
                        "降水量": w_info["rain"], # 【自動化】
                        "潮位_cm": 0, "月齢": m_age, "潮名": t_name, 
                        "次の満潮まで_分": 0, "次の干潮まで_分": 0,
                        "直前の満潮_時刻": "", "直前の干潮_時刻": "", "潮位フェーズ": "不明",
                        "場所": place_name, "魚種": final_fish_name,
                        "全長_cm": float(st.session_state.length_val), "ルアー": lure,
                        "備考": memo, "group_id": target_group_id, "観測所": "不明", "釣り人": angler
                    }

                    df_main = conn.read(spreadsheet=url, ttl=0)
                    cols = ["filename","datetime","date","time","lat","lon","気温","風速","風向","降水量","潮位_cm","月齢","潮名","次の満潮まで_分","次の干潮まで_分","直前の満潮_時刻","直前の干潮_時刻","潮位フェーズ","場所","魚種","全長_cm","ルアー","備考","group_id","観測所","釣り人"]
                    new_row_df = pd.DataFrame([save_data])[cols]
                    conn.update(spreadsheet=url, data=pd.concat([df_main, new_row_df], ignore_index=True))
                    
                    st.success(f"🎉 記録完了！ ({t_name} / {w_info['temp']}℃ / {w_info['wind_dir']}の風 {w_info['wind_speed']}m)")
                    st.balloons()
                    st.session_state.data_ready = False
                    st.session_state.length_val = 0.0
                    time.sleep(2); st.rerun()
            except Exception as e:
                st.error(f"❌ 保存失敗: {e}")
