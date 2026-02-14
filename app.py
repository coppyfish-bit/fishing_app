import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from datetime import datetime, timedelta # timedeltaを追加
import cloudinary
import cloudinary.uploader
import unicodedata
import io
import numpy as np
import ephem
import requests
from PIL import Image, ExifTags

def safe_strptime(date_str, fmt='%Y/%m/%d %H:%M'):
    """ミリ秒などが混入していても、フォーマットに合う長さだけ切り取って解析する"""
    if not date_str: return None
    # 指定されたフォーマットの文字数（例: %Y/%m/%d %H:%M は 16文字）だけ抽出
    target_len = len(datetime.now().strftime(fmt))
    clean_str = str(date_str).replace("-", "/").strip()[:target_len]
    return datetime.strptime(clean_str, fmt)

# --- 1. 設定 ---
try:
    cloudinary.config(
        cloud_name = st.secrets["cloudinary"]["cloud_name"],
        api_key = st.secrets["cloudinary"]["api_key"],
        api_secret = st.secrets["cloudinary"]["api_secret"],
        secure = True
    )
except Exception as e:
    st.error("Cloudinaryの設定を確認してください。")

TIDE_STATIONS = [
    # --- 熊本・有明海・八代海エリア ---
    {"name": "苓北", "lat": 32.4667, "lon": 130.0333, "code": "RH"},
    {"name": "三角", "lat": 32.6167, "lon": 130.4500, "code": "MS"},
    {"name": "本渡瀬戸", "lat": 32.4333, "lon": 130.2167, "code": "HS"},
    {"name": "八代", "lat": 32.5167, "lon": 130.5667, "code": "O5"},
    {"name": "水俣", "lat": 32.2000, "lon": 130.3667, "code": "O7"},
    {"name": "熊本", "lat": 32.7500, "lon": 130.5667, "code": "KU"},
    {"name": "大牟田", "lat": 33.0167, "lon": 130.4167, "code": "O6"},
    {"name": "大浦", "lat": 32.9833, "lon": 130.2167, "code": "OU"},
    {"name": "口之津", "lat": 32.6000, "lon": 130.2000, "code": "KT"},
    
    # --- 九州他エリア ---
    {"name": "長崎", "lat": 32.7333, "lon": 129.8667, "code": "NS"},
    {"name": "佐世保", "lat": 33.1500, "lon": 129.7167, "code": "QD"},
    {"name": "博多", "lat": 33.6167, "lon": 130.4000, "code": "QF"},
    {"name": "鹿児島", "lat": 31.6000, "lon": 130.5667, "code": "KG"},
    {"name": "枕崎", "lat": 31.2667, "lon": 130.3000, "code": "MK"},
    {"name": "油津", "lat": 31.5833, "lon": 131.4167, "code": "AB"},
    
    # --- 主要都市・その他 ---
    {"name": "東京", "lat": 35.6500, "lon": 139.7667, "code": "TK"},
    {"name": "横浜", "lat": 35.4500, "lon": 139.6500, "code": "QS"},
    {"name": "名古屋", "lat": 35.0833, "lon": 136.8833, "code": "NG"},
    {"name": "大阪", "lat": 34.6500, "lon": 135.4333, "code": "OS"},
    {"name": "神戸", "lat": 34.6833, "lon": 135.1833, "code": "KB"},
    {"name": "広島", "lat": 34.3500, "lon": 132.4667, "code": "Q8"},
    {"name": "高松", "lat": 34.3500, "lon": 134.0500, "code": "TA"},
    {"name": "高知", "lat": 33.5000, "lon": 133.5667, "code": "KC"},
    {"name": "那覇", "lat": 26.2167, "lon": 127.6667, "code": "NH"}
]

# --- 2. 関数定義 ---
# (既存の get_geotagging, get_decimal_from_dms, normalize_float, find_nearest_place, get_moon_age, get_tide_name は維持)
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

