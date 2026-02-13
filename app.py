import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from datetime import datetime
import cloudinary
import cloudinary.uploader

# --- 1. Cloudinary設定 ---
# Secretsから設定を読み込みます
try:
    cloudinary.config(
        cloud_name = st.secrets["cloudinary"]["cloud_name"],
        api_key = st.secrets["cloudinary"]["api_key"],
        api_secret = st.secrets["cloudinary"]["api_secret"],
        secure = True
    )
except:
    st.error("Cloudinaryの設定がSecretsに見つかりません。")

# --- 2. 関数定義: 位置情報の解析 ---
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

# --- 3. 接続と初期化 ---
st.title("🎣 釣果自動記録システム")

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    # セッション状態で解析データを保持
    if "data_ready" not in st.session_state: st.session_state.data_ready = False
    if "form_data" not in st.session_state: st.session_state.form_data = {}
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# --- 4. 画像アップロードと解析 ---
uploaded_file = st.file_uploader("写真をアップロード (JPEG形式)", type=["jpg", "jpeg"])

# 1. 写真アップロード（スマホの「写真ライブラリ」から選ぶ）
uploaded_file = st.file_uploader("📸 釣果写真をアップロード", type=["jpg", "jpeg"])

if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, caption="プレビュー", use_container_width=True)
    
    exif = img._getexif()
    geo = get_geotagging(exif)
    
    # ここで位置情報の解析結果を判定
    if geo:
        lat = get_decimal_from_dms(geo['GPSLatitude'], geo['GPSLatitudeRef'])
        lon = get_decimal_from_dms(geo['GPSLongitude'], geo['GPSLongitudeRef'])
        
        if lat and lon:
            st.success(f"📍 位置を特定しました")
            st.session_state.data_ready = True
            st.session_state.lat = lat
            st.session_state.lon = lon
        else:
            st.error("位置情報の計算に失敗しました。")
            st.session_state.data_ready = False
    else:
        st.error("❌ この写真にはGPSが含まれていません。")
        st.session_state.data_ready = False
        
# --- 5. フォーム入力 ---
if st.session_state.data_ready:
    with st.form("fishing_form"):
        st.subheader("詳細情報を入力")
        fish_name = st.selectbox("🐟 魚種", ["シーバス", "チヌ", "アオリイカ", "真鯛", "その他"])
        length = st.number_input("全長_cm", value=0.0, step=0.1)
        lure = st.text_input("ルアー", value="")
        angler = st.radio("👤 釣り人", ["自分", "川口","山川","その他"], horizontal=True)
        place = st.text_input("場所名", value="新規地点")
        memo = st.text_area("備考", value="")
        
        st.form_submit_button("🚀 釣果を記録する", use_container_width=True, type="primary")

        if submit:
            try:
                with st.spinner("💾 保存中..."):
                    # 1. Cloudinaryにアップロード
                    uploaded_file.seek(0)
                    res = cloudinary.uploader.upload(uploaded_file, folder="fishing_app")
                    image_url = res.get("secure_url")
                    
                    # 2. 保存データの作成（スプレッドシートのカラム順に合わせる）
                    now = datetime.now()
                    save_data = {
                        "filename": image_url,
                        "datetime": now.strftime("%Y-%m-%d %H:%M"),
                        "date": now.strftime("%Y-%m-%d"),
                        "time": now.strftime("%H:%M"),
                        "lat": float(st.session_state.lat),
                        "lon": float(st.session_state.lon),
                        "気温": 0, "風速": 0, "風向": "不明", "降水量": 0, # 気象系は後ほど
                        "潮位_cm": 0, "月齢": 0, "潮名": "不明", # 潮汐系も後ほど
                        "次の満潮まで_分": 0, "次の干潮まで_分": 0,
                        "直前の満潮_時刻": "", "直前の干潮_時刻": "",
                        "潮位フェーズ": "不明",
                        "場所": place,
                        "魚種": fish_name,
                        "全長_cm": float(length),
                        "ルアー": lure,
                        "備考": memo,
                        "group_id": "default",
                        "観測所": "不明",
                        "釣り人": angler
                    }
                    
                    # 3. スプレッドシートへ書き込み
                    existing_df = conn.read(spreadsheet=url, ttl=0)
                    # カラム順を確実に一致させる
                    cols = ["filename","datetime","date","time","lat","lon","気温","風速","風向","降水量","潮位_cm","月齢","潮名","次の満潮まで_分","次の干潮まで_分","直前の満潮_時刻","直前の干潮_時刻","潮位フェーズ","場所","魚種","全長_cm","ルアー","備考","group_id","観測所","釣り人"]
                    new_row_df = pd.DataFrame([save_data])[cols]
                    
                    updated_df = pd.concat([existing_df, new_row_df], ignore_index=True)
                    conn.update(spreadsheet=url, data=updated_df)
                    
                    st.success("✅ スプレッドシートに保存しました！")
                    st.balloons()
                    st.session_state.data_ready = False
                    time.sleep(2)
                    st.rerun()
                    
            except Exception as e:
                st.error(f"保存エラー: {e}")





