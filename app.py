import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime, timedelta
import requests
import math

# --- 1. 各種関数定義 ---
def calculate_distance(lat1, lon1, lat2, lon2):
    """
    2点間の直線距離(km)を計算する関数（ハバーシン公式）
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return 999.0  # 座標がない場合は大きな値を返す
    
    R = 6371.0  # 地球の半径 (km)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c
    
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

# --- 2. 気象データ取得関数（風向対応版） ---
def get_weather_data(lat, lon, dt):
    """気象データを取得。気温・風速・風向・48h降水量の4つを返す"""
    try:
        start_date = (dt - timedelta(days=2)).strftime('%Y-%m-%d')
        end_date = dt.strftime('%Y-%m-%d')
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": float(lat),
            "longitude": float(lon),
            "start_date": start_date,
            "end_date": end_date,
            "hourly": "temperature_2m,windspeed_10m,winddirection_10m,precipitation",
            "timezone": "Asia/Tokyo"
        }
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        
        if "hourly" not in data:
            return None, None, None, None # 4つ返す

        idx = (len(data['hourly']['temperature_2m']) - 25) + dt.hour
        idx = max(0, min(idx, len(data['hourly']['temperature_2m']) - 1))
        
        temp = data['hourly']['temperature_2m'][idx]
        wind_s = data['hourly']['windspeed_10m'][idx]
        wind_d = data['hourly']['winddirection_10m'][idx] # 風向を追加
        precip_list = data['hourly']['precipitation'][:idx+1]
        precip_48h = sum(precip_list[-48:])
        
        return temp, wind_s, wind_d, round(precip_48h, 1) # 4つ返す
    except:
        return None, None, None, None # 失敗時も4つ返す

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
    
    # 潮位(cm)の計算
    tide_cm = int(100 + 80 * math.cos(math.pi * (hour_cycle / 6.21)))

    # --- 直前の満潮・干潮時刻の算出 ---
    # 1. 直前の満潮 (hour_cycle分だけ遡る)
    prev_high_dt = dt - timedelta(hours=hour_cycle)
    
    # 2. 直前の干潮
    if hour_cycle >= 6.21:
        # すでに干潮を過ぎている場合、その干潮時刻
        prev_low_dt = dt - timedelta(hours=(hour_cycle - 6.21))
    else:
        # まだ干潮に達していない場合、前サイクルの干潮時刻
        prev_low_dt = dt - timedelta(hours=(hour_cycle + 6.21))

    return {
        "潮位_cm": tide_cm,
        "月齢": moon_age,
        "潮位フェーズ": phase,
        "直前の満潮_時刻": prev_high_dt.strftime("%H:%M"),
        "直前の干潮_時刻": prev_low_dt.strftime("%H:%M"),
        "次の満潮まで_分": int((12.42 - hour_cycle) * 60) if hour_cycle < 12.42 else 0,
        "次の干潮まで_分": int((6.21 - hour_cycle) * 60 if hour_cycle < 6.21 else (18.63 - hour_cycle) * 60)
    }

def get_wind_direction_label(degree):
    """角度(0-360)を方位文字に変換"""
    if degree is None or degree == "": return ""
    labels = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", 
              "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
    idx = int((degree + 11.25) / 22.5) % 16
    return labels[idx]

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

# --- 統合版：場所自動判定 ＆ 入力フォーム ---

# 1. 準備：マスターデータから場所・ID・座標の辞書を作成
if not m_df.empty:
    # 場所名 -> ID の辞書
    place_to_id = dict(zip(m_df["place_name"], m_df["group_id"]))
    # 場所名 -> (緯度, 経度) の辞書（距離計算用）
    place_coords = {row['place_name']: (row['latitude'], row['longitude']) for _, row in m_df.iterrows()}
    place_options = sorted(place_to_id.keys())
    
    # 【GPS自動検知】写真の座標(lat_in, lon_in)から最も近い地点を探す
    nearest_place = None
    min_dist = 0.5  # 500m以内を検知対象とする
    
    for p_name, coords in place_coords.items():
        dist = calculate_distance(lat_in, lon_in, coords[0], coords[1])
        if dist < min_dist:
            min_dist = dist
            nearest_place = p_name
else:
    place_to_id = {}
    place_options = []
    nearest_place = None

# --- UI表示 ---

st.write("### 📝 釣果入力")

# デフォルトの選択肢を決定（GPSで見つかればその場所、なければ「新規」）
default_index = 0
if nearest_place in place_options:
    default_index = place_options.index(nearest_place) + 1 # 0番目は「--新規--」のため+1

with st.form("main_form", clear_on_submit=True):
    # レイアウト：1列目（日時・場所選択）
    col1, col2 = st.columns(2)
    
    with col1:
        date_in = st.date_input("📅 日付", value=default_dt.date())
        time_in = st.time_input("⏰ 時刻", value=default_dt.time())
        
        place_selected = st.selectbox(
            "📍 釣り場を選択（GPS自動検知対応）", 
            options=["-- 新規地点 or 手動入力 --"] + place_options,
            index=default_index
        )
        
        # 自動検知された場合のメッセージ表示
        if nearest_place and place_selected == nearest_place:
            st.caption(f"✨ 写真の位置情報から「{nearest_place}」を自動選択しました（距離: {int(min_dist*1000)}m）")

    with col2:
        lat_in_final = st.number_input("緯度(Lat)", value=lat_in, format="%.6f")
        lon_in_final = st.number_input("経度(Lon)", value=lon_in, format="%.6f")
        
        place_manual = st.text_input("📍 新しい場所名を入力（新規の場合）", placeholder="〇〇漁港 外堤防")

    st.divider()

    # レイアウト：2列目（釣果詳細）
    col3, col4 = st.columns(2)
    
    with col3:
        fish_in = st.text_input("🐟 魚種", placeholder="シーバス、チヌ、アジなど")
        length_in = st.slider("📏 全長 (cm)", 0.0, 150.0, 40.0, step=0.5)
        lure_in = st.text_input("🎣 使用ルアー/仕掛け", placeholder="ミノー 120F")
        
    with col4:
        memo_in = st.text_area("📝 備考・ヒットパターン", placeholder="上げ潮が効き始めたタイミング。明暗の境目でヒット。")

    # 保存ボタン
    submit = st.form_submit_button("🚀 気象・潮汐を解析してスプレッドシートに保存")

# --- 保存ボタンが押された後の処理 ---

if submit:
    # 場所名とIDの確定
    if place_selected != "-- 新規地点 or 手動入力 --":
        final_place_name = place_selected
        final_group_id = place_to_id.get(place_selected)
    else:
        final_place_name = place_manual
        # 新規の場合は現在の最大ID + 1
        final_group_id = int(m_df["group_id"].max() + 1) if not m_df.empty else 0

    if not final_place_name:
        st.error("⚠️ 場所名を選択するか、新しい場所名を入力してください。")
    else:
        with st.spinner('📊 当時の気象と潮汐を計算中...'):
            target_dt = datetime.combine(date_in, time_in)
            
            # 1. 気象取得（4項目）
            weather_res = get_weather_data(lat_in_final, lon_in_final, target_dt)
            if weather_res and len(weather_res) == 4:
                temp, wind_s, wind_d, precip = weather_res
            else:
                temp, wind_s, wind_d, precip = None, None, None, None
            
            # 2. 潮汐取得（10段階フェーズ版）
            tide_name = get_tide_name(target_dt)
            tide_info = get_tide_details(target_dt)
            
            # 3. 保存データの作成
            save_data = {
                "group_id": final_group_id,
                "場所": final_place_name,
                "datetime": target_dt.strftime('%Y-%m-%d %H:%M'),
                "date": date_in.strftime('%Y-%m-%d'),
                "time": time_in.strftime('%H:%M'),
                "lat": lat_in_final,
                "lon": lon_in_final,
                "気温": temp,
                "風速": wind_s,
                "風向": get_wind_direction_label(wind_d), # 度数から方位文字へ
                "降水量": precip,
                "潮名": tide_name,
                "潮位_cm": tide_info.get("潮位_cm"),
                "月齢": tide_info.get("月齢"),
                "潮位フェーズ": tide_info.get("潮位フェーズ"),
                "直前の満潮_時刻": tide_info.get("直前の満潮_時刻"),
                "直前の干潮_時刻": tide_info.get("直前の干潮_時刻"),
                "次の満潮まで_分": tide_info.get("次の満潮まで_分"),
                "次の干潮まで_分": tide_info.get("次の干潮まで_分"),
                "魚種": fish_in,
                "全長_cm": length_in,
                "ルアー": lure_in,
                "備考": memo_in,
                "filename": uploaded_file.name if uploaded_file else ""
            }
            
            # 4. 書き込み実行
            try:
                new_row = pd.DataFrame([save_data])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(spreadsheet=url, data=updated_df)
                
                # 新規場所だった場合はマスターにも追加
                if place_selected == "-- 新規地点 or 手動入力 --":
                    new_m = pd.DataFrame([{
                        "group_id": final_group_id, 
                        "place_name": final_place_name, 
                        "latitude": lat_in_final, 
                        "longitude": lon_in_final
                    }])
                    updated_m = pd.concat([m_df, new_m], ignore_index=True)
                    conn.update(spreadsheet=url, worksheet="place_master", data=updated_m)

                st.success(f"✅ 保存成功: {final_place_name} (ID:{final_group_id})")
                st.balloons()
                st.cache_data.clear()
                # st.rerun() # 必要に応じて
            except Exception as e:
                st.error(f"保存に失敗しました: {e}")