def find_nearest_place(lat, lon, df_master):
    if lat == 0.0 or lon == 0.0 or df_master.empty:
        return "新規地点", "default"
    valid_master = df_master.dropna(subset=['latitude', 'longitude']).copy()
    if valid_master.empty: return "新規地点", "default"
    valid_master['dist_m'] = np.sqrt(((valid_master['latitude'] - lat) * 111000 )**2 + ((valid_master['longitude'] - lon) * 91000 )**2)
    nearest = valid_master.loc[valid_master['dist_m'].idxmin()]
    return (nearest['place_name'], nearest['group_id']) if nearest['dist_m'] <= 500 else ("新規地点", "default")

def get_moon_age(date_obj):
    e_date = ephem.Date(date_obj)
    prev_new = ephem.previous_new_moon(e_date)
    return round(float(e_date - prev_new), 1)

def get_tide_name(moon_age):
    age = int(round(moon_age)) % 30
    if age in [30, 0, 1, 14, 15, 16]: return "大潮"
    elif age in [2, 3, 4, 11, 12, 13, 17, 18, 19, 26, 27, 28]: return "中潮"
    elif age in [5, 6, 7, 8, 20, 21, 22, 23]: return "小潮"
    elif age in [9, 24]: return "長潮"
    elif age in [10, 25]: return "若潮"
    else: return "不明"

# 最寄りの潮位観測所を探す
def find_nearest_tide_station(lat, lon):
    distances = []
    for s in TIDE_STATIONS:
        d = np.sqrt((s['lat'] - lat)**2 + (s['lon'] - lon)**2)
        distances.append(d)
    return TIDE_STATIONS[np.argmin(distances)]

# 気象庁から潮位(cm)を取得・計算
def get_tide_details(station_code, dt):
    try:
        # 秒やミリ秒を切り捨てた「分」までの基準時刻を作成
        base_dt = datetime.strptime(dt.strftime('%Y%m%d%H%M'), '%Y%m%d%H%M')
        
        # 仕様に合わせた年月日文字列の作成 (73-78カラム用)
        target_ymd = base_dt.strftime('%y') + f"{base_dt.month:2d}" + f"{base_dt.day:2d}"
        
        url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{base_dt.year}/{station_code}.txt"
        res = requests.get(url, timeout=10)
        if res.status_code != 200: return None
        
        lines = res.text.splitlines()
        day_data = None
        
        # 1. 該当する日の行を特定
        for line in lines:
            if len(line) < 80: continue
            if line[72:78] == target_ymd and line[78:80] == station_code:
                day_data = line
                break
        
        if not day_data: return None

        # 2. 毎時潮位の取得 (1-72カラム)
        hourly = []
        for i in range(24):
            val = day_data[i*3 : (i+1)*3].strip()
            hourly.append(int(val))
        
        # 現在時刻の潮位計算
        t1 = hourly[base_dt.hour]
        t2 = hourly[base_dt.hour+1] if base_dt.hour < 23 else hourly[base_dt.hour]
        current_cm = int(round(t1 + (t2 - t1) * (base_dt.minute / 60.0)))

        # 3. 満干潮時刻の抽出 (満潮 81-108 / 干潮 109-136)
        event_times = []
        today_prefix = dt.strftime('%Y%m%d')

        # 満潮 (index 80から7文字×4)
        for i in range(4):
            start = 80 + (i * 7)
            time_part = day_data[start : start+4].strip()
            if time_part and time_part != "9999":
                clean_time = time_part.zfill(4)
                # --- ここを修正：strptimeを物理的に安全にする ---
                try:
                    # 時刻文字列を確実に8文字(YYYYMMDD) + 4文字(HHMM) = 12文字で切り落とす
                    raw_str = (today_prefix + clean_time)[:12]
                    ev_time = datetime.strptime(raw_str, '%Y%m%d%H%M')
                    event_times.append({"time": ev_time, "type": "満潮"})
                except:
                    continue

        # 干潮 (index 108から7文字×4)
        for i in range(4):
            start = 108 + (i * 7)
            time_part = day_data[start : start+4].strip()
            if time_part and time_part != "9999":
                clean_time = time_part.zfill(4)
                # --- ここを修正：strptimeを物理的に安全にする ---
                try:
                    raw_str = (today_prefix + clean_time)[:12]
                    ev_time = datetime.strptime(raw_str, '%Y%m%d%H%M')
                    event_times.append({"time": ev_time, "type": "干潮"})
                except:
                    continue

        # 4. フェーズ計算
        phase_text = "不明"
        prev_ev = next((e for e in reversed(event_times) if e['time'] <= base_dt), None)
        next_ev = next((e for e in event_times if e['time'] > base_dt), None)

        if prev_ev and next_ev:
            duration = (next_ev['time'] - prev_ev['time']).total_seconds()
            elapsed = (base_dt - prev_ev['time']).total_seconds()
            if duration > 0:
                step = max(1, min(9, int((elapsed / duration) * 10)))
                phase_text = f"上げ{step}分" if prev_ev['type'] == "干潮" else f"下げ{step}分"

        return {"cm": current_cm, "phase": phase_text, "events": event_times}

    except Exception as e:
        # ここでエラーが出た場合、詳細を表示
        st.error(f"潮位解析内部エラー: {e}")
        return None
