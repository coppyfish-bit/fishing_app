import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime, timedelta
import requests
import math

# --- 1. 各種関数定義（計算・変換系） ---
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
    res = dms[0] + dms[1] / 60.0 + dms[2] / 3600.0
    return -res if ref in ['S', 'W'] else round(res, 6)

# --- 2. 気象・潮汐取得（外部データ連動） ---
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
        data = requests.get(url, params=params, timeout=10).json()
        idx = (len(data['hourly']['temperature_2m']) - 25) + dt.hour
        h = data['hourly']
        return h['temperature_2m'][idx], h['windspeed_10m'][idx], h['winddirection_10m'][idx], round(sum(h['precipitation'][:idx+1][-48:]), 1)
    except: return None, None, None, None

def get_tide_details(lat, lon, dt):
    """気象庁データに基づく精密解析（観測所リスト連動）"""
    STATIONS = [
        {"name": "本渡瀬戸", "lat": 32.26, "lon": 130.13, "code": "HS"},
        {"name": "苓北", "lat": 32.28, "lon": 130.20, "code": "RH"},
        {"name": "口之津", "lat": 32.36, "lon": 130.12, "code": "KT"},
        {"name": "八代", "lat": 32.31, "lon": 130.34, "code": "O5"},
    ]
    # 最寄りの観測所を判定
    station = STATIONS[0]
    min_dist = 999
    for s in STATIONS:
        d = calculate_distance(lat, lon, s["lat"], s["lon"])
        if d < min_dist: min_dist, station = d, s

    try:
        url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{dt.year}/{station['code']}.txt"
        lines = requests.get(url, timeout=10).text.splitlines()
        date_str = dt.strftime("%y%m%d")
        line = next((l for l in lines if l[72:78] == date_str), None)
        if not line: return {}

        # 満干潮イベント抽出
        events = []
        for i in range(4):
            m = line[80+i*7:84+i*7].strip()
            if m and m != "9999": events.append(("満潮", datetime(dt.year, dt.month, dt.day, int(m[:2]), int(m[2:]))))
            k = line[108+i*7:112+i*7].strip()
            if k and k != "9999": events.append(("干潮", datetime(dt.year, dt.month, dt.day, int(k[:2]), int(k[2:]))))
        events.sort(key=lambda x: x[1])

        # フェーズ判定
        prev_ev = next((e for e in reversed(events) if e[1] <= dt), None)
        next_ev = next((e for e in events if e[1] > dt), None)
        phase = "不明"
        if prev_ev and next_ev:
            ratio = (dt - prev_ev[1]).total_seconds() / (next_ev[1] - prev_ev[1]).total_seconds()
            direction = "下げ" if prev_ev[0] == "満潮" else "上げ"
            phase = f"{direction}{max(1, min(9, round(ratio * 10)))}分"
            if ratio < 0.1: phase = prev_ev[0]
            elif ratio > 0.9: phase = next_ev[0]

        return {
            "潮位_cm": int(line[dt.hour*3:dt.hour*3+3].strip() or 0),
            "潮位フェーズ": phase,
            "直前の満潮_時刻": next((e[1].strftime("%H:%M") for e in reversed(events) if e[0]=="満潮" and e[1]<=dt), ""),
            "直前の干潮_時刻": next((e[1].strftime("%H:%M") for e in reversed(events) if e[0]=="干潮" and e[1]<=dt), ""),
            "観測所": station["name"]
        }
    except: return {}

# --- 3. メイン UI ---
st.set_page_config(page_title="Fishing AI Log", layout="wide")
st.title("🎣 釣果統合ログシステム")

# データ接続
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    df = conn.read(spreadsheet=url, ttl="5m")
    m_df = conn.read(spreadsheet=url, worksheet="place_master", ttl="10m")
except:
    st.error("スプレッドシート接続エラー"); st.stop()

# 写真アップロード
uploaded_file = st.file_uploader("📸 写真を選択", type=['jpg', 'jpeg'])
auto_lat, auto_lon, default_dt = 32.5, 130.0, datetime.now()

