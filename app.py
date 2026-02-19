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
# app.py の冒頭に追加
from edit_module import show_edit_page
from gallery_module import show_gallery_page
from analysis_module import show_analysis_page # この名前であることを確認

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

# 1. 接続設定（既存のコード）
conn = st.connection("gsheets", type=GSheetsConnection)
url = "https://docs.google.com/spreadsheets/d/12hcg7hagi0oLq3nS-K27OqIjBYmzMYXh_FcoS8gFFyE/edit?gid=0#gid=0"

# 2. データを読み込んで 'df' という名前の変数に入れる（★ここが重要！）
# 先ほどのエラー(429)対策として ="1m" を推奨します
df = conn.read(spreadsheet=url, ttl="10m")
# --- タブの設定部分 ---
tab1, tab2, tab3, tab4 = st.tabs(["記録", "編集", "ギャラリー", "分析（時合・フェーズ）"])

with tab1:
    # --- 3. 以降、初期設定・画像アップロード・入力画面は既存と同じ ---
    st.set_page_config(page_title="釣果記録アプリ", layout="centered")
    st.title("🎣 KTDシステム")
    
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
    
# --- デバッグ機能付き画像解析セクション ---
    uploaded_file = st.file_uploader("釣果写真をアップロード", type=["jpg", "jpeg", "png", "heic"])
    
    if uploaded_file:
        img_for_upload = Image.open(uploaded_file)
        exif = img_for_upload._getexif()
        
        # --- DEBUG PANEL ---
        with st.expander("🔍 内部解析デバッグ (ここを確認して報告してください)"):
            if exif:
                st.write("✅ EXIFデータを検出しました")
                # GPS情報のタグ(34853)の有無
                gps_data = exif.get(34853)
                st.write(f"GPSタグ(34853)の有無: {'あり' if gps_data else 'なし'}")
                if gps_data:
                    st.write("生GPSデータ:", gps_data)
            else:
                st.error("❌ EXIFデータが画像に含まれていません。LINE等で保存した写真は位置情報が消えます。")

        temp_dt = datetime.now()
        lat, lon = 0.0, 0.0
        
        if exif:
            # 日時抽出
            for tag_id, value in exif.items():
                tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                if tag_name == 'DateTimeOriginal':
                    try:
                        clean_val = str(value).strip()[:16].replace(":", "/", 2)
                        temp_dt = datetime.strptime(clean_val, '%Y/%m/%d %H:%M')
                    except: pass
            
            # 位置抽出
            geo = get_geotagging(exif)
            if geo:
                lat = get_decimal_from_dms(geo['GPSLatitude'], geo['GPSLatitudeRef'])
                lon = get_decimal_from_dms(geo['GPSLongitude'], geo['GPSLongitudeRef'])

        # セッションに即時保存
        st.session_state.lat = lat
        st.session_state.lon = lon
        st.session_state.target_dt = temp_dt

        # --- 地点照合デバッグ ---
        if lat != 0.0:
            place, gid = find_nearest_place(lat, lon, df_master)
            
            # 内部での計算距離をデバッグ表示
            valid_m = df_master.dropna(subset=['latitude', 'longitude']).copy()
            if not valid_m.empty:
                valid_m['dist_m'] = np.sqrt(((valid_m['latitude'] - lat) * 111000 )**2 + ((valid_m['longitude'] - lon) * 91000 )**2)
                min_dist = valid_m['dist_m'].min()
                nearest_row = valid_m.loc[valid_m['dist_m'].idxmin()]
                
                with st.expander("📏 地点照合の計算結果"):
                    st.write(f"画像座標: {lat}, {lon}")
                    st.write(f"最寄りの登録地点: {nearest_row['place_name']}")
                    st.write(f"計算距離: {min_dist:.1f} メートル")
                    st.write(f"判定: {'成功（反映します）' if min_dist <= 500 else '失敗（500m以上離れているため新規地点扱い）'}")
            
            st.session_state.detected_place = place
            st.session_state.group_id = gid
            st.success(f"📸 解析完了: {detected_place}")
        else:
            st.warning("⚠️ 画像から位置情報を取得できませんでした。手入力してください。")
   # --- 270行目付近：入力エリアの修正 ---
    if uploaded_file:
        with st.expander("📍 位置情報の確認", expanded=False):
            if st.session_state.lat != 0.0:
                st.map(pd.DataFrame({'lat': [st.session_state.lat], 'lon': [st.session_state.lon]}), zoom=14)
        
        st.subheader("📝 釣果の詳細")
        fish_options = ["スズキ", "ヒラスズキ", "ボウズ", "バラシ", "カサゴ", "ターポン", "タチウオ", "マダイ", "チヌ", "キビレ", "ブリ", "アジ", "（手入力）"]
        selected_fish = st.selectbox("🐟 魚種を選択", fish_options)
        final_fish_name = st.text_input("魚種名を入力") if selected_fish == "（手入力）" else selected_fish
    
        c1, c2, c3 = st.columns([1, 2, 1])
        if c1.button("➖ 0.5", use_container_width=True):
            st.session_state.length_val = max(0.0, st.session_state.length_val - 0.5)
        length_text = c2.text_input("全長(cm)", value=str(st.session_state.length_val) if st.session_state.length_val > 0 else "")
        st.session_state.length_val = normalize_float(length_text)
        if c3.button("➕ 0.5", use_container_width=True):
            st.session_state.length_val += 0.5
    
        # --- 場所名入力欄の重要修正 ---
        force_new = st.checkbox("🆕 新しい場所として登録する")
        
        # valueにセッション状態を直接指定し、かつ手入力も受け付けるようにする
        default_place_val = "" if force_new else st.session_state.detected_place
        place_name = st.text_input("📍 場所名", value=default_place_val)
        
        # 保存用データの確定
        target_group_id = "default" if force_new else st.session_state.group_id
    
        lure = st.text_input("🪝 ルアー/仕掛け")
        angler = st.selectbox("👤 釣り人", ["長元", "川口", "山川"])
        memo = st.text_area("🗒️ 備考")

        # --- 保存ボタン ---
        if st.button("🚀 釣果を記録する", use_container_width=True, type="primary"):
            if not place_name or place_name == "新規地点":
                st.error("⚠️ 場所名を入力してください。")
            else:
                try:
                    with st.spinner("📊 データ解析中..."):
                        target_dt = st.session_state.target_dt   
                        
                        # 気象・潮汐取得
                        temp, wind_s, wind_d, rain_48 = get_weather_data_openmeteo(st.session_state.lat, st.session_state.lon, target_dt)
                        m_age = get_moon_age(target_dt)
                        t_name = get_tide_name(m_age)
                        station_info = find_nearest_tide_station(st.session_state.lat, st.session_state.lon)
                        
                        # 潮汐フェーズの計算（既存ロジック）
                        all_events = []
                        tide_cm = 0
                        for delta in [-1, 0, 1]:
                            day_data = get_tide_details(station_info['code'], target_dt + timedelta(days=delta))
                            if day_data:
                                if 'events' in day_data: all_events.extend(day_data['events'])
                                if delta == 0: tide_cm = day_data['cm']
                        
                        all_events = sorted({ev['time']: ev for ev in all_events}.values(), key=lambda x: x['time'])
                        prev_ev = next((e for e in reversed(all_events) if e['time'] <= target_dt), None)
                        next_ev = next((e for e in all_events if e['time'] > target_dt), None)
                        
                        tide_phase = "不明"
                        if prev_ev and next_ev:
                            duration = (next_ev['time'] - prev_ev['time']).total_seconds()
                            elapsed = (target_dt - prev_ev['time']).total_seconds()
                            if duration > 0:
                                step = max(1, min(9, int((elapsed / duration) * 10)))
                                tide_phase = f"上げ{step}分" if "干" in prev_ev['type'] else f"下げ{step}分"

                        # 満干潮時刻
                        prev_h = next((e['time'] for e in reversed(all_events) if e['time'] <= target_dt and '満' in e['type']), None)
                        prev_l = next((e['time'] for e in reversed(all_events) if e['time'] <= target_dt and '干' in e['type']), None)
                        next_h = next((e['time'] for e in all_events if e['time'] > target_dt and '満' in e['type']), None)
                        next_l = next((e['time'] for e in all_events if e['time'] > target_dt and '干' in e['type']), None)
                        val_next_high = int((next_h - target_dt).total_seconds() / 60) if next_h else ""
                        val_next_low = int((next_l - target_dt).total_seconds() / 60) if next_l else ""

                        # 画像のリサイズと向き補正
                        img_final = Image.open(uploaded_file)
                        # EXIF補正
                        try:
                            exif_orient = img_final._getexif()
                            if exif_orient:
                                orient = next((k for k, v in ExifTags.TAGS.items() if v == 'Orientation'), None)
                                if orient in exif_orient:
                                    if exif_orient[orient] == 3: img_final = img_final.rotate(180, expand=True)
                                    elif exif_orient[orient] == 6: img_final = img_final.rotate(270, expand=True)
                                    elif exif_orient[orient] == 8: img_final = img_final.rotate(90, expand=True)
                        except: pass

                        img_final.thumbnail((800, 800), Image.Resampling.LANCZOS)
                        img_bytes = io.BytesIO()
                        img_final.convert('RGB').save(img_bytes, format='JPEG', quality=70, optimize=True)
                        img_bytes.seek(0)

                        # Cloudinary保存
                        res = cloudinary.uploader.upload(img_bytes, folder="fishing_app")
                        
                        # スプレッドシート保存データ作成
                        save_data = {
                            "filename": res.get("secure_url"), 
                            "datetime": target_dt.strftime("%Y/%m/%d %H:%M"),
                            "date": target_dt.strftime("%Y/%m/%d"), 
                            "time": target_dt.strftime("%H:%M"),
                            "lat": float(st.session_state.lat), "lon": float(st.session_state.lon),
                            "気温": temp, "風速": wind_s, "風向": wind_d, "降水量": rain_48, 
                            "潮位_cm": tide_cm, "月齢": m_age, "潮名": t_name,
                            "次の満潮まで_分": val_next_high, "次の干潮まで_分": val_next_low,
                            "直前の満潮_時刻": prev_h.strftime('%Y/%m/%d %H:%M') if prev_h else "",
                            "直前の干潮_時刻": prev_l.strftime('%Y/%m/%d %H:%M') if prev_l else "",
                            "潮位フェーズ": tide_phase, "場所": place_name, "魚種": final_fish_name,
                            "全長_cm": float(st.session_state.length_val), "ルアー": lure, "備考": memo,
                            "group_id": target_group_id, "観測所": station_info['name'], "釣り人": angler
                        }

                        # 更新実行
                        df_main = conn.read(spreadsheet=url, )
                        new_row = pd.DataFrame([save_data])
                        updated_df = pd.concat([df_main, new_row], ignore_index=True)
    # app.py の「保存完了しました！」のメッセージ周辺を修正
# (中略) スプレッドシートを更新した直後
                        conn.update(spreadsheet=url, data=updated_df)
                        
                        # 保存した時だけ、古いキャッシュを捨てる
                        st.cache_data.clear() 
                        
                        st.success("✅ 記録完了しました！")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()

                except Exception as e:
                    st.error(f"❌ 保存失敗: {e}")

# ↓ ここから下の「with tab...」が、すべて同じ左端の高さにあるか確認してください
with tab2:
    show_edit_page(conn, url)

with tab3:
    # 保存時にキャッシュをクリアする設定にしていれば、ここは ttl="10m" のままでも
    # 保存直後は最新が表示されます。念を入れるなら今のまま ttl="0s" でもOKです。
    df_for_gallery = conn.read(spreadsheet=url, ttl="0s")
    show_gallery_page(df_for_gallery)

with tab4:
    show_analysis_page(df)










































