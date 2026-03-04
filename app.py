import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection
from PIL import Image, ExifTags
from datetime import datetime, timedelta
import cloudinary
import cloudinary.uploader
import unicodedata
import io
import numpy as np
import ephem
import requests
import traceback
import streamlit.components.v1 as components

# モジュールインポート
from edit_module import show_edit_page
from gallery_module import show_gallery_page
from analysis_module import show_analysis_page
from monthly_stats import show_monthly_stats
from matching_module import show_matching_page
from strategy_analysis import show_strategy_analysis
import ai_module

# AIとの会話は学習に使用したり外部に漏れたりしません。釣果情報も共有しないでください。

# 1. ブラウザ設定
icon_url = "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"
st.set_page_config(page_title="Seabass Strategy App", page_icon=icon_url, layout="wide")

components.html(
    f"""
    <script>
        var link = window.parent.document.createElement('link');
        link.rel = 'apple-touch-icon'; link.href = '{icon_url}';
        window.parent.document.getElementsByTagName('head')[0].appendChild(link);
        var link2 = window.parent.document.createElement('link');
        link2.rel = 'shortcut icon'; link2.href = '{icon_url}';
        window.parent.document.getElementsByTagName('head')[0].appendChild(link2);
    </script>
    """, height=0,
)

# --- 定数・関数定義 ---
TIDE_STATIONS = [
    {"name": "苓北", "lat": 32.4667, "lon": 130.0333, "code": "RH"},
    {"name": "三角", "lat": 32.6167, "lon": 130.4500, "code": "MS"},
    {"name": "本渡瀬戸", "lat": 32.4333, "lon": 130.2167, "code": "HS"},
    {"name": "八代", "lat": 32.5167, "lon": 130.5667, "code": "O5"},
    {"name": "熊本", "lat": 32.7500, "lon": 130.5667, "code": "KU"},
    {"name": "長崎", "lat": 32.7333, "lon": 129.8667, "code": "NS"},
]

