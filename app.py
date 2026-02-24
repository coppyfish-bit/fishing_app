import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image, ExifTags
from datetime import datetime, timedelta
import cloudinary
import cloudinary.uploader
import unicodedata
import io
import numpy as np
import ephem
import requests
import streamlit.components.v1 as components

# --- 1. モジュールインポート ---
try:
    from edit_module import show_edit_page
    from gallery_module import show_gallery_page
    from analysis_module import show_analysis_page
    from monthly_stats import show_monthly_stats
    # from strategy_analysis import show_strategy_analysis # 必要に応じて有効化
except ImportError:
    st.warning("一部のカスタムモジュールが読み込めませんでした。")

# --- 2. 基本設定 ---
icon_url = "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"
st.set_page_config(page_title="Seabass Strategy App", page_icon=icon_url, layout="wide")

# --- 3. 潮位・気象用の関数 ---
TIDE_STATIONS = [
    {"name": "苓北", "lat": 32.4667, "lon": 130.0333, "code": "RH"},
    {"name": "三角", "lat": 32.6167, "lon": 130.4500, "code": "MS"},
    {"name": "本渡瀬戸", "lat": 32.4333, "lon": 130.2167, "code": "HS"},
    {"name": "八代", "lat": 32.5167, "lon": 130.5667, "code": "O5"},
    {"name": "水俣", "lat": 32.2000, "lon": 130.3667, "code": "O7"},
    {"name": "熊本", "lat": 32.7500, "lon": 130.5667, "code": "KU"},
    {"name": "大牟田", "lat": 33.0167, "lon": 130.4167, "code": "O6"},
    {"name": "大浦", "lat": 32.9833, "lon": 130.2167, "code": "OU"},
    {"name": "口之津", "lat": 32.6000, "lon": 130.2000, "code": "KT"}
]

def get_geotagging(exif):
    if not exif: return None
    gps_info = exif.get(34853)
    if not gps_info: return None
    return {'GPSLatitudeRef': gps_info.get(1), 'GPSLatitude': gps_info.get(2),
            'GPSLongitudeRef': gps_info.get(3), 'GPSLongitude': gps_info.get(4)}

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
    try: return float(unicodedata.normalize('NFKC', str(text)))
    except: return 0.0

def find_nearest_place(lat, lon, df_master):
    if lat == 0.0 or lon == 0.0 or df_master.empty: return "新規地点", "default"
    valid_master = df_master.dropna(subset=['latitude', 'longitude']).copy()
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
    return "若潮"

def find_nearest_tide_station(lat, lon):
    distances = [np.sqrt((s['lat'] - lat)**2 + (s['lon'] - lon)**2) for s in TIDE_STATIONS]
    return TIDE_STATIONS[np.argmin(distances)]

def get_tide_details(station_code, dt):
    try:
        url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{dt.year}/{station_code}.txt"
        res = requests.get(url, timeout=10)
        if res.status_code != 200: return None
        target_ymd = dt.strftime('%y%m%d')
        day_data = next((line for line in res.text.splitlines() if line[72:78] == target_ymd), None)
        if not day_data: return None
        hourly = [int(day_data[i*3:(i+1)*3].strip()) for i in range(24)]
        t1, t2 = hourly[dt.hour], hourly[dt.hour+1] if dt.hour < 23 else hourly[dt.hour]
        current_cm = int(round(t1 + (t2 - t1) * (dt.minute / 60.0)))
        events = []
        for i in range(4):
            t_h, l_h = day_data[80+(i*7):84+(i*7)].strip(), day_data[84+(i*7):87+(i*7)].strip()
            if t_h and t_h != "9999": events.append({"time": datetime.strptime(dt.strftime('%Y%m%d')+t_h.zfill(4), '%Y%m%d%H%M'), "type": "満潮"})
            t_l, l_l = day_data[108+(i*7):112+(i*7)].strip(), day_data[112+(i*7):115+(i*7)].strip()
            if t_l and t_l != "9999": events.append({"time": datetime.strptime(dt.strftime('%Y%m%d')+t_l.zfill(4), '%Y%m%d%H%M'), "type": "干潮"})
        return {"cm": current_cm, "events": events}
    except: return None

def get_weather_data_openmeteo(lat, lon, dt):
    try:
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {"latitude": lat, "longitude": lon, "start_date": (dt - timedelta(days=2)).strftime('%Y-%m-%d'), "end_date": dt.strftime('%Y-%m-%d'), "hourly": "temperature_2m,windspeed_10m,winddirection_10m,precipitation", "timezone": "Asia/Tokyo"}
        res = requests.get(url, params=params, timeout=10).json()
        h = res['hourly']
        idx = (len(h['temperature_2m']) - 25) + dt.hour
        wind_dir = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"][int((h['winddirection_10m'][idx] + 11.25) / 22.5) % 16]
        return h['temperature_2m'][idx], round(h['windspeed_10m'][idx]/3.6, 1), wind_dir, round(sum(h['precipitation'][:idx+1][-48:]), 1)
    except: return None, None, "不明", 0.0

# --- 4. 接続設定 ---
cloudinary.config(cloud_name=st.secrets["cloudinary"]["cloud_name"], api_key=st.secrets["cloudinary"]["api_key"], api_secret=st.secrets["cloudinary"]["api_secret"], secure=True)
conn = st.connection("gsheets", type=GSheetsConnection)
gs_url = st.secrets["connections"]["gsheets"]["spreadsheet"]

@st.cache_data(ttl=600)
def get_all_data(_conn, _url):
    return _conn.read(spreadsheet=_url, ttl="10m"), _conn.read(spreadsheet=_url, worksheet="place_master", ttl="1h")

