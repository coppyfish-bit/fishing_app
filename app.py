import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime, timedelta
import requests
import math
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account

# --- 1. 各種関数定義 ---
def upload_to_drive(uploaded_file):
    # 1. StreamlitのSecretsから認証情報を取得
    creds_dict = st.secrets["connections"]["gsheets"]
    creds = service_account.Credentials.from_service_account_info(creds_dict)
    
    # 2. ドライブサービスを構築
    service = build('drive', 'v3', credentials=creds)
    
    # 3. 保存先フォルダID (ここを書き換えてください！)
    folder_id = "1bmgT1IBAZd7U37dKkUBBoFx2TpR6BMXI" 
    
    # 4. ファイルの設定
    file_metadata = {
        'name': f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}",
        'parents': [folder_id]
    }
    
    # 5. ファイルをバイナリとして読み込み
    media = MediaIoBaseUpload(io.BytesIO(uploaded_file.getvalue()), 
                              mimetype='image/jpeg', 
                              resumable=True)
    
    # 6. アップロード実行
    file = service.files().create(body=file_metadata, 
                                  media_body=media, 
                                  fields='id').execute()
    
    # 7. 画像の直リンクURLを返す
    return f"https://drive.google.com/uc?id={file.get('id')}"
    
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


# --- 3. 接続の初期化 (ここで conn を作る) ---
try:
    # 接続オブジェクトの作成
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    
    # 【節約術】Session State を使って読み込み回数を減らす
    # 1分間（60s）はAPIを叩かず、手元のデータ(session_state)を使います
    if "df" not in st.session_state:
        st.session_state.df = conn.read(spreadsheet=url, ttl="60s")
    
    # 場所マスターも同様に保持
    if "m_df" not in st.session_state:
        st.session_state.m_df = conn.read(spreadsheet=url, worksheet="place_master", ttl="60s")

    # 共通変数として使いやすくしておく
    df = st.session_state.df
    m_df = st.session_state.m_df

except Exception as e:
    st.error(f"接続の初期化に失敗しました: {e}")
    st.stop()  # ここで止めれば、これ以降の NameError は起きません
    
# --- 2. メイン UI 制御 ---
st.set_page_config(page_title="Fishing AI Log", layout="centered")
st.title("🎣 釣果統合ログシステム")

# --- タブの作成 ---
tab1, tab2 = st.tabs(["📝 釣果登録", "🔧 履歴の修正・削除"])

# ==========================================
# タブ1: 釣果登録 (既存のコードをここに移動)
# ==========================================
with tab1:
    # (ここに今までの写真アップロード〜保存処理のコードをすべて入れます)
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

# --- 魚種登録セクション ---
st.subheader("🐟 魚種")

# 選択肢のリスト（よく釣れるものを入れておくと楽です）
fish_options = ["スズキ", "ヒラスズキ", "ターポン", "タチウオ", "コチ", "ヒラメ","カサゴ", "クロダイ", "キビレ","キジハタ","マダイ","その他（手入力）"]
selected_fish = st.selectbox("魚種を選択", fish_options)
# 2. 手入力欄（常に表示）
# placeholder を入れることで、何を書けばいいか分かりやすくします
manual_fish_name = st.text_input("魚種名（手入力）", placeholder="例：アカハタ、または魚種の補足など")

# 保存用の最終的な魚種名を決定するロジック
if manual_fish_name:
    # 手入力があればそれを優先、または「選択肢 + 手入力」とする
    final_fish_name = manual_fish_name
else:
    final_fish_name = selected_fish