if uploaded_file:
    img = Image.open(uploaded_file)
    exif = img._getexif()
    if exif:
        geotags = get_geotagging(exif)
        if geotags:
            lat, lon = get_decimal_from_dms(geotags['GPSLatitude'], geotags['GPSLatitudeRef']), get_decimal_from_dms(geotags['GPSLongitude'], geotags['GPSLongitudeRef'])
            if lat: auto_lat, auto_lon = lat, lon
        dt_str = exif.get(36867)
        if dt_str: default_dt = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S')

# 場所自動判定
nearest_place = None
if not m_df.empty:
    place_to_id = dict(zip(m_df["place_name"], m_df["group_id"]))
    for _, row in m_df.iterrows():
        if calculate_distance(auto_lat, auto_lon, row['latitude'], row['longitude']) < 0.5:
            nearest_place = row['place_name']; break
    place_options = sorted(place_to_id.keys())
else: place_to_id, place_options = {}, []

# フォーム
with st.form("main_form"):
    c1, c2 = st.columns(2)
    with c1:
        date_in = st.date_input("📅 日付", value=default_dt.date())
        time_in = st.time_input("⏰ 時刻", value=default_dt.time())
        default_idx = (place_options.index(nearest_place) + 1) if nearest_place in place_options else 0
        place_sel = st.selectbox("📍 釣り場を選択", options=["-- 新規入力 --"] + place_options, index=default_idx)
    with c2:
        lat_in = st.number_input("緯度", value=auto_lat, format="%.6f")
        lon_in = st.number_input("経度", value=auto_lon, format="%.6f")
        place_man = st.text_input("📍 新しい場所名（新規時のみ）")

    fish = st.text_input("🐟 魚種")
    length = st.number_input("📏 全長(cm)", value=0.0)
    memo = st.text_area("📝 備考")
    submit = st.form_submit_button("🚀 データを保存")

if submit:
    target_dt = datetime.combine(date_in, time_in)
    final_place = place_sel if place_sel != "-- 新規入力 --" else place_man
    final_gid = place_to_id.get(final_place, int(m_df["group_id"].max() + 1 if not m_df.empty else 0))
    
    if not final_place: st.error("場所名を入力してください"); st.stop()

    with st.spinner('解析中...'):
        temp, ws, wd, prec = get_weather_data(lat_in, lon_in, target_dt)
        tide = get_tide_details(lat_in, lon_in, target_dt)
        
        save_data = {
            "group_id": final_gid, "場所": final_place, "datetime": target_dt.strftime('%Y-%m-%d %H:%M'),
            "lat": lat_in, "lon": lon_in, "気温": temp, "風速": ws, "風向": get_wind_direction_label(wd),
            "降水量": prec, "潮位フェーズ": tide.get("潮位フェーズ"), "潮位_cm": tide.get("潮位_cm"),
            "直前の満潮_時刻": tide.get("直前の満潮_時刻"), "直前の干潮_時刻": tide.get("直前の干潮_時刻"),
            "魚種": fish, "全長_cm": length, "備考": memo
        }
        
        # 保存とマスター更新
        conn.update(spreadsheet=url, data=pd.concat([df, pd.DataFrame([save_data])], ignore_index=True))
        if place_sel == "-- 新規入力 --":
            new_m = pd.DataFrame([{"group_id": final_gid, "place_name": final_place, "latitude": lat_in, "longitude": lon_in}])
            conn.update(spreadsheet=url, worksheet="place_master", data=pd.concat([m_df, new_m], ignore_index=True))
        
        st.success("✅ 保存完了！"); st.balloons(); st.cache_data.clear()
# 写真解析
uploaded_file = st.file_uploader("📸 写真を選択", type=['jpg', 'jpeg'])
if uploaded_file:
    img = Image.open(uploaded_file)
    exif = img._getexif()
    if exif:
        for tag_id, value in exif.items():
            if TAGS.get(tag_id) == 'DateTimeOriginal':
                default_dt = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
        geotags = get_geotagging(exif)
        if geotags:
            lat, lon = get_coordinates(geotags)
            if lat: auto_lat, auto_lon = lat, lon
            st.success(f"📍 GPS/日時を取得しました")