df, df_master = get_all_data(conn, gs_url)

# --- 5. メイン UI ---
tabs = st.tabs(["記録", "編集", "ギャラリー", "分析", "月別統計"])
tab1, tab2, tab3, tab4, tab5 = tabs

with tab1:
    st.title("🎣 釣果記録")
    if "lat" not in st.session_state: st.session_state.lat = 0.0
    if "lon" not in st.session_state: st.session_state.lon = 0.0
    if "detected_place" not in st.session_state: st.session_state.detected_place = "新規地点"
    if "length_val" not in st.session_state: st.session_state.length_val = 0.0
    if "target_dt" not in st.session_state: st.session_state.target_dt = datetime.now()

    uploaded_file = st.file_uploader("釣果写真をアップロード", type=["jpg", "jpeg", "png", "heic"], key="unique_uploader")
    
    if uploaded_file:
        img = Image.open(uploaded_file)
        exif = img._getexif()
        if exif:
            for tag, val in exif.items():
                if ExifTags.TAGS.get(tag) == 'DateTimeOriginal':
                    try: st.session_state.target_dt = datetime.strptime(str(val).strip()[:16].replace(":", "/", 2), '%Y/%m/%d %H:%M')
                    except: pass
            geo = get_geotagging(exif)
            if geo:
                st.session_state.lat = get_decimal_from_dms(geo['GPSLatitude'], geo['GPSLatitudeRef'])
                st.session_state.lon = get_decimal_from_dms(geo['GPSLongitude'], geo['GPSLongitudeRef'])
                st.session_state.detected_place, st.session_state.group_id = find_nearest_place(st.session_state.lat, st.session_state.lon, df_master)

        st.info(f"📸 解析完了: {st.session_state.detected_place} / {st.session_state.target_dt}")

        fish_options = ["スズキ", "ヒラスズキ", "ボウズ", "バラシ", "カサゴ", "（手入力）"]
        fish = st.selectbox("🐟 魚種", fish_options)
        fish_name = st.text_input("手入力魚種") if fish == "（手入力）" else fish

        place_options = ["自動判定に従う", "（新規登録）"] + sorted(df_master['place_name'].unique().tolist())
        sel_place = st.selectbox("📍 場所修正", place_options)
        final_place = st.text_input("場所名確定", value=st.session_state.detected_place) if sel_place == "自動判定に従う" else (st.text_input("新規場所") if sel_place == "（新規登録）" else sel_place)

        c1, c2, c3 = st.columns([1, 2, 1])
        if c1.button("➖"): st.session_state.length_val -= 0.5
        len_in = c2.text_input("全長(cm)", value=str(st.session_state.length_val))
        st.session_state.length_val = normalize_float(len_in)
        if c3.button("➕"): st.session_state.length_val += 0.5

        lure = st.text_input("🪝 ルアー")
        angler = st.selectbox("👤 釣り人", ["長元", "川口", "山川"])
        memo = st.text_area("🗒️ 備考")

        if st.button("🚀 記録する", type="primary", use_container_width=True):
            with st.spinner("データ取得中..."):
                t_dt = st.session_state.target_dt
                temp, w_s, w_d, r_48 = get_weather_data_openmeteo(st.session_state.lat, st.session_state.lon, t_dt)
                m_age = get_moon_age(t_dt)
                station = find_nearest_tide_station(st.session_state.lat, st.session_state.lon)
                
                # 前後3日分の潮汐イベントをマージしてフェーズ判定
                all_evs = []
                t_cm = 0
                for d in [-1, 0, 1]:
                    res = get_tide_details(station['code'], t_dt + timedelta(days=d))
                    if res:
                        all_evs.extend(res['events'])
                        if d == 0: t_cm = res['cm']
                
                all_evs = sorted(all_evs, key=lambda x: x['time'])
                prev_ev = next((e for e in reversed(all_evs) if e['time'] <= t_dt), None)
                next_ev = next((e for e in all_evs if e['time'] > t_dt), None)
                phase = "不明"
                if prev_ev and next_ev:
                    step = max(1, min(9, int(((t_dt - prev_ev['time']).total_seconds() / (next_ev['time'] - prev_ev['time']).total_seconds()) * 10)))
                    phase = f"{'上げ' if prev_ev['type'] == '干潮' else '下げ'}{step}分"

                # 画像アップ
                img_io = io.BytesIO()
                img.convert('RGB').save(img_io, format='JPEG', quality=70)
                img_io.seek(0)
                res_c = cloudinary.uploader.upload(img_io, folder="fishing_app")

                new_row = {
                    "filename": res_c["secure_url"], "datetime": t_dt.strftime("%Y/%m/%d %H:%M"),
                    "lat": st.session_state.lat, "lon": st.session_state.lon, "気温": temp, "風速": w_s,
                    "風向": w_d, "降水量": r_48, "潮位_cm": t_cm, "月齢": m_age, "潮名": get_tide_name(m_age),
                    "潮位フェーズ": phase, "場所": final_place, "魚種": fish_name, "全長_cm": st.session_state.length_val,
                    "ルアー": lure, "備考": memo, "釣り人": angler, "観測所": station['name']
                }
                
                updated_df = pd.concat([conn.read(spreadsheet=gs_url), pd.DataFrame([new_row])], ignore_index=True)
                conn.update(spreadsheet=gs_url, data=updated_df)
                st.cache_data.clear()
                st.success("記録完了！")
                st.balloons()

# 他のタブの呼び出し
with tab2: show_edit_page(conn, url):
with tab3: show_gallery_page()
with tab4: show_analysis_page()
with tab5: show_monthly_stats()