# 釣果入力
# --- カスタムCSS（フィッシュメジャー風） ---
st.markdown("""
    <style>
    .stSlider [data-baseweb="slider"] {
        height: 60px !important;
        width: calc(100% - 12px) !important; 
        margin: 0 auto !important;
        background-color: #FFFFFF !important;
        border: 2px solid #001f3f !important;
        border-radius: 4px !important;

        /* 目盛り線の描画 */
        background-image: 
            linear-gradient(90deg, #001f3f 3px, transparent 3px),
            linear-gradient(90deg, #001f3f 1px, transparent 1px) !important;
        
        /* ↓【最重要】線の間隔を120cmの「区切り数」で正確に指定 */
        /* 120に行くにつれて「矢印が線より左に遅れる」なら、数字を小さく（例: 8.32%） */
        /* 120に行くにつれて「矢印が線より右に追い越す」なら、数字を大きく（例: 8.34%） */
        background-size: 8.08% 100%, 4.04% 50% !important;
        
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
current_len = st.session_state.get('len_slider', 0.0)
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
        margin-bottom: -20px;  /* ここを大きくマイナスにすると、数字が下の要素（バー）に重なります */
        position: relative; 
        z-index: 10; 
        pointer-events: none; 
        line-height: 60px;     /* バーの高さと同じにする */
        font-family: 'Arial Black', sans-serif;
        transform: translateX(8px); /* ←これを追加・調整！ */
        padding: 0px;  /* ←ここを調整！ (0 左右の余白) */
        <div style="
        ...
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

st.markdown("**ルアー・仕掛け**")
lure_sel = st.text_input("例：カゲロウ125MD ←数字、英字は半角でお願いします。コピペ用 50s 55 60f 60s 60ES 70f 70s 70ES 73 80f 80s 82s 87 88 95f 95ss 100f 100s 100ss 110f 110s　111f 120f 120s 124f 125f 125ss 130f 130s 140f 140s 150f 150s 156MD 160f 160s 165f 170f 170J 180f 190f 190ss")
lure_extra = st.text_input("詳細・カラー (任意)")
lure_in = ", ".join(lure_sel) + (f" ({lure_extra})" if lure_extra else "")

st.markdown("**メモ**")
memo_in = st.text_area("", placeholder="ヒットパターンなど", label_visibility="collapsed")

st.markdown("---")
submit = st.button("🚀 釣果を保存する", use_container_width=True, type="primary")

# --- 保存処理 ---
if submit:
    if not final_place_name:
        st.error("⚠️ 場所名を入力してください。")
    else:
        with st.spinner('📸 画像をアップロード中...'):
            # --- ここを追加 ---
            drive_url = ""
            if uploaded_file:
                try:
                    drive_url = upload_to_drive(uploaded_file)
                except Exception as e:
                    st.error(f"画像アップロード失敗: {e}")
            # -----------------
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
                st.success(f"✅ {final_place_name} での釣果を保存しました！")
                st.balloons()

                # --- 保存した情報のサマリー表示を追加 ---
                st.markdown("### 📊 保存されたフィールドデータ")
                
                # 3列で見やすく表示
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("潮位", f"{t_info.get('潮位_cm')} cm")
                    st.caption(f"潮名: {t_name}")
                with m2:
                    st.metric("気温", f"{temp} ℃")
                    st.caption(f"降水: {prec} mm")
                with m3:
                    st.metric("風速", f"{wind_s} m/s")
                    st.caption(f"風向: {get_wind_direction_label(wind_d)}")

                st.info(f"📍 潮位フェーズ: {t_info.get('潮位フェーズ')} / 月齢: {get_moon_age(target_dt)}")
                # --------------------------------------

                st.cache_data.clear()
                st.cache_data.clear()
            except Exception as e:
                st.error(f"❌ 書き込みエラー: {e}")

    st.subheader("新しい釣果を記録する")
    # ... 既存のコード ...

# ==========================================
# タブ2: 釣果の修正・削除
# ==========================================
# --- Googleドライブのリンクを直接表示用に変換する関数 ---
def convert_google_drive_url(url):
    # 通常の表示用URLを直接参照用URLに書き換える
    if "drive.google.com" in url:
        file_id = url.split('/')[-2] if "/view" in url else url.split('id=')[-1]
        return f"https://lh3.googleusercontent.com/u/0/d/{file_id}"
    return url
    
with tab2:
    st.subheader("📸 直近5件の履歴（詳細修正・削除）")

    # API制限対策：手動リロードボタン
    if st.button("🔄 最新の履歴に更新"):
        st.cache_data.clear()
        if 'df' in st.session_state:
            del st.session_state.df
        st.rerun()

    try:
        # 共通部分で読み込んだ session_state のデータを使用
        edit_df = st.session_state.df
        
        if edit_df is None or edit_df.empty:
            st.info("履歴がまだありません。")
        else:
            # 【ここから重要】tryの直下のインデントを正しく揃える
            target_df = edit_df.tail(5).copy().iloc[::-1]
            
            for index, row in target_df.iterrows():
                # タイトルに基本情報を表示
                with st.expander(f"📌 {row['date']} | {row['魚種']} | {row['場所']}"):
                    
                    # --- 1. 画像の直接表示 ---
                    # filenameにURLが入っている場合のみ表示を試みる
                    img_url = str(row.get('filename', ''))
                    if "http" in img_url:
                        direct_url = convert_google_drive_url(img_url)
                        st.image(direct_url, caption=f"登録写真: {row['魚種']}", use_container_width=True)
                    
                    # --- 2. 修正項目のレイアウト ---
                    col1, col2 = st.columns(2)
                    with col1:
                        u_fish = st.text_input("🐟 魚種", value=row['魚種'], key=f"f_{index}")
                        u_place = st.text_input("📍 場所", value=row['場所'], key=f"p_{index}")
                        u_size = st.number_input("📏 サイズ(cm)", value=float(row['全長_cm']), step=0.5, key=f"s_{index}")
                        u_lure = st.text_input("🏹 ルアー・仕掛け", value=row['ルアー'], key=f"l_{index}")

                    with col2:
                        # 潮位や気温が空(NaN)の場合の対策
                        t_val = int(row['潮位_cm']) if pd.notnull(row['潮位_cm']) else 0
                        te_val = float(row['気温']) if pd.notnull(row['気温']) else 0.0
                        
                        u_tide = st.number_input("🌊 潮位(cm)", value=t_val, key=f"t_{index}")
                        u_temp = st.number_input("🌡️ 気温(℃)", value=te_val, step=0.1, key=f"te_{index}")
                        u_wind = st.text_input("💨 風情報", value=f"{row['風向']} {row['風速']}m/s", key=f"w_{index}")

                    u_memo = st.text_area("📝 メモ", value=row['備考'], key=f"m_{index}")

                    # --- 3. 更新・削除ボタン ---
                    b_col1, b_col2 = st.columns(2)
                    
                    if b_col1.button("🆙 修正を保存", key=f"up_btn_{index}", use_container_width=True, type="primary"):
                        edit_df.at[index, '魚種'] = u_fish
                        edit_df.at[index, '場所'] = u_place
                        edit_df.at[index, '全長_cm'] = u_size
                        edit_df.at[index, 'ルアー'] = u_lure
                        edit_df.at[index, '潮位_cm'] = u_tide
                        edit_df.at[index, '気温'] = u_temp
                        edit_df.at[index, '備考'] = u_memo
                        
                        conn.update(spreadsheet=url, data=edit_df)
                        # キャッシュを消してリロード
                        st.cache_data.clear()
                        if 'df' in st.session_state:
                            del st.session_state.df
                        st.success("修正を反映しました！")
                        st.rerun()

                    if b_col2.button("🗑️ データを削除", key=f"del_btn_{index}", use_container_width=True):
                        edit_df = edit_df.drop(index)
                        conn.update(spreadsheet=url, data=edit_df)
                        st.cache_data.clear()
                        if 'df' in st.session_state:
                            del st.session_state.df
                        st.warning("データを削除しました。")
                        st.rerun()

    except Exception as e:
        st.error(f"履歴の表示中にエラーが発生しました: {e}")



















































































