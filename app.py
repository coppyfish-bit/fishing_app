import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime
import requests # 気象API用

# --- 1. 気象データ取得関数 ---
def get_weather_data(lat, lon, dt):
    try:
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": dt.strftime('%Y-%m-%d'),
            "end_date": dt.strftime('%Y-%m-%d'),
            "hourly": "temperature_2m,windspeed_10m,winddirection_10m,weathercode",
            "timezone": "Asia/Tokyo"
        }
        response = requests.get(url, params=params).json()
        hour = dt.hour
        temp = response['hourly']['temperature_2m'][hour]
        wind_s = response['hourly']['windspeed_10m'][hour]
        wind_d = response['hourly']['winddirection_10m'][hour]
        return temp, wind_s, wind_d
    except:
        return None, None, None

# --- 2. ページ設定とデータ読み込み ---
st.set_page_config(page_title="Fishing App", layout="wide")
st.title("🎣 プロ仕様・自動補完ログ")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    df = conn.read(spreadsheet=url, ttl=0)
    m_df = conn.read(spreadsheet=url, worksheet="place_master", ttl=0)
    place_options = sorted(m_df["place_name"].unique().tolist())
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# (写真アップローダー部分は前回同様のため中略)
# ... [uploaded_file の処理] ...

# --- 3. 釣果登録フォーム ---
with st.form("input_form"):
    date_in = st.date_input("📅 日付", value=default_datetime.date())
    time_in = st.time_input("⏰ 時刻", value=default_datetime.time())
    place_in = st.selectbox("📍 場所", options=place_options)
    
    # 選択された場所の緯度経度を取得 (マスターに登録されている前提)
    loc_data = m_df.loc[m_df["place_name"] == place_in]
    lat = loc_data["latitude"].values[0] if "latitude" in m_df.columns else 35.0
    lon = loc_data["longitude"].values[0] if "longitude" in m_df.columns else 135.0
    
    fish_in = st.text_input("🐟 魚種")
    lure_in = st.text_input("🎣 ルアー")
    length_in = st.slider("📏 全長 (cm)", 0.0, 150.0, 40.0, 1.0)
    memo_in = st.text_area("📝 備考")
    
    submit_button = st.form_submit_button("🚀 気象を自動取得して保存", use_container_width=True)

# --- 4. 保存処理（自動取得フェーズ） ---
if submit_button:
    with st.spinner('気象データと潮汐を計算中...'):
        target_dt = datetime.combine(date_in, time_in)
        
        # 気象データの取得
        temp, wind_s, wind_d = get_weather_data(lat, lon, target_dt)
        
        # 保存用データ作成
        new_data = pd.DataFrame([{
            "datetime": target_dt.strftime('%Y-%m-%d %H:%M'),
            "場所": place_in,
            "魚種": fish_in,
            "ルアー": lure_in,
            "全長_cm": length_in,
            "気温": temp,
            "風速": wind_s,
            "風向き": wind_d,
            "備考": memo_in
        }])
        
        # スプレッドシート更新
        updated_df = pd.concat([df, new_data], ignore_index=True)
        conn.update(spreadsheet=url, data=updated_df)
        
        st.success(f"✅ 保存完了！ 気温:{temp}℃ / 風速:{wind_s}m")
        st.cache_data.clear()
        st.rerun()

st.write("---")

# --- 3. 写真アップローダー（EXIF解析） ---
uploaded_file = st.file_uploader("📸 写真を選択（日時を自動反映）", type=['jpg', 'jpeg', 'png'])

if uploaded_file:
    img = Image.open(uploaded_file)
    exif = img._getexif()
    if exif:
        for tag_id, value in exif.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == 'DateTimeOriginal':
                default_datetime = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                st.success(f"✅ 写真から日時を読み取りました: {default_datetime.strftime('%Y-%m-%d %H:%M')}")

# --- 4. 釣果登録フォーム（ID紐付け） ---
with st.form("input_form", clear_on_submit=True):
    date_in = st.date_input("📅 日付", value=default_datetime.date())
    time_in = st.time_input("⏰ 時刻", value=default_datetime.time())
    
    place_in = st.selectbox("📍 場所", options=place_options)
    
    # 選ばれた場所からIDを自動特定（ここがポイント！）
    current_id = m_df.loc[m_df["place_name"] == place_in, "group_id"].values[0] if not m_df.empty else None
    
    fish_in = st.text_input("🐟 魚種", placeholder="スズキ")
    lure_in = st.text_input("🎣 ルアー", placeholder="カゲロウ125MD")
    length_in = st.slider("📏 全長 (cm)", 0.0, 150.0, 40.0, 1.0)
    memo_in = st.text_area("📝 備考")
    
    submit_button = st.form_submit_button("🚀 スプレッドシートに保存", use_container_width=True)

# --- 5. 保存処理 ---
if submit_button:
    try:
        new_data = pd.DataFrame([{
            "datetime": f"{date_in} {time_in}",
            "場所": place_in,
            "group_id": int(current_id), # 特定したIDを保存
            "魚種": fish_in,
            "ルアー": lure_in,
            "全長_cm": length_in,
            "備考": memo_in
        }])
        
        updated_df = pd.concat([df, new_data], ignore_index=True)
        conn.update(spreadsheet=url, data=updated_df)
        
        st.success(f"✅ {place_in} での釣果を登録しました！")
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"登録失敗: {e}")

