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

# 気象庁から潮位(cm)を取得・計算
def get_tide_details(station_code, dt):
    try:
        year = dt.year
        url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{year}/{station_code}.txt"
        
        # --- ここからデバッグ ---
        st.info(f"🔍 アクセス中: {url}")
        res = requests.get(url, timeout=10)
        st.write(f"📡 ステータスコード: {res.status_code}")
        
        if res.status_code != 200:
            st.error("❌ URLにアクセスできませんでした")
            return None
        
        lines = res.text.splitlines()
        st.write(f"📝 全行数: {len(lines)} 行取得")
        
        target_day = str(dt.day)
        st.write(f"📅 探している日: {target_day}日, 地点: {station_code}")
        
        day_data = None
        for i, line in enumerate(lines):
            # 実際のデータの「日」と「コード」の場所を無理やり表示
            if i < 5: # 最初の5行だけサンプル表示
                st.write(f"行サンプル[{i}]: 日='{line[72:74]}' コード='{line[78:80]}'")
            
            if len(line) < 80: continue
            if line[72:74].strip() == target_day and line[78:80] == station_code:
                day_data = line
                st.success(f"🎯 該当行を発見しました！")
                break
        
        if not day_data:
            st.warning("⚠️ 該当する日のデータ行が見つかりませんでした")
            return None
except Exception as e: # ← ここが抜けているか、インデントがズレています
        st.error(f"潮位解析エラー: {e}")
        return None
# 【修正】Open-Meteoを使用した過去48時間降水量対応の気象取得関数
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

# --- 3. 以降、初期設定・画像アップロード・入力画面は既存と同じ ---
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
                with st.spinner("📊 気象・潮位データを取得中..."):
                    now = datetime.now()
                    
                    # 1. 気象・月齢
                    m_age = get_moon_age(now)
                    t_name = get_tide_name(m_age)
                    temp, wind_s, wind_d, rain_48 = get_weather_data_openmeteo(st.session_state.lat, st.session_state.lon, now)
                    
                    # 2. 潮位詳細（10段階フェーズ付き）
                    station_info = find_nearest_tide_station(st.session_state.lat, st.session_state.lon)
                    tide_data = get_tide_details(station_info['code'], now)
                    
                    # --- データの整理 ---
                    if tide_data:
                        tide_cm = tide_data['cm']
                        tide_phase = tide_data['phase']
                        # 満潮時刻と干潮時刻を分けて文字列にする
                        high_tides = [e['time'].strftime('%H:%M') for e in tide_data['events'] if e['type'] == '満潮']
                        low_tides = [e['time'].strftime('%H:%M') for e in tide_data['events'] if e['type'] == '干潮']
                        high_str = ", ".join(high_tides)
                        low_str = ", ".join(low_tides)
                    else:
                        tide_cm = 0
                        tide_phase = "不明"
                        high_str = ""
                        low_str = ""

                    # (マスター登録ロジックとCloudinaryアップロードはそのまま維持)
                    if force_new or (st.session_state.detected_place == "新規地点"):
                        # ...既存のマスター登録ロジック...
                        if not df_master.empty and place_name in df_master['place_name'].values:
                            target_group_id = df_master[df_master['place_name'] == place_name]['group_id'].values[0]
                        else:
                            new_gid = int(df_master['group_id'].max()) + 1 if not df_master.empty else 0
                            new_place_df = pd.DataFrame([{"group_id": new_gid, "place_name": place_name, "latitude": st.session_state.lat, "longitude": st.session_state.lon}])
                            conn.update(spreadsheet=url, worksheet="place_master", data=pd.concat([df_master, new_place_df], ignore_index=True))
                            target_group_id = new_gid

                    uploaded_file.seek(0)
                    res = cloudinary.uploader.upload(uploaded_file, folder="fishing_app")
                    
                    # --- 修正された save_data ---
                    save_data = {
                        "filename": res.get("secure_url"), "datetime": now.strftime("%Y-%m-%d %H:%M"),
                        "date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M"),
                        "lat": float(st.session_state.lat), "lon": float(st.session_state.lon),
                        "気温": temp if temp else 0,
                        "風速": wind_s if wind_s else 0,
                        "風向": wind_d,
                        "降水量": rain_48, 
                        "潮位_cm": tide_cm,           # 修正: tide_data['cm'] を反映
                        "月齢": m_age, 
                        "潮名": t_name, 
                        "次の満潮まで_分": 0,           # (必要に応じて計算)
                        "次の干潮まで_分": 0,           # (必要に応じて計算)
                        "直前の満潮_時刻": high_str,    # 修正: 今日の満潮リストを反映
                        "直前の干潮_時刻": low_str,     # 修正: 今日の干潮リストを反映
                        "潮位フェーズ": tide_phase,    # 修正: 「上げ3分」などを反映
                        "場所": place_name, 
                        "魚種": final_fish_name,
                        "全長_cm": float(st.session_state.length_val), 
                        "ルアー": lure,
                        "備考": memo, 
                        "group_id": target_group_id, 
                        "観測所": station_info['name'], # 修正: 観測所名を反映
                        "釣り人": angler
                    }

                    df_main = conn.read(spreadsheet=url, ttl=0)
                    cols = ["filename","datetime","date","time","lat","lon","気温","風速","風向","降水量","潮位_cm","月齢","潮名","次の満潮まで_分","次の干潮まで_分","直前の満潮_時刻","直前の干潮_時刻","潮位フェーズ","場所","魚種","全長_cm","ルアー","備考","group_id","観測所","釣り人"]
                    new_row_df = pd.DataFrame([save_data])[cols]
                    conn.update(spreadsheet=url, data=pd.concat([df_main, new_row_df], ignore_index=True))
                    
                    st.success(f"🎉 記録完了！ (48h降水: {rain_48}mm)")
                    st.balloons()
                    st.session_state.data_ready = False
                    st.session_state.length_val = 0.0
                    time.sleep(2); st.rerun()
            except Exception as e:
                st.error(f"❌ 保存失敗: {e}")









