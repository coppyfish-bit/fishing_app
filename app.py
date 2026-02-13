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
    if valid_master.empty:
        return "新規地点", "default"

    # 距離計算 (1度 = 約111km)
    valid_master['dist_m'] = np.sqrt(
        ( (valid_master['latitude'] - lat) * 111000 )**2 + 
        ( (valid_master['longitude'] - lon) * 91000 )**2
    )
    
    nearest = valid_master.loc[valid_master['dist_m'].idxmin()]
    
    if nearest['dist_m'] <= 500:
        return nearest['place_name'], nearest['group_id']
    else:
        return "新規地点", "default"

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
    st.error(f"スプレッドシート接続エラー: {e}")
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
                st.session_state.detected_place = place
                st.session_state.group_id = gid
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
        st.session_state.length_val = max(0.0, st.session_state.length_val - 0.5)
        st.rerun()
    length_text = c2.text_input("全長入力", value=str(st.session_state.length_val) if st.session_state.length_val > 0 else "", placeholder="ここに全長を入力", label_visibility="collapsed")
    st.session_state.length_val = normalize_float(length_text)
    if c3.button("➕ 0.5", use_container_width=True):
        st.session_state.length_val += 0.5
        st.rerun()

    # 場所名入力
    place_name = st.text_input("📍 場所名", value=st.session_state.detected_place)
    lure = st.text_input("🪝 ルアー/仕掛け")
    angler = st.selectbox("👤 釣り人", ["長元", "川口", "山川"])
    memo = st.text_area("🗒️ 備考")

    if st.button("🚀 釣果を記録する", use_container_width=True, type="primary"):
        try:
            with st.spinner("📊 保存中..."):
                # 新規地点かつ場所名が入力されている場合、マスターに登録
                current_gid = st.session_state.group_id
                if st.session_state.detected_place == "新規地点" and place_name != "新規地点":
                    new_gid = int(df_master['group_id'].max()) + 1 if not df_master.empty else 0
                    new_place_df = pd.DataFrame([{
                        "group_id": new_gid,
                        "place_name": place_name,
                        "latitude": st.session_state.lat,
                        "longitude": st.session_state.lon
                    }])
                    # place_masterシートを更新
                    updated_master = pd.concat([df_master, new_place_df], ignore_index=True)
                    conn.update(spreadsheet=url, worksheet="place_master", data=updated_master)
                    current_gid = new_gid
                    st.info(f"🆕 新しい場所「{place_name}」をマスターに登録しました！")

                # 画像アップロード
                uploaded_file.seek(0)
                res = cloudinary.uploader.upload(uploaded_file, folder="fishing_app")
                image_url = res.get("secure_url")
                
                # 釣果データ保存
                now = datetime.now()
                save_data = {
                    "filename": image_url, "datetime": now.strftime("%Y-%m-%d %H:%M"),
                    "date": now.strftime("%Y-%m-%d"), "time": now.strftime("%H:%M"),
                    "lat": float(st.session_state.lat), "lon": float(st.session_state.lon),
                    "気温": 0, "風速": 0, "風向": "不明", "降水量": 0,
                    "潮位_cm": 0, "月齢": 0, "潮名": "不明",
                    "次の満潮まで_分": 0, "次の干潮まで_分": 0,
                    "直前の満潮_時刻": "", "直前の干潮_時刻": "",
                    "潮位フェーズ": "不明",
                    "場所": place_name, "魚種": final_fish_name,
                    "全長_cm": float(st.session_state.length_val), "ルアー": lure,
                    "備考": memo, "group_id": current_gid, "観測所": "不明", "釣り人": angler
                }

                df_main = conn.read(spreadsheet=url, ttl=0) # mainシート
                new_row = pd.DataFrame([save_data])
                updated_main = pd.concat([df_main, new_row], ignore_index=True)
                conn.update(spreadsheet=url, data=updated_main)
                
                st.success("🎉 釣果を記録しました！")
                st.balloons()
                st.session_state.data_ready = False
                st.session_state.length_val = 0.0
                time.sleep(2)
                st.rerun()
        except Exception as e:
            st.error(f"❌ 保存失敗: {e}")
