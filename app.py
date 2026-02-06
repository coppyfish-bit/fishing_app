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
        idx = (len(h['temperature_2m']) - 25) + dt.hour
        return h['temperature_2m'][idx], h['windspeed_10m'][idx], h['winddirection_10m'][idx], round(sum(h['precipitation'][:idx+1][-48:]), 1)
    except: return None, None, None, None

def get_best_station(lat, lon, place_name):
    if any(k in place_name for k in ["苓北", "富岡", "都呂々"]):
        return {"name": "苓北", "code": "RH", "lat": 32.5011, "lon": 130.0381}
    if any(k in place_name for k in ["本渡", "瀬戸", "下浦"]):
        return {"name": "本渡瀬戸", "code": "HS", "lat": 32.2625, "lon": 130.1342}
    if any(k in place_name for k in ["八代", "鏡", "日奈久"]):
        return {"name": "八代", "code": "O5", "lat": 32.5022, "lon": 130.5683}
    if any(k in place_name for k in ["口之津", "島原", "南島原"]):
        return {"name": "口之津", "code": "KT", "lat": 32.6106, "lon": 130.1931}

    STATIONS = [
        {"name": "本渡瀬戸", "code": "HS", "lat": 32.2625, "lon": 130.1342},
        {"name": "苓北",     "code": "RH", "lat": 32.5011, "lon": 130.0381},
        {"name": "口之津",   "code": "KT", "lat": 32.6106, "lon": 130.1931},
        {"name": "八代",     "code": "O5", "lat": 32.5022, "lon": 130.5683},
    ]
    best_s = STATIONS[0]
    min_dist = 999
    for s in STATIONS:
        dist = ((lat - s["lat"])**2 + (lon - s["lon"])**2)**0.5
        if dist < min_dist:
            min_dist, best_s = dist, s
    return best_s

def get_tide_details(lat, lon, dt, place_name=""):
    station = get_best_station(lat, lon, place_name)
    try:
        url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{dt.year}/{station['code']}.txt"
        response = requests.get(url, timeout=10)
        if response.status_code != 200: return {}
        lines = response.text.splitlines()
        
        def parse_line(target_date):
            d_str = f"{target_date.month:>2}{target_date.day:>2}"
            row = next((l for l in lines if len(l) > 78 and l[74:78] == d_str), None)
            if not row: return None, []
            evs = []
            for b_start, e_type in [(80, "満潮"), (108, "干潮")]:
                for i in range(4):
                    base = b_start + (i * 7)
                    t_raw = row[base : base+4].strip()
                    h_raw = row[base+4 : base+7].strip()
                    if t_raw and t_raw != "9999":
                        t_str = t_raw.replace(" ", "0").zfill(4)
                        ev_dt = datetime(target_date.year, target_date.month, target_date.day, int(t_str[:2]), int(t_str[2:]))
                        evs.append({"type": e_type, "time": ev_dt, "tide": h_raw})
            return row, evs

        line_today, events_today = parse_line(dt)
        _, events_tomorrow = parse_line(dt + timedelta(days=1))
        all_events = sorted(events_today + events_tomorrow, key=lambda x: x["time"])

        tide_val = line_today[dt.hour*3 : dt.hour*3+3].strip()
        current_hour_tide = int(tide_val) if tide_val else 0

        next_high = next((e for e in all_events if e["type"] == "満潮" and e["time"] > dt), None)
        next_low = next((e for e in all_events if e["type"] == "干潮" and e["time"] > dt), None)
        prev_ev = next((e for e in reversed(all_events) if e["time"] <= dt), None)
        next_ev = next((e for e in all_events if e["time"] > dt), None)

        res = {
            "潮位_cm": current_hour_tide,
            "潮位フェーズ": "不明",
            "直前の満潮_時刻": next((e["time"].strftime("%H:%M") for e in reversed(all_events) if e["type"] == "満潮" and e["time"] <= dt), ""),
            "直前の干潮_時刻": next((e["time"].strftime("%H:%M") for e in reversed(all_events) if e["type"] == "干潮" and e["time"] <= dt), ""),
            "次の満潮まで_分": int((next_high["time"] - dt).total_seconds() / 60) if next_high else "",
            "次の干潮まで_分": int((next_low["time"] - dt).total_seconds() / 60) if next_low else "",
            "観測所": station["name"]
        }

        if prev_ev and next_ev:
            direction = "下げ" if prev_ev["type"] == "満潮" else "上げ"
            diff_total = (next_ev["time"] - prev_ev["time"]).total_seconds()
            diff_now = (dt - prev_ev["time"]).total_seconds()
            res["潮位フェーズ"] = f"{direction}{max(1, min(9, round(diff_now / diff_total * 10)))}分"
        return res
    except: return {}

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

