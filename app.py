import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime, timedelta # timedeltaを追加
import requests

# --- 1. 気象データ取得関数 (48時間降水量対応) ---
def get_weather_data(lat, lon, dt):
    try:
        # 48時間前から取得するために開始日を計算
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
        
        # 釣った瞬間のリスト内インデックスを計算
        # 48時間分(2日分) + 当日の経過時間
        current_idx = (len(response['hourly']['temperature_2m']) - 25) + dt.hour
        
        temp = response['hourly']['temperature_2m'][current_idx]
        wind_s = response['hourly']['windspeed_10m'][current_idx]
        
        # 48時間合計降水量の計算
        precip_list = response['hourly']['precipitation'][:current_idx+1]
        total_precip_48h = sum(precip_list[-48:])
        
        return temp, wind_s, round(total_precip_48h, 1)
    except Exception as e:
        return None, None, None

# --- 2. 初期設定 ---
st.set_page_config(page_title="Fishing App", layout="wide")
st.title("🎣 プロ仕様・自動補完ログ")

# ★重要★ エラー回避のため、まず最初にデフォルト値を決める
default_datetime = datetime.now()

## --- データの読み込み部分を修正 ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    
    # ttl=0 (毎回読み込む) から ttl="10m" (10分間キャッシュ) に変更
    # これで Google へのリクエスト回数が激減します
    df = conn.read(spreadsheet=url, ttl="10m")
    
    # 場所マスターも同様にキャッシュ
    m_df = conn.read(spreadsheet=url, worksheet="place_master", ttl="10m")
    place_options = sorted(m_df["place_name"].unique().tolist())
except Exception as e:
    # 429エラーが出た時のための分かりやすい表示
    if "429" in str(e):
        st.error("🚫 Google APIの制限に達しました。1分ほど待ってから再読み込みしてください。")
    else:
        st.error(f"接続エラー: {e}")
    st.stop()

# --- 3. 写真アップローダー（EXIF解析） ---
uploaded_file = st.file_uploader("📸 写真を選択（日時を自動反映）", type=['jpg', 'jpeg', 'png'])

if uploaded_file:
    img = Image.open(uploaded_file)
    exif = img._getexif()
    if exif:
        for tag_id, value in exif.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == 'DateTimeOriginal':
                # 写真の日時で default_datetime を上書き
                default_datetime = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                st.success(f"✅ 写真から日時を読み取りました: {default_datetime.strftime('%Y-%m-%d %H:%M')}")

# --- 4. 釣果登録フォーム ---
with st.form("input_form", clear_on_submit=True):
    # ここで使う default_datetime は必ず存在するのでエラーになりません
    date_in = st.date_input("📅 日付", value=default_datetime.date())
    time_in = st.time_input("⏰ 時刻", value=default_datetime.time())
    
    place_in = st.selectbox("📍 場所", options=place_options)
    
    # 緯度経度の取得（マスターに latitude, longitude 列がある前提。なければデフォルト値）
    loc_data = m_df.loc[m_df["place_name"] == place_in]
    lat = loc_data["latitude"].values[0] if "latitude" in m_df.columns else 35.0
    lon = loc_data["longitude"].values[0] if "longitude" in m_df.columns else 135.0
    
    fish_in = st.text_input("🐟 魚種", placeholder="シーバス")
    lure_in = st.text_input("🎣 ルアー")
    length_in = st.slider("📏 全長 (cm)", 0.0, 150.0, 40.0, 1.0)
    memo_in = st.text_area("📝 備考")
    
    submit_button = st.form_submit_button("🚀 気象を自動取得して保存", use_container_width=True)

if submit_button:
    with st.spinner('データを解析・保存中...'):
        target_dt = datetime.combine(date_in, time_in)
        temp, wind_s, precip_48h = get_weather_data(lat, lon, target_dt)
        
        # 保存するデータの辞書（ここを増やすだけでOK）
        save_data = {
            "datetime": target_dt.strftime('%Y-%m-%d %H:%M'),
            "場所": place_in,
            "group_id": int(current_id),
            "魚種": fish_in,
            "ルアー": lure_in,
            "全長_cm": length_in,
            "気温": temp,
            "風速": wind_s,
            "48h降水量": precip_48h,
            "備考": memo_in,
            # 将来的に「潮名」などを追加したくなったらここに行を増やすだけ！
            # "潮名": get_tide_name(target_dt), 
        }
        
        new_row_df = pd.DataFrame([save_data])
        
        # 既存のスプレッドシートに新しい列があれば、それを含めて結合
        updated_df = pd.concat([df, new_row_df], ignore_index=True)
        
        # スプレッドシートを更新
        conn.update(spreadsheet=url, data=updated_df)
        
        st.success("✅ 正常に記録されました！")
        st.cache_data.clear()
        st.rerun()

st.write("---")