def get_geotagging(exif):
    if not exif: return None
    gps_info = exif.get(34853)
    if not gps_info: return None
    return {
        'GPSLatitudeRef': gps_info.get(1), 'GPSLatitude': gps_info.get(2),
        'GPSLongitudeRef': gps_info.get(3), 'GPSLongitude': gps_info.get(4)
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
    try: return float(unicodedata.normalize('NFKC', str(text)))
    except: return 0.0

def find_nearest_place(lat, lon, df_master):
    if lat == 0.0 or lon == 0.0 or df_master.empty: return "新規地点", "default"
    valid_master = df_master.dropna(subset=['latitude', 'longitude']).copy()
    valid_master['dist_m'] = np.sqrt(((valid_master['latitude'] - lat) * 111000 )**2 + ((valid_master['longitude'] - lon) * 91000 )**2)
    nearest = valid_master.loc[valid_master['dist_m'].idxmin()]
    return (nearest['place_name'], nearest['group_id']) if nearest['dist_m'] <= 500 else ("新規地点", "default")

def get_moon_age(date_obj):
    e_date = ephem.Date(date_obj)
    return round(float(e_date - ephem.previous_new_moon(e_date)), 1)

def get_tide_name(moon_age):
    age = int(round(moon_age)) % 30
    if age in [30, 0, 1, 14, 15, 16]: return "大潮"
    elif age in [2, 3, 4, 11, 12, 13, 17, 18, 19, 26, 27, 28]: return "中潮"
    elif age in [5, 6, 7, 8, 20, 21, 22, 23]: return "小潮"
    elif age in [9, 24]: return "長潮"
    elif age in [10, 25]: return "若潮"
    return "不明"

def find_nearest_tide_station(lat, lon):
    distances = [np.sqrt((s['lat'] - lat)**2 + (s['lon'] - lon)**2) for s in TIDE_STATIONS]
    return TIDE_STATIONS[np.argmin(distances)]

def get_tide_details(res, dt):
    """
    GitHubから取得したレスポンスを解析して潮位とイベントを返す。
    """
    try:
        if isinstance(res, str): # URLが渡された場合の保険
            res = requests.get(res)
        data = res.json()
        
        # 2026- 3- 4 形式への対応
        target_date_clean = dt.strftime("%Y-%m-%d").replace("-0", "-").replace("-", "").replace(" ", "")
        
        day_info = next((item for item in data.get('data', []) if str(item.get('date')).replace(" ", "").replace("-", "") == target_date_clean), None)
        
        if not day_info: return {"cm": 0, "phase": "日付不一致", "events": [], "hourly": []}

        hourly = [int(v) if str(v).strip().replace('-','').isdigit() else 0 for v in day_info.get('hourly', [])]
        h, mi = dt.hour, dt.minute
        t1, t2 = hourly[h], hourly[(h+1)%24]
        current_cm = int(round(t1 + (t2 - t1) * (mi / 60.0)))

        event_times = []
        for ev in day_info.get('events', []):
            try:
                t_str = str(ev.get('time', '')).strip()
                if ":" in t_str:
                    ev_dt = pd.to_datetime(f"{dt.strftime('%Y-%m-%d')} {t_str}")
                    event_times.append({"time": ev_dt, "type": ev.get('type', 'unknown')})
            except: continue
        
        return {"cm": current_cm, "events": sorted(event_times, key=lambda x: x['time']), "hourly": hourly}
    except Exception as e:
        st.error(f"潮位解析エラー: {e}")
        return {"cm": 0, "phase": "解析失敗", "events": [], "hourly": []}

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
        idx = (len(h['temperature_2m']) - 25) + dt.hour
        temp = h['temperature_2m'][idx]
        wind_speed = round(h['windspeed_10m'][idx] / 3.6, 1)
        wind_deg = h['winddirection_10m'][idx]
        precip_48h = round(sum(h['precipitation'][:idx+1][-48:]), 1)

        def get_wind_dir(deg):
            dirs = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
            return dirs[int((deg + 11.25) / 22.5) % 16]
        
        return temp, wind_speed, get_wind_dir(wind_deg), precip_48h
    except: return None, None, "不明", 0.0

# --- メイン処理 ---
def main():
    cloudinary.config(
        cloud_name = st.secrets["cloudinary"]["cloud_name"],
        api_key = st.secrets["cloudinary"]["api_key"],
        api_secret = st.secrets["cloudinary"]["api_secret"],
        secure = True
    )

    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    conn = st.connection("gsheets", type=GSheetsConnection)

    @st.cache_data(ttl=600)
    def get_all_data(_conn, _url):
        d_main = _conn.read(spreadsheet=_url, ttl="10m")
        d_master = _conn.read(spreadsheet=_url, worksheet="place_master", ttl="24h")
        return d_main, d_master

    df, df_master = get_all_data(conn, url)

    tabs = st.tabs(["記録", "編集", "ギャラリー", "分析", "統計", "戦略", "マッチング", "デーモン佐藤"])
    
    with tabs[0]:
        st.markdown(f"""<div style="text-align: center; padding: 20px 0;"><img src="{icon_url}" style="width: 100px;"><h2>Kinetic Tide <span style="color: #00ffd0;">Data</span></h2></div>""", unsafe_allow_html=True)
        
        # セッション初期化
        for key, val in {"length_val":0.0, "lat":0.0, "lon":0.0, "detected_place":"新規地点", "group_id":"default", "target_dt":datetime.now()}.items():
            if key not in st.session_state: st.session_state[key] = val

        uploaded_file = st.file_uploader("魚の写真を選択", type=["jpg", "jpeg", "png"])
        
        if uploaded_file:
            img = Image.open(uploaded_file)
            exif = img._getexif()
            if exif:
                # 日時
                for tag, val in exif.items():
                    if ExifTags.TAGS.get(tag) == 'DateTimeOriginal':
                        try: st.session_state.target_dt = datetime.strptime(str(val)[:16].replace(":","/",2), '%Y/%m/%d %H:%M')
                        except: pass
                # 位置
                geo = get_geotagging(exif)
                if geo:
                    lat = get_decimal_from_dms(geo['GPSLatitude'], geo['GPSLatitudeRef'])
                    lon = get_decimal_from_dms(geo['GPSLongitude'], geo['GPSLongitudeRef'])
                    if lat and lon:
                        st.session_state.lat, st.session_state.lon = lat, lon
                        p, g = find_nearest_place(lat, lon, df_master)
                        st.session_state.detected_place, st.session_state.group_id = p, g

            st.success(f"📸 解析完了: {st.session_state.detected_place}")
            
            # 入力UI
            fish_options = ["スズキ", "ヒラスズキ", "ボウズ", "バラシ", "カサゴ", "マダイ", "チヌ", "ブリ", "アジ", "（手入力）"]
            selected_fish = st.selectbox("🐟 魚種", fish_options)
            final_fish = st.text_input("魚種名入力") if selected_fish == "（手入力）" else selected_fish
            
            place_options = ["自動判定に従う", "（新規登録）"] + sorted(df_master['place_name'].unique().tolist())
            sel_place = st.selectbox("📍 場所修正", place_options)
            if sel_place == "自動判定に従う": 
                place_name, target_gid = st.session_state.detected_place, st.session_state.group_id
            elif sel_place == "（新規登録）":
                place_name = st.text_input("新規場所名")
                target_gid = "default"
            else:
                place_name = sel_place
                target_gid = df_master[df_master['place_name']==sel_place]['group_id'].iloc[0]

            col1, col2, col3 = st.columns([1,2,1])
            if col1.button("➖ 0.5"): st.session_state.length_val -= 0.5
            len_input = col2.text_input("全長(cm)", value=str(st.session_state.length_val))
            st.session_state.length_val = normalize_float(len_input)
            if col3.button("➕ 0.5"): st.session_state.length_val += 0.5

            lure = st.text_input("🪝 ルアー")
            angler = st.selectbox("👤 釣り人", ["長元", "川口", "山川"])
            memo = st.text_area("🗒️ 備考")

            if st.button("🚀 記録する", type="primary", use_container_width=True):
                with st.spinner("送信中..."):
                    dt = st.session_state.target_dt
                    temp, wind_s, wind_d, rain48 = get_weather_data_openmeteo(st.session_state.lat, st.session_state.lon, dt)
                    m_age = get_moon_age(dt)
                    station = find_nearest_tide_station(st.session_state.lat, st.session_state.lon)
                    
                    # 潮位取得 (GitHub連携)
                    t_url = f"https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{dt.year}/{station['code']}.json"
                    t_res = requests.get(t_url)
                    t_data = get_tide_details(t_res, dt)
                    
                    # フェーズ判定
                    all_ev = t_data.get('events', [])
                    tide_phase = "不明"
                    prev_ev = next((e for e in reversed(all_ev) if e['time'] <= dt), None)
                    next_ev = next((e for e in all_ev if e['time'] > dt), None)
                    if prev_ev and next_ev:
                        p_type = "上げ" if "干" in prev_ev['type'] else "下げ"
                        step = int(((dt - prev_ev['time']).total_seconds() / (next_ev['time'] - prev_ev['time']).total_seconds()) * 10)
                        tide_phase = f"{p_type}{max(1, min(9, step))}分"

                    # 画像アップロード
                    res_img = cloudinary.uploader.upload(uploaded_file, folder="fishing_app")
                    
                    save_row = {
                        "filename": res_img.get("secure_url"), "datetime": dt.strftime("%Y/%m/%d %H:%M"),
                        "lat": st.session_state.lat, "lon": st.session_state.lon,
                        "気温": temp, "風速": wind_s, "風向": wind_d, "潮位_cm": t_data['cm'],
                        "月齢": m_age, "潮名": get_tide_name(m_age), "潮位フェーズ": tide_phase,
                        "場所": place_name, "魚種": final_fish, "全長_cm": st.session_state.length_val,
                        "ルアー": lure, "備考": memo, "group_id": target_gid, "観測所": station['name'], "釣り人": angler
                    }
                    
                    df_new = pd.concat([conn.read(spreadsheet=url), pd.DataFrame([save_row])], ignore_index=True)
                    conn.update(spreadsheet=url, data=df_new)
                    st.cache_data.clear()
                    st.success("記録完了！")
                    st.rerun()

    # --- 他のタブ ---
    with tabs[1]: show_edit_page(conn, url, get_weather_data_openmeteo, find_nearest_tide_station, get_tide_details, get_moon_age, get_tide_name)
    with tabs[2]: show_gallery_page(conn.read(spreadsheet=url, ttl="0s"))
    with tabs[3]: show_analysis_page(df)
    with tabs[4]: show_monthly_stats(df)
    with tabs[5]: show_strategy_analysis(df)
    with tabs[6]: show_matching_page(df)
    with tabs[7]: ai_module.show_ai_page(conn, url, df)

if __name__ == "__main__":
    main()