# --- 2. メイン UI 制御 ---
st.set_page_config(page_title="Fishing AI Log", layout="centered")
st.title("🎣 釣果統合ログシステム")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    df = conn.read(spreadsheet=url, ttl="5m")
    m_df = conn.read(spreadsheet=url, worksheet="place_master", ttl="10m")
except:
    st.error("スプレッドシート接続エラー"); st.stop()

uploaded_file = st.file_uploader("📸 写真を選択", type=['jpg', 'jpeg'], key="main_uploader")
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

# 場所の判定
detected_name, detected_id = find_nearest_place(auto_lat, auto_lon, m_df)
is_new_place = False

st.markdown("### 📍 釣り場")
if detected_name:
    st.success(f"✅ **{detected_name}** (付近の写真です)")
    final_place_name = detected_name
    final_group_id = detected_id
else:
    st.warning("🆕 500m以内に登録地点がありません")
    final_place_name = st.text_input("新規釣り場名を入力", placeholder="例: 〇〇港 堤防")
    final_group_id = int(m_df["group_id"].max() + 1) if not m_df.empty else 1
    is_new_place = True

with st.expander("場所を手動で修正・選択"):
    place_to_id = dict(zip(m_df['place_name'], m_df['group_id'])) if not m_df.empty else {}
    manual_sel = st.selectbox("登録済み地点から選ぶ", ["-- 選択なし --"] + list(place_to_id.keys()))
    if manual_sel != "-- 選択なし --":
        final_place_name = manual_sel
        final_group_id = place_to_id[manual_sel]
        is_new_place = False

# 釣果入力
# --- カスタムCSS（フィッシュメジャー風） ---
st.markdown("""
    <style>
    .stSlider [data-baseweb="slider"] {
        height: 60px !important;
        width: calc(100% - 24px) !important; 
        margin: 0 auto !important;
        background-color: #FFFFFF !important;
        border: 2px solid #001f3f !important;
        border-radius: 4px !important;

        /* 目盛り線の描画 */
        background-image: 
            linear-gradient(90deg, #001f3f 3px, transparent 3px),
            linear-gradient(90deg, #001f3f 1px, transparent 1px) !important;
        
        /* ↓【最重要】線の間隔を120cmの「区切り数」で正確に指定 */
        background-size: calc((100% / 12)) 100%, calc((100% / 24)) 50% !important;
        
        /* ↓【微調整】線の開始位置をスライダーのポインタの「芯」に合わせる */
        background-position: 4.0px center !important; 
        background-repeat: repeat-x !important;
    }

    /* ポインタ（赤矢印）の芯出し */
    .stSlider [role="slider"]::after {
        content: "";
        display: block;
        width: 0;
        height: 0;
        border-left: 15px solid transparent;
        border-right: 15px solid transparent;
        border-bottom: 25px solid #FF4B4B; 
        margin-top: 85px; 
        /* ポインタの真ん中を目盛りに合わせるための位置補正 */
        transform: translateX(0px); 
    }
    </style>
    """, unsafe_allow_html=True)
# --- 2. スライダーと目盛り表示部分 ---
current_len = st.session_state.get('len_slider', 20.0)
st.markdown(f"### 全長: <span style='font-size:40px; color:#FF4B4B; font-weight:900;'>{current_len}</span> cm", unsafe_allow_html=True)

# 【重要：順番を入れ替える】スライダーの「前」に数字を書く
st.markdown("""
    <div style="
        display: flex; 
        justify-content: space-between; 
      /* 左の数字を大きく、右の数字を小さくすると、全体が左に寄ります */
        padding: 0 -40px 0 -120px;  /* 上 右 下 左 の順番です */
        font-size: 16px; 
        color: #FF4B4B;        /* 数字も赤に変更（お好みで） */
        font-weight: 900; 
        margin-bottom: -72px;  /* ここを大きくマイナスにすると、数字が下の要素（バー）に重なります */
        position: relative; 
        z-index: 10; 
        pointer-events: none; 
        line-height: 60px;     /* バーの高さと同じにする */
        font-family: 'Arial Black', sans-serif;
    ">
        <span>0</span><span>10</span><span>20</span><span>30</span><span>40</span><span>50</span><span>60</span>
        <span>70</span><span>80</span><span>90</span><span>100</span><span>110</span><span>120</span>
    </div>
    """, unsafe_allow_html=True)