# 【修正】Open-Meteoを使用した過去48時間降水量対応の気象取得関数
def get_weather_data_openmeteo(lat, lon, dt):
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
        
        # 配列の最後から現在時刻に最も近いインデックスを特定
        # 48時間以上のデータが返ってくるため、末尾付近から計算
        idx = (len(h['temperature_2m']) - 25) + dt.hour
        
        temp = h['temperature_2m'][idx]
        wind_speed = round(h['windspeed_10m'][idx] / 3.6, 1) # km/h -> m/s 変換
        wind_deg = h['winddirection_10m'][idx]
        
        # 過去48時間の合計降水量
        precip_48h = round(sum(h['precipitation'][:idx+1][-48:]), 1)

        # 16方位変換
        def get_wind_dir(deg):
            dirs = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
            return dirs[int((deg + 11.25) / 22.5) % 16]
        
        return temp, wind_speed, get_wind_dir(wind_deg), precip_48h
    except Exception as e:
        return None, None, "不明", 0.0

# --- 3. 以降、初期設定・画像アップロード・入力画面は既存と同じ ---
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

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    df_master = conn.read(spreadsheet=url, worksheet="place_master")
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# --- try-except の外に出して、確実に行が実行されるようにする ---
uploaded_file = st.file_uploader("釣果写真をアップロード", type=["jpg", "jpeg", "png", "heic"])

