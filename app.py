import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime, timedelta
import requests
import math

# --- 1. 各種関数定義 ---
def get_moon_age(dt):
    base_new_moon = datetime(2023, 1, 22, 5, 53)
    lunar_cycle = 29.530588
    diff_days = (dt - base_new_moon).total_seconds() / 86400
    return round(diff_days % lunar_cycle, 1)
    
def calculate_distance(lat1, lon1, lat2, lon2):
    if None in [lat1, lon1, lat2, lon2]: return 999.0
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

def get_wind_direction_label(degree):
    if degree is None: return ""
    labels = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
    return labels[int((degree + 11.25) / 22.5) % 16]

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
    if not dms: return None
    res = dms[0] + dms[1] / 60.0 + dms[2] / 3600.0
    return -res if ref in ['S', 'W'] else round(res, 6)

def get_weather_data(lat, lon, dt):
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
        # ターゲット時刻に最も近いインデックスを取得
        idx = (len(h['temperature_2m']) - 25) + dt.hour
        return h['temperature_2m'][idx], h['windspeed_10m'][idx], h['winddirection_10m'][idx], round(sum(h['precipitation'][:idx+1][-48:]), 1)
    except: return None, None, None, None

def get_tide_details(lat, lon, dt):
    STATIONS = [
        {"name": "本渡瀬戸", "lat": 32.26, "lon": 130.13, "code": "HS"},
        {"name": "苓北", "lat": 32.28, "lon": 130.20, "code": "RH"},
        {"name": "口之津", "lat": 32.36, "lon": 130.12, "code": "KT"},
        {"name": "八代", "lat": 32.31, "lon": 130.34, "code": "O5"},
    ]
    
    station = STATIONS[0]
    min_dist = 999
    for s in STATIONS:
        d = calculate_distance(lat, lon, s["lat"], s["lon"])
        if d < min_dist: min_dist, station = d, s

    try:
        url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{dt.year}/{station['code']}.txt"
        response = requests.get(url, timeout=10)
        if response.status_code != 200: return {}
        
        lines = response.text.splitlines()
        # 日付: 73-78カラム (Python index 72-78)
        date_str = dt.strftime("%y%m%d")
        
        line = next((l for l in lines if len(l) >= 78 and l[72:78] == date_str), None)
        if not line: return {}

        # 1. 毎時潮位: 1-72カラム (3桁×24時間)
        # 10時のデータなら、(10 * 3) = 30文字目から3文字
        start_idx = dt.hour * 3
        current_hour_tide_raw = line[start_idx : start_idx + 3].strip()
        current_hour_tide = int(current_hour_tide_raw) if current_hour_tide_raw else 0

        # 2. 満潮・干潮イベント
        events = []
        # 満潮: 81-108カラム (4桁時刻+3桁潮位が4セット)
        # Pythonインデックスでは 80番目から開始
        for i in range(4):
            base = 80 + (i * 7)
            time_part = line[base : base + 4].strip()
            tide_part = line[base + 4 : base + 7].strip()
            if time_part and time_part != "9999":
                ev_dt = datetime(dt.year, dt.month, dt.day, int(time_part[:2]), int(time_part[2:]))
                events.append({"type": "満潮", "time": ev_dt, "tide": tide_part})

        # 干潮: 109-136カラム (4桁時刻+3桁潮位が4セット)
        # Pythonインデックスでは 108番目から開始
        for i in range(4):
            base = 108 + (i * 7)
            time_part = line[base : base + 4].strip()
            tide_part = line[base + 4 : base + 7].strip()
            if time_part and time_part != "9999":
                ev_dt = datetime(dt.year, dt.month, dt.day, int(time_part[:2]), int(time_part[2:]))
                events.append({"type": "干潮", "time": ev_dt, "tide": tide_part})

        events.sort(key=lambda x: x["time"])

        # 3. 補足情報の計算
        next_high = next((e for e in events if e["type"] == "満潮" and e["time"] > dt), None)
        next_low = next((e for e in events if e["type"] == "干潮" and e["time"] > dt), None)
        min_to_high = int((next_high["time"] - dt).total_seconds() / 60) if next_high else ""
        min_to_low = int((next_low["time"] - dt).total_seconds() / 60) if next_low else ""

        # 直前の満干潮
        prev_h = next((e["time"].strftime("%H:%M") for e in reversed(events) if e["type"] == "満潮" and e["time"] <= dt), "")
        prev_l = next((e["time"].strftime("%H:%M") for e in reversed(events) if e["type"] == "干潮" and e["time"] <= dt), "")

        # 4. フェーズ判定
        prev_ev = next((e for e in reversed(events) if e["time"] <= dt), None)
        next_ev = next((e for e in events if e["time"] > dt), None)
        phase = "不明"
        if prev_ev and next_ev:
            direction = "下げ" if prev_ev["type"] == "満潮" else "上げ"
            ratio = (dt - prev_ev["time"]).total_seconds() / (next_ev["time"] - prev_ev["time"]).total_seconds()
            phase = f"{direction}{max(1, min(9, round(ratio * 10)))}分"

        return {
            "潮位_cm": current_hour_tide,
            "潮位フェーズ": phase,
            "直前の満潮_時刻": prev_h,
            "直前の干潮_時刻": prev_l,
            "次の満潮まで_分": min_to_high,
            "次の干潮まで_分": min_to_low,
            "観測所": station["name"]
        }
    except:
        return {}