# --- 座標の初期値を確定させる ---
# 写真から取得できていればそれを使い、なければデフォルト（例：天草近辺）を入れる
lat_in = locals().get('auto_lat', 32.5) 
lon_in = locals().get('auto_lon', 130.0)
# --- 統合版：場所自動判定 ＆ 入力フォーム ---

# 1. 準備：マスターデータから場所・ID・座標の辞書を作成
if not m_df.empty:
    # 場所名 -> ID の辞書
    place_to_id = dict(zip(m_df["place_name"], m_df["group_id"]))
    # 場所名 -> (緯度, 経度) の辞書（距離計算用）
    place_coords = {row['place_name']: (row['latitude'], row['longitude']) for _, row in m_df.iterrows()}
    place_options = sorted(place_to_id.keys())
    
    # 【GPS自動検知】写真の座標(lat_in, lon_in)から最も近い地点を探す
    nearest_place = None
    min_dist = 0.5  # 500m以内を検知対象とする
    
    for p_name, coords in place_coords.items():
        dist = calculate_distance(lat_in, lon_in, coords[0], coords[1])
        if dist < min_dist:
            min_dist = dist
            nearest_place = p_name
else:
    place_to_id = {}
    place_options = []
    nearest_place = None

# --- UI表示 ---

st.write("### 📝 釣果入力")

# デフォルトの選択肢を決定（GPSで見つかればその場所、なければ「新規」）
default_index = 0
if nearest_place in place_options:
    default_index = place_options.index(nearest_place) + 1 # 0番目は「--新規--」のため+1

with st.form("main_form", clear_on_submit=True):
    # レイアウト：1列目（日時・場所選択）
    col1, col2 = st.columns(2)
    
    with col1:
        date_in = st.date_input("📅 日付", value=default_dt.date())
        time_in = st.time_input("⏰ 時刻", value=default_dt.time())
        
        place_selected = st.selectbox(
            "📍 釣り場を選択（GPS自動検知対応）", 
            options=["-- 新規地点 or 手動入力 --"] + place_options,
            index=default_index
        )
        
        # 自動検知された場合のメッセージ表示
        if nearest_place and place_selected == nearest_place:
            st.caption(f"✨ 写真の位置情報から「{nearest_place}」を自動選択しました（距離: {int(min_dist*1000)}m）")

    with col2:
        lat_in_final = st.number_input("緯度(Lat)", value=lat_in, format="%.6f")
        lon_in_final = st.number_input("経度(Lon)", value=lon_in, format="%.6f")
        
        place_manual = st.text_input("📍 新しい場所名を入力（新規の場合）", placeholder="〇〇漁港 外堤防")

    st.divider()

    # レイアウト：2列目（釣果詳細）
    col3, col4 = st.columns(2)
    
    with col3:
        fish_in = st.text_input("🐟 魚種", placeholder="シーバス、チヌ、アジなど")
        length_in = st.slider("📏 全長 (cm)", 0.0, 150.0, 40.0, step=0.5)
        lure_in = st.text_input("🎣 使用ルアー/仕掛け", placeholder="ミノー 120F")
        
    with col4:
        memo_in = st.text_area("📝 備考・ヒットパターン", placeholder="上げ潮が効き始めたタイミング。明暗の境目でヒット。")

    # 保存ボタン
    submit = st.form_submit_button("🚀 気象・潮汐を解析してスプレッドシートに保存")

