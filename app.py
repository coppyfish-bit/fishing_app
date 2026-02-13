import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from datetime import datetime
import cloudinary
import cloudinary.uploader
import io

# --- 1. Cloudinary設定 (Secretsから取得) ---
try:
    cloudinary.config(
        cloud_name = st.secrets["cloudinary"]["cloud_name"],
        api_key = st.secrets["cloudinary"]["api_key"],
        api_secret = st.secrets["cloudinary"]["api_secret"],
        secure = True
    )
except Exception as e:
    st.error("Cloudinaryの設定を確認してください。")

# --- 2. 関数定義: 位置情報の解析 ---
def get_geotagging(exif):
    if not exif: return None
    # GPSInfoのタグIDは 34853
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
        # Pillowのバージョンによりデータ形式が異なるためfloatに変換
        d = float(dms[0])
        m = float(dms[1])
        s = float(dms[2])
        decimal = d + (m / 60.0) + (s / 3600.0)
        if ref in ['S', 'W']: decimal = -decimal
        return decimal
    except: return None

# --- 3. 接続と初期化 ---
st.set_page_config(page_title="釣果記録アプリ", layout="centered")
st.title("🎣 釣果記録システム")

# セッション状態の初期化
if "data_ready" not in st.session_state: st.session_state.data_ready = False
if "lat" not in st.session_state: st.session_state.lat = None
if "lon" not in st.session_state: st.session_state.lon = None

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# --- 4. メインUI: 画像アップロード ---
uploaded_file = st.file_uploader("📸 釣果写真をアップロード", type=["jpg", "jpeg"])

if uploaded_file:
    img = Image.open(uploaded_file)
    st.image(img, caption="アップロード画像", use_container_width=True)
    
    # EXIFから位置情報を解析
    exif = img._getexif()
    geo = get_geotagging(exif)
    
    if geo:
        lat = get_decimal_from_dms(geo['GPSLatitude'], geo['GPSLatitudeRef'])
        lon = get_decimal_from_dms(geo['GPSLongitude'], geo['GPSLongitudeRef'])
        
        if lat and lon:
            st.session_state.lat = lat
            st.session_state.lon = lon
            st.session_state.data_ready = True
            st.success("📍 位置情報の取得に成功！")
        else:
            st.error("位置情報の数値変換に失敗しました。")
            st.session_state.data_ready = False
    else:
        st.warning("⚠️ この写真には位置情報(GPS)が含まれていません。")
        # GPSがない場合も手動入力できるようフラグを立てる場合はここを調整
        st.session_state.data_ready = False

# --- 5. 入力フォーム ---
if st.session_state.data_ready:
    with st.form("fishing_form"):
        st.subheader("📝 釣果の詳細を入力")
        
        # スマホで見やすい大きな数字表示
        col1, col2 = st.columns(2)
        col1.metric("緯度", f"{st.session_state.lat:.4f}")
        col2.metric("経度", f"{st.session_state.lon:.4f}")

        # --- 【ここが追加：魚種の選択と手入力】 ---
        fish_options = ["スズキ","ヒラスズキ","ボウズ","タチウオ","ターポン","チヌ","キビレ","コチ","ヒラメ","マダイ","キジハタ","カサゴ","ブリ","アジ","メバル","キス", "（手入力）"]
        selected_fish = st.selectbox("🐟 魚種を選択", fish_options)
        
        # 「（手入力）」が選ばれた時だけ入力欄を出す
        manual_fish_name = ""
        if selected_fish == "（手入力）":
            manual_fish_name = st.text_input("魚種名を入力してください", placeholder="例: カクレクマノミ")
        
        # 最終的な魚種名を決定
        final_fish_name = manual_fish_name if selected_fish == "（手入力）" else selected_fish
          # 【2. 全長調整】（★ここが重要：フォームの外に置く）
        st.write("📏 全長 (cm)")
        c1, c2, c3 = st.columns([1, 2, 1])
        
        # マイナスボタン
        if c1.button("➖", use_container_width=True):
            st.session_state.length_val = max(0.0, st.session_state.length_val - 1.0)
            st.rerun() # 値を更新して再描画
        
        # 中央の入力欄
        length_text = c2.text_input("数値入力（全角OK）", value=str(st.session_state.length_val), label_visibility="collapsed")
        st.session_state.length_val = normalize_float(length_text)
        
        # プラスボタン
        if c3.button("➕", use_container_width=True):
            st.session_state.length_val += 1.0
            st.rerun() # 値を更新して再描画
    
        st.markdown("---") # 区切り線
        place_name = st.text_input("📍 場所名", value="新規地点")
        lure = st.text_input("🪝 ルアー/仕掛け")
        angler = st.selectbox("👤 釣り人", ["長元", "川口","山川"])
        memo = st.text_area("🗒️ 備考")

        # スマホで押しやすい巨大な保存ボタン
        submit = st.form_submit_button("🚀 釣果を記録する", use_container_width=True, type="primary")

        if submit:
            try:
                with st.spinner("📊 データを保存中..."):
                    # ① Cloudinaryへ画像アップロード
                    uploaded_file.seek(0)
                    res = cloudinary.uploader.upload(uploaded_file, folder="fishing_app")
                    image_url = res.get("secure_url")
                    
                    # ② 保存データの作成
                    now = datetime.now()
                    save_data = {
                        "filename": image_url,
                        "datetime": now.strftime("%Y-%m-%d %H:%M"),
                        "date": now.strftime("%Y-%m-%d"),
                        "time": now.strftime("%H:%M"),
                        "lat": float(st.session_state.lat),
                        "lon": float(st.session_state.lon),
                        "気温": 0, "風速": 0, "風向": "不明", "降水量": 0,
                        "潮位_cm": 0, "月齢": 0, "潮名": "不明",
                        "次の満潮まで_分": 0, "次の干潮まで_分": 0,
                        "直前の満潮_時刻": "", "直前の干潮_時刻": "",
                        "潮位フェーズ": "不明",
                        "場所": place_name,
                        "魚種": fish_name,
                        "全長_cm": float(length),
                        "ルアー": lure,
                        "備考": memo,
                        "group_id": "default",
                        "観測所": "不明",
                        "釣り人": angler
                    }

                    # ③ スプレッドシートへ書き込み
                    current_df = conn.read(spreadsheet=url, ttl=0)
                    cols = ["filename","datetime","date","time","lat","lon","気温","風速","風向","降水量","潮位_cm","月齢","潮名","次の満潮まで_分","次の干潮まで_分","直前の満潮_時刻","直前の干潮_時刻","潮位フェーズ","場所","魚種","全長_cm","ルアー","備考","group_id","観測所","釣り人"]
                    new_row_df = pd.DataFrame([save_data])[cols]
                    
                    updated_df = pd.concat([current_df, new_row_df], ignore_index=True)
                    conn.update(spreadsheet=url, data=updated_df)
                    
                    st.success("🎉 記録完了！スプレッドシートを更新しました。")
                    st.balloons()
                    
                    # 状態をリセットして再起動
                    st.session_state.data_ready = False
                    time.sleep(2)
                    st.rerun()

            except Exception as e:
                st.error(f"❌ 保存に失敗しました: {e}")