def get_tide_name(dt):
    base_new_moon = datetime(2023, 1, 22, 5, 53)
    lunar_cycle = 29.530588
    diff_days = (dt - base_new_moon).total_seconds() / 86400
    age = diff_days % lunar_cycle
    if age < 3.0 or age > 26.5: return "大潮"
    elif age < 7.0: return "中潮"
    elif age < 11.0: return "小潮"
    elif age < 13.0: return "長潮"
    elif age < 14.0: return "若潮"
    elif age < 18.0: return "大潮"
    elif age < 22.0: return "中潮"
    else: return "小潮"

# --- 3. メイン UI ---
st.set_page_config(page_title="Fishing AI Log", layout="wide")
st.title("🎣 釣果統合ログシステム")

# データ接続
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    df = conn.read(spreadsheet=url, ttl="5m")
    m_df = conn.read(spreadsheet=url, worksheet="place_master", ttl="10m")
except:
    st.error("スプレッドシート接続エラー"); st.stop()

# 写真アップロード
uploaded_file = st.file_uploader("📸 写真を選択", type=['jpg', 'jpeg'])
auto_lat, auto_lon, default_dt = 32.5, 130.0, datetime.now()

if uploaded_file:
    img = Image.open(uploaded_file)
    exif = img._getexif()
    if exif:
        geotags = get_geotagging(exif)
        if geotags:
            lat = get_decimal_from_dms(geotags.get('GPSLatitude'), geotags.get('GPSLatitudeRef'))
            lon = get_decimal_from_dms(geotags.get('GPSLongitude'), geotags.get('GPSLongitudeRef'))
            if lat: auto_lat, auto_lon = lat, lon
        dt_str = exif.get(36867)
        if dt_str: 
            try: default_dt = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S')
            except: pass

# 場所自動判定
nearest_place = None
place_to_id = {}
if not m_df.empty:
    place_to_id = dict(zip(m_df["place_name"], m_df["group_id"]))
    for _, row in m_df.iterrows():
        if calculate_distance(auto_lat, auto_lon, row['latitude'], row['longitude']) < 0.5:
            nearest_place = row['place_name']; break
place_options = sorted(place_to_id.keys())