if uploaded_file:
    # 1. 画像の読み込み
    img_for_upload = Image.open(uploaded_file)
    
    # 2. EXIFデータの解析
    exif = img_for_upload._getexif()
    temp_dt = None
    
    if exif:
        for tag_id, value in exif.items():
            tag_name = ExifTags.TAGS.get(tag_id, tag_id)
            if tag_name == 'DateTimeOriginal':
                try:
                    # ミリ秒やゴミを物理的にカット（16文字）
                    clean_val = str(value).strip()[:16].replace(":", "/", 2)
                    temp_dt = datetime.strptime(clean_val, '%Y/%m/%d %H:%M')
                except:
                    pass
    
        # 取得できたか判定
        if temp_dt:
            st.session_state.target_dt = temp_dt
            st.success(f"📸 撮影日時を検出: {temp_dt.strftime('%Y/%m/%d %H:%M')}")
        else:
            st.session_state.target_dt = datetime.now()
            st.info("ℹ️ 撮影日時が取得できないため現在時刻を使用します。")

        # --- 2. GPS情報の取得 ---
        geo = get_geotagging(exif)
        if geo:
            lat = get_decimal_from_dms(geo['GPSLatitude'], geo['GPSLatitudeRef'])
            lon = get_decimal_from_dms(geo['GPSLongitude'], geo['GPSLongitudeRef'])
            if lat and lon:
                st.session_state.lat, st.session_state.lon = lat, lon
                # find_nearest_place で場所を特定
                place, gid = find_nearest_place(lat, lon, df_master)
                st.session_state.detected_place, st.session_state.group_id = place, gid
                st.session_state.data_ready = True
        else:
            st.warning("⚠️ GPS情報が見つかりません。地点を選択してください。")
            st.session_state.data_ready = TrueTrue

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

    st.markdown("---")
    force_new = st.checkbox("🆕 新しい場所として登録する")
    if force_new:
        place_name = st.text_input("📍 新しい場所名を入力してください", value="")
        target_group_id = "default"
    else:
        place_name = st.text_input("📍 場所名", value=st.session_state.detected_place)
        target_group_id = st.session_state.group_id

    lure = st.text_input("🪝 ルアー/仕掛け")
    angler = st.selectbox("👤 釣り人", ["長元", "川口", "山川"])
    memo = st.text_area("🗒️ 備考")
    