# スライダー本体（数字の後に書く）
length_in = st.slider("", 0.0, 120.0, 0.0, step=1.0, key="len_slider", label_visibility="collapsed")
with st.expander("日時・座標の微調整"):
    date_in = st.date_input("日付", default_dt.date())
    time_in = st.time_input("時刻", default_dt.time())
    lat_in = st.number_input("緯度", value=auto_lat, format="%.6f")
    lon_in = st.number_input("経度", value=auto_lon, format="%.6f")

st.markdown("---")
submit = st.button("🚀 釣果を保存する", use_container_width=True, type="primary")

st.markdown("**ルアー・仕掛け**")
lure_sel = st.text_input("例：カゲロウ125MD ←数字、英字は半角でお願いします。コピペ用 60ES 70f 70s 80f 80s 82s 100f 100s 110f 110s 120f 120s 124f 125f 130f 130s 140f 140s 150f 150s 160f 160s")
lure_extra = st.text_input("詳細・カラー (任意)")
lure_in = ", ".join(lure_sel) + (f" ({lure_extra})" if lure_extra else "")

st.markdown("**メモ**")
memo_in = st.text_area("", placeholder="ヒットパターンなど", label_visibility="collapsed")

# --- 保存処理 ---
if submit:
    if not final_place_name:
        st.error("⚠️ 場所名を入力してください。")
    else:
        with st.spinner('📊 解析・保存中...'):
            try:
                target_dt = datetime.combine(date_in, time_in)
                t_name = get_tide_name(target_dt)
                t_info = get_tide_details(lat_in, lon_in, target_dt, final_place_name)
                temp, wind_s, wind_d, prec = get_weather_data(lat_in, lon_in, target_dt)

                save_data = {
                    "filename": uploaded_file.name if uploaded_file else "",
                    "datetime": target_dt.strftime('%Y-%m-%d %H:%M'),
                    "date": date_in.strftime('%Y-%m-%d'),
                    "time": time_in.strftime('%H:%M'),
                    "lat": lat_in, "lon": lon_in,
                    "気温": temp, "風速": wind_s, "風向": get_wind_direction_label(wind_d), "降水量": prec,
                    "潮位_cm": t_info.get("潮位_cm"),
                    "月齢": get_moon_age(target_dt),
                    "潮名": t_name,
                    "次の満潮まで_分": t_info.get("次の満潮まで_分", ""),
                    "次の干潮まで_分": t_info.get("次の干潮まで_分", ""),
                    "直前の満潮_時刻": t_info.get("直前の満潮_時刻"),
                    "直前の干潮_時刻": t_info.get("直前の干潮_時刻"),
                    "潮位フェーズ": t_info.get("潮位フェーズ"),
                    "場所": final_place_name,
                    "魚種": fish_in, "全長_cm": length_in, "ルアー": lure_in, "備考": memo_in,
                    "group_id": final_group_id, "観測所": t_info.get("観測所", "不明")
                }

                cols = ["filename", "datetime", "date", "time", "lat", "lon", "気温", "風速", "風向", "降水量", "潮位_cm", "月齢", "潮名", "次の満潮まで_分", "次の干潮まで_分", "直前の満潮_時刻", "直前の干潮_時刻", "潮位フェーズ", "場所", "魚種", "全長_cm", "ルアー", "備考", "group_id", "観測所"]
                new_row = pd.DataFrame([save_data])[cols]
                updated_df = pd.concat([df[cols], new_row], ignore_index=True)
                conn.update(spreadsheet=url, data=updated_df)

                if is_new_place:
                    new_m = pd.DataFrame([{"group_id": final_group_id, "place_name": final_place_name, "latitude": lat_in, "longitude": lon_in}])
                    updated_m = pd.concat([m_df, new_m], ignore_index=True)
                    conn.update(spreadsheet=url, worksheet="place_master", data=updated_m)

                st.success(f"✅ {final_place_name} での釣果を保存しました！")
                st.balloons()
                st.cache_data.clear()
            except Exception as e:
                st.error(f"❌ 書き込みエラー: {e}")













































