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
import ephem  # 月齢計算用のライブラリ（要：pip install pyephem）

# --- 1. Cloudinary設定 ---
try:
    cloudinary.config(
        cloud_name = st.secrets["cloudinary"]["cloud_name"],
        api_key = st.secrets["cloudinary"]["api_key"],
        api_secret = st.secrets["cloudinary"]["api_secret"],
        secure = True
    )
except Exception as e:
    st.error("Cloudinaryの設定を確認してください。")

# --- 2. 関数定義 ---
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

# 距離判定付きの場所検索関数（500m制限）
def find_nearest_place(lat, lon, df_master):
    if lat == 0.0 or lon == 0.0 or df_master.empty:
        return "新規地点", "default"
    valid_master = df_master.dropna(subset=['latitude', 'longitude']).copy()
    if valid_master.empty: return "新規地点", "default"
    valid_master['dist_m'] = np.sqrt(((valid_master['latitude'] - lat) * 111000 )**2 + ((valid_master['longitude'] - lon) * 91000 )**2)
    nearest = valid_master.loc[valid_master['dist_m'].idxmin()]
    return (nearest['place_name'], nearest['group_id']) if nearest['dist_m'] <= 500 else ("新規地点", "default")

# 月齢計算関数（修正版）
def get_moon_age(date_obj):
    e_date = ephem.Date(date_obj)
    prev_new = ephem.previous_new_moon(e_date)
    return round(float(e_date - prev_new), 1)

# 【追加】月齢から潮名を判定する関数
def get_tide_name(moon_age):
    # 月齢を整数に丸めて判定（一般的な釣り用カレンダーの基準）
    age = int(round(moon_age)) % 30
    if age in [30, 0, 1, 14, 15, 16]: return "大潮"
    elif age in [2, 3, 4, 11, 12, 13, 17, 18, 19, 26, 27, 28]: return "中潮"
    elif age in [5, 6, 7, 8, 20, 21, 22, 23]: return "小潮"
    elif age in [9, 24]: return "長潮"
    elif age in [10, 25]: return "若潮"
    else: return "不明"

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

    place_name = st.text_input("📍 場所名", value=st.session_state.detected_place)
    lure = st.text_input("🪝 ルアー/仕掛け")
    angler = st.selectbox("👤 釣り人", ["長元", "川口", "山川"])
    memo = st.text_area("🗒️ 備考")

    if st.button("🚀 釣果を記録する", use_container_width=True, type="primary"):
        try:
            with st.spinner("📊 保存中..."):
                now = datetime.now()
                # 【追加】月齢を計算
                moon_age = get_moon_age(now)

                # マスター登録処理
                current_gid = st.session_state.group_id
                if st.session_state.detected_place == "新規地点" and place_name != "新規地点":
                    new_gid = int(df_master['group_id'].max()) + 1 if not df_master.empty else 0
                    new_place_df = pd.DataFrame([{"group_id": new_gid, "place_name": place_name, "latitude": st.session_state.lat, "longitude": st.session_state.lon}])
                    conn.update(spreadsheet=url, worksheet="place_master", data=pd.concat([df_master, new_place_df], ignore_index=True))
                    current_gid = new_gid

                # 画像アップロード
                uploaded_file.seek(0)
                res = cloudinary.uploader.upload(uploaded_file, folder="fishing_app")
                
                # 保存データ
                save_data = {
                    "filename": res.get("secure_url"), "datetime": now.strftime("%Y-%m-%d %H:%M"),
                    "date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M"),
                    "lat": float(st.session_state.lat), "lon": float(st.session_state.lon),
                    "気温": 0, "風速": 0, "風向": "不明", "降水量": 0,
                    "潮位_cm": 0, "月齢": moon_age,  # 【自動化完了】
                    "潮名": "不明", "次の満潮まで_分": 0, "次の干潮まで_分": 0,
                    "直前の満潮_時刻": "", "直前の干潮_時刻": "", "潮位フェーズ": "不明",
                    "場所": place_name, "魚種": final_fish_name,
                    "全長_cm": float(st.session_state.length_val), "ルアー": lure,
                    "備考": memo, "group_id": current_gid, "観測所": "不明", "釣り人": angler
                }

                df_main = conn.read(spreadsheet=url, ttl=0)
                conn.update(spreadsheet=url, data=pd.concat([df_main, pd.DataFrame([save_data])], ignore_index=True))
                
                st.success(f"🎉 記録完了！ (月齢: {moon_age})")
                st.balloons()
                st.session_state.data_ready = False
                st.session_state.length_val = 0.0
                time.sleep(2); st.rerun()
        except Exception as e:
            st.error(f"❌ 保存失敗: {e}")