# --- 保存処理の改良版全文 ---
if submit:
    # 1. 場所名とIDの確定ロジック
    if place_selected != "-- 新規地点 or 手動入力 --":
        final_place_name = place_selected
        final_group_id = place_to_id.get(place_selected)
    else:
        final_place_name = place_manual.strip() # 前後の空白を削除
        # 新規の場合は現在の最大ID + 1 を数値として取得
        if not m_df.empty and "group_id" in m_df.columns:
            final_group_id = int(m_df["group_id"].max() + 1)
        else:
            final_group_id = 0

    # 2. 入力チェック
    if not final_place_name:
        st.error("⚠️ 場所名を選択するか、新しい場所名を入力してください。")
    else:
        with st.spinner('📊 当時の気象と潮汐を解析中...'):
            try:
                # 3. 日時の厳密な datetime オブジェクト化（TypeError対策）
                target_dt = datetime(
                    date_in.year, date_in.month, date_in.day,
                    time_in.hour, time_in.minute
                )
                
                # 4. 気象データの取得（4項目: 気温, 風速, 風向, 降水量）
                weather_res = get_weather_data(lat_in_final, lon_in_final, target_dt)
                if weather_res and len(weather_res) == 4:
                    temp, wind_s, wind_d, precip = weather_res
                else:
                    temp, wind_s, wind_d, precip = None, None, None, None
                
                # 5. 潮汐データの取得（10段階フェーズ・干満時刻）
                tide_name = get_tide_name(target_dt)
                tide_info = get_tide_details(target_dt)
                if not tide_info:
                    tide_info = {} # 万が一の空辞書ガード

                # 6. 保存データの辞書作成（全23カラム想定）
                save_data = {
                    "group_id": final_group_id,
                    "場所": final_place_name,
                    "datetime": target_dt.strftime('%Y-%m-%d %H:%M'),
                    "date": date_in.strftime('%Y-%m-%d'),
                    "time": time_in.strftime('%H:%M'),
                    "lat": lat_in_final,
                    "lon": lon_in_final,
                    "気温": temp,
                    "風速": wind_s,
                    "風向": get_wind_direction_label(wind_d), # 角度を方位文字（南南西など）へ変換
                    "降水量": precip,
                    "潮名": tide_name,
                    "潮位_cm": tide_info.get("潮位_cm"),
                    "月齢": tide_info.get("月齢"),
                    "潮位フェーズ": tide_info.get("潮位フェーズ"),
                    "直前の満潮_時刻": tide_info.get("直前の満潮_時刻"),
                    "直前の干潮_時刻": tide_info.get("直前の干潮_時刻"),
                    "次の満潮まで_分": tide_info.get("次の満潮まで_分"),
                    "次の干潮まで_分": tide_info.get("次の干潮まで_分"),
                    "魚種": fish_in,
                    "全長_cm": length_in,
                    "ルアー": lure_in,
                    "備考": memo_in,
                    "filename": uploaded_file.name if uploaded_file else ""
                }
                
                # 7. スプレッドシートへの書き込み実行
                # 釣果ログシートの更新
                new_row = pd.DataFrame([save_data])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(spreadsheet=url, data=updated_df)
                
                # 8. マスターデータの更新（新規場所かつ、まだ登録されていない場合のみ）
                if place_selected == "-- 新規地点 or 手動入力 --" and final_place_name not in place_options:
                    new_m_row = pd.DataFrame([{
                        "group_id": final_group_id, 
                        "place_name": final_place_name, 
                        "latitude": lat_in_final, 
                        "longitude": lon_in_final
                    }])
                    # 列名をマスターシートの形式に合わせて結合
                    updated_m_df = pd.concat([m_df, new_m_row], ignore_index=True)
                    conn.update(spreadsheet=url, worksheet="place_master", data=updated_m_df)
                    st.toast(f"📍 新しい釣り場「{final_place_name}」をマスターに登録しました")

                # 9. 完了通知
                st.success(f"✅ 保存成功: {final_place_name} (ID:{final_group_id})")
                st.balloons()
                
                # 画面更新のためのキャッシュクリア
                st.cache_data.clear()
                # 成功したら画面をリセット
                st.rerun()

            except Exception as e:
                st.error(f"❌ 処理中にエラーが発生しました: {e}")
                # 詳細なエラーを画面に出したい場合は以下を有効に
                # st.exception(e)
