if st.button("🚀 釣果を記録する", use_container_width=True, type="primary"):
        # 1. すべての変数を初期化
        temp, wind_s, wind_d, rain_48 = 0, 0, "不明", 0
        tide_cm, tide_phase = 0, "不明"
        m_age, t_name = 0, "不明"
        high_str, low_str = "", ""
        val_next_high, val_next_low = "", ""
        station_name = "不明"
        
        if place_name == "" or place_name == "新規地点":
            st.error("⚠️ 場所名を入力してください。")
        else:
            try:
                with st.spinner("📊 前後3日間の潮汐データを解析中..."):
                    # --- 2. 撮影日時の確定（秒を物理的にカットしてエラー防止） ---
                    raw_dt = st.session_state.get('target_dt', datetime.now())
                    clean_dt_str = raw_dt.isoformat()[:16].replace("T", " ")
                    target_dt = datetime.strptime(clean_dt_str, '%Y-%m-%d %H:%M')
                    
                    # 3. 気象・月齢データの取得
                    temp, wind_s, wind_d, rain_48 = get_weather_data_openmeteo(
                        st.session_state.lat, st.session_state.lon, target_dt
                    )
                    m_age = get_moon_age(target_dt)
                    t_name = get_tide_name(m_age)
                    
                    # 4. 潮汐データの取得（前後3日間スキャンロジック）
                    station_info = find_nearest_tide_station(st.session_state.lat, st.session_state.lon)
                    station_name = station_info['name']
                    
                    all_events = []
                    # 前日(-1), 当日(0), 翌日(1) の3日分を合体
                    for delta in [-1, 0, 1]:
                        check_day = target_dt + timedelta(days=delta)
                        day_data = get_tide_details(station_info['code'], check_day)
                        if day_data and 'events' in day_data:
                            all_events.extend(day_data['events'])
                            # 現在の潮位とフェーズは「当日」分から取得
                            if delta == 0:
                                tide_cm = day_data['cm']
                                tide_phase = day_data['phase']
                    
                    # 時間順にソート（旧コードの肝）
                    all_events.sort(key=lambda x: x['time'])
                    
                    # 5. 直前と次のイベントを特定（旧コードのロジックを継承）
                    prev_h = prev_l = next_h = next_l = None
                    for ev in all_events:
                        ev_dt = ev['time']
                        kind = ev['type']
                        if ev_dt <= target_dt:
                            if '満' in kind: prev_h = ev_dt
                            if '干' in kind: prev_l = ev_dt
                        else:
                            if '満' in kind and next_h is None: next_h = ev_dt
                            if '干' in kind and next_l is None: next_l = ev_dt

                    # 表示・保存用にフォーマット（秒なし）
                    high_str = prev_h.strftime('%Y/%m/%d %H:%M') if prev_h else ""
                    low_str = prev_l.strftime('%Y/%m/%d %H:%M') if prev_l else ""
                    if next_h:
                        val_next_high = int((next_h - target_dt).total_seconds() / 60)
                    if next_l:
                        val_next_low = int((next_l - target_dt).total_seconds() / 60)

                    # --- 6. 画像のリサイズと軽量化処理 (長辺800px) ---
                    # uploaded_file を開き直す（ポインタを先頭に戻してから）
                    uploaded_file.seek(0)
                    img_for_upload = Image.open(uploaded_file)
                    
                    # スマホ写真の向き（回転情報）を補正
                    try:
                        exif = img_for_upload._getexif()
                        if exif:
                            orientation = next((k for k, v in ExifTags.TAGS.items() if v == 'Orientation'), None)
                            if orientation and orientation in exif:
                                if exif[orientation] == 3: img_for_upload = img_for_upload.rotate(180, expand=True)
                                elif exif[orientation] == 6: img_for_upload = img_for_upload.rotate(270, expand=True)
                                elif exif[orientation] == 8: img_for_upload = img_for_upload.rotate(90, expand=True)
                    except:
                        pass # 補正に失敗してもリサイズ処理へ進む

                    # リサイズ：長辺を800pxに制限
                    img_for_upload.thumbnail((800, 800), Image.Resampling.LANCZOS)

                    # メモリ上でJPEG圧縮（画質70%）
                    img_bytes = io.BytesIO()
                    if img_for_upload.mode != 'RGB':
                        img_for_upload = img_for_upload.convert('RGB')
                        
                    img_for_upload.save(img_bytes, format='JPEG', quality=70, optimize=True)
                    img_bytes.seek(0)

                    # Cloudinaryへアップロード
                    res = cloudinary.uploader.upload(img_bytes, folder="fishing_app")
                    
                    # 7. 保存データの作成
                    save_data = {
                        "filename": res.get("secure_url"), 
                        "datetime": target_dt.strftime("%Y/%m/%d %H:%M"),
                        "date": target_dt.strftime("%Y/%m/%d"), 
                        "time": target_dt.strftime("%H:%M"),
                        "lat": float(st.session_state.lat), "lon": float(st.session_state.lon),
                        "気温": temp, "風速": wind_s, "風向": wind_d, "降水量": rain_48, 
                        "潮位_cm": tide_cm, "月齢": m_age, "潮名": t_name,
                        "次の満潮まで_分": val_next_high, "次の干潮まで_分": val_next_low,
                        "直前の満潮_時刻": high_str, "直前の干潮_時刻": low_str,
                        "潮位フェーズ": tide_phase, "場所": place_name, "魚種": final_fish_name,
                        "全長_cm": float(st.session_state.length_val), "ルアー": lure, "備考": memo,
                        "group_id": target_group_id, "観測所": station_name, "釣り人": angler
                    }

                    # 8. スプレッドシート更新
                    df_main = conn.read(spreadsheet=url, ttl=0)
                    cols = ["filename","datetime","date","time","lat","lon","気温","風速","風向","降水量","潮位_cm","月齢","潮名","次の満潮まで_分","次の干潮まで_分","直前の満潮_時刻","直前の干潮_時刻","潮位フェーズ","場所","魚種","全長_cm","ルアー","備考","group_id","観測所","釣り人"]
                    new_row_df = pd.DataFrame([save_data])[cols]
                    conn.update(spreadsheet=url, data=pd.concat([df_main, new_row_df], ignore_index=True))
                    
                    st.success(f"✅ 保存完了！次の干潮まで: {val_next_low}分")
                    st.balloons()
                    st.session_state.data_ready = False
                    time.sleep(2); st.rerun()

            except Exception as e:
                st.error(f"❌ 保存失敗: {e}")
    






























