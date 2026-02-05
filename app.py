import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime, timedelta
import requests

# --- 1. 関数定義エリア (独立させて並べる) ---

def get_weather_data(lat, lon, dt):
    """指定された緯度経度・日時の気象データ(気温・風速・48h降水量)を取得"""
    try:
        start_date = (dt - timedelta(days=2)).strftime('%Y-%m-%d')
        end_date = dt.strftime('%Y-%m-%d')
        
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": "temperature_2m,windspeed_10m,precipitation",
            "timezone": "Asia/Tokyo"
        }
        response = requests.get(url, params=params).json()

        # インデックスの計算 (48時間前からのリストなので調整)
        current_idx = (len(response['hourly']['temperature_2m']) - 25) + dt.hour
        
        temp = response['hourly']['temperature_2m'][current_idx]
        wind_s = response['hourly']['windspeed_10m'][current_idx]
        
        # 48時間合計降水量の計算
        precip_list = response['hourly']['precipitation'][:current_idx+1]
        total_precip_48h = sum(precip_list[-48:])
        
        return temp, wind_s, round(total_precip_48h, 1)
    except Exception as e:
        return None, None, None

def get_tide_name(dt):
    """簡易的な潮名判定ロジック"""
    base_date = datetime(2023, 1, 22) # 新月基準
    diff = (dt - base_date).days % 30
    
    if diff in [0, 1, 14, 15, 29]: return "大潮"
    if diff in [2, 3, 4, 16, 17, 18]: return "中潮"
    if diff in [5, 6, 7, 19, 20, 21]: return "小潮"
    if diff in [8, 22]: return "長潮"
    if diff in [9, 23]: return "若潮"
    return "中潮"

# --- 2. アプリ初期設定 ---

st.set_page_config(page_title="Fishing App", layout="wide")
st.title("🎣 プロ仕様・自動補完ログ")

# デフォルト日時の設定
default_datetime = datetime.now()

# データの読み込み (キャッシュ設定 ttl="10m")
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    
    df = conn.read(spreadsheet=url, ttl="10m")
    m_df = conn.read(spreadsheet=url, worksheet="place_master", ttl="10m")
    place_options = sorted(m_df["place_name"].unique().tolist())
except Exception as e:
    if "429" in str(e):
        st.error("🚫 Google APIの制限に達しました。1分ほど待って再起動してください。")
    else:
        st.error(f"接続エラー: {e}")
    st.stop()

# --- 3. マスター管理 (釣り場追加) ---

with st.expander("📍 新しい釣り場をマスターに追加"):
    new_place_name = st.text_input("追加する釣り場名")
    new_lat = st.number_input("緯度 (Latitude)", value=35.0, format="%.6f")
    new_lon = st.number_input("経度 (Longitude)", value=135.0, format="%.6f")
    
    if st.button("場所を登録"):
        if new_place_name and new_place_name not in m_df["place_name"].values:
            new_id = m_df["group_id"].max() + 1 if not m_df.empty else 0
            new_row = pd.DataFrame([{
                "group_id": int(new_id), 
                "place_name": new_place_name,
                "latitude": new_lat,
                "longitude": new_lon
            }])
            updated_m_df = pd.concat([m_df, new_row], ignore_index=True)
            conn.update(spreadsheet=url, worksheet="place_master", data=updated_m_df)
            st.success(f"✅ 「{new_place_name}」を登録しました！")
            st.cache_data.clear()
            st.rerun()

st.write("---")

# --- 4. 釣果入力エリア ---

uploaded_file = st.file_uploader("📸 写真を選択（日時を自動反映）", type=['jpg', 'jpeg', 'png'])

if uploaded_file:
    try:
        img = Image.open(uploaded_file)
        exif = img._getexif()
        if exif:
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag == 'DateTimeOriginal':
                    default_datetime = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                    st.success(f"✅ 写真から日時を読み取りました: {default_datetime.strftime('%Y-%m-%d %H:%M')}")
    except Exception:
        st.warning("写真のメタデータを読み込めませんでした。")

with st.form("input_form", clear_on_submit=True):
    date_in = st.date_input("📅 日付", value=default_datetime.date())
    time_in = st.time_input("⏰ 時刻", value=default_datetime.time())
    
    place_in = st.selectbox("📍 場所", options=place_options)
    
    # 選択した場所の情報を取得
    loc_data = m_df.loc[m_df["place_name"] == place_in]
    current_id = loc_data["group_id"].values[0] if not loc_data.empty else 0
    lat = loc_data["latitude"].values[0] if "latitude" in m_df.columns and not loc_data.empty else 35.0
    lon = loc_data["longitude"].values[0] if "longitude" in m_df.columns and not loc_data.empty else 135.0
    
    fish_in = st.text_input("🐟 魚種", placeholder="シーバス")
    lure_in = st.text_input("🎣 ルアー")
    length_in = st.slider("📏 全長 (cm)", 0.0, 150.0, 40.0, 1.0)
    memo_in = st.text_area("📝 備考")
    
    submit_button = st.form_submit_button("🚀 気象を自動取得して保存", use_container_width=True)

# --- 5. 保存処理 ---

if submit_button:
    with st.spinner('データを解析・保存中...'):
        target_dt = datetime.combine(date_in, time_in)
        temp, wind_s, precip_48h = get_weather_data(lat, lon, target_dt)
        tide_name = get_tide_name(target_dt)

        save_data = {
            "filename": uploaded_file.name if uploaded_file else "",
            "datetime": target_dt.strftime('%Y-%m-%d %H:%M'),
            "date": date_in.strftime('%Y-%m-%d'),
            "time": time_in.strftime('%H:%M'),
            "lat": lat,
            "lon": lon,
            "気温": temp,
            "風速": wind_s,
            "降水量": precip_48h,
            "潮名": tide_name,
            "場所": place_in,
            "魚種": fish_in,
            "全長_cm": length_in,
            "ルアー": lure_in,
            "備考": memo_in,
            "group_id": int(current_id),
            "weather_station_name": "", 
            "station_code": "",
            "潮位_cm": "",
            "月齢": ""
        }
        
        new_row_df = pd.DataFrame([save_data])
        updated_df = pd.concat([df, new_row_df], ignore_index=True)
        conn.update(spreadsheet=url, data=updated_df)
        
        st.success(f"✅ 保存完了！ 気温:{temp}℃ 降水量:{precip_48h}mm")
        st.cache_data.clear()
        st.rerun()

st.write("---")