# --- 4. フォーム ---
with st.form("main_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    with c1:
        date_in = st.date_input("📅 日付", value=default_dt.date())
        time_in = st.time_input("⏰ 時刻", value=default_dt.time())
        default_idx = (place_options.index(nearest_place) + 1) if nearest_place in place_options else 0
        place_sel = st.selectbox("📍 釣り場を選択", options=["-- 新規地点 or 手動入力 --"] + place_options, index=default_idx)
    with c2:
        lat_in = st.number_input("緯度", value=auto_lat, format="%.6f")
        lon_in = st.number_input("経度", value=auto_lon, format="%.6f")
        place_man = st.text_input("📍 新しい場所名（新規時のみ）")

    fish_in = st.text_input("🐟 魚種")
    length_in = st.number_input("📏 全長(cm)", value=0.0)
    lure_in = st.text_input("🪝 ルアー")
    memo_in = st.text_area("📝 備考")
    submit = st.form_submit_button("🚀 保存")

    # --- 保存処理の開始 ---
    if submit:
        # 場所の確定
        if place_sel != "-- 新規地点 or 手動入力 --":
            final_place_name = place_sel
            final_group_id = place_to_id.get(place_sel)
        else:
            final_place_name = place_man
            final_group_id = int(m_df["group_id"].max() + 1) if not m_df.empty else 1

        if not final_place_name:
            st.error("⚠️ 場所名を入力してください。")
        else:
            with st.spinner('📊 解析中...'):
                try:
                    # 日時オブジェクト作成
                    target_dt = datetime(date_in.year, date_in.month, date_in.day, time_in.hour, time_in.minute)
                    
                    # 潮汐・気象計算
                    t_name = get_tide_name(target_dt)
                    t_info = get_tide_details(lat_in, lon_in, target_dt)
                    temp, wind_s, wind_d, prec = get_weather_data(lat_in, lon_in, target_dt)

                    # --- ご指定の列順にデータを並べ替え ---
                    # 全ての列を網羅し、スプレッドシートの左からの並び順と一致させます
                    save_data = {
                        "filename": uploaded_file.name if uploaded_file else "",
                        "datetime": target_dt.strftime('%Y-%m-%d %H:%M'),
                        "date": date_in.strftime('%Y-%m-%d'),
                        "time": time_in.strftime('%H:%M'),
                        "lat": lat_in,
                        "lon": lon_in,
                        "気温": temp,
                        "風速": wind_s,
                        "風向": get_wind_direction_label(wind_d),
                        "降水量": prec,
                        "潮位_cm": t_info.get("潮位_cm"),
                        "月齢": get_moon_age(target_dt), # 月齢取得用の簡易処理
                        "潮名": t_name,
                        "次の満潮まで_分": t_info.get("次の満潮まで_分", ""), # 計算に含まれる場合
                        "次の干潮まで_分": t_info.get("次の干潮まで_分", ""), # 計算に含まれる場合
                        "直前の満潮_時刻": t_info.get("直前の満潮_時刻"),
                        "直前の干潮_時刻": t_info.get("直前の干潮_時刻"),
                        "潮位フェーズ": t_info.get("潮位フェーズ"),
                        "場所": final_place_name,
                        "魚種": fish_in,
                        "全長_cm": length_in,
                        "ルアー": lure_in,
                        "備考": memo_in,
                        "group_id": final_group_id,
                        "観測所": t_info.get("観測所", "不明")
                    }

                    # データフレーム作成（順番を維持）
                    new_row = pd.DataFrame([save_data])
                    
                    # カラムの順番を強制的にスプレッドシートに合わせる
                    cols = ["filename", "datetime", "date", "time", "lat", "lon", "気温", "風速", "風向", "降水量", "潮位_cm", "月齢", "潮名", "次の満潮まで_分", "次の干潮まで_分", "直前の満潮_時刻", "直前の干潮_時刻", "潮位フェーズ", "場所", "魚種", "全長_cm", "ルアー", "備考", "group_id", "観測所"]
                    new_row = new_row[cols]

                    # メインデータ更新
                    updated_df = pd.concat([df[cols], new_row], ignore_index=True)
                    conn.update(spreadsheet=url, data=updated_df)

                    # 新規場所ならマスターにも追加
                    if place_sel == "-- 新規地点 or 手動入力 --":
                        new_m = pd.DataFrame([{"group_id": final_group_id, "place_name": final_place_name, "latitude": lat_in, "longitude": lon_in}])
                        updated_m = pd.concat([m_df, new_m], ignore_index=True)
                        conn.update(spreadsheet=url, worksheet="place_master", data=updated_m)

                    st.success(f"✅ {final_place_name} での釣果を保存しました！")
                    st.balloons()
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"❌ 書き込みエラーが発生しました: {e}")



