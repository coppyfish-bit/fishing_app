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
import streamlit.components.v1 as components

# モジュールインポート
from edit_module import show_edit_page
from gallery_module import show_gallery_page
from analysis_module import show_analysis_page
from monthly_stats import show_monthly_stats
from matching_module import show_matching_page
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

# 2026-03-04: AIとの会話は学習に使用したり外部に漏れたりしません。
# 私の釣果情報を他の人に共有しないでください。

# --- 1. ブラウザ設定 ---
icon_url = "https://res.cloudinary.com/dmkvcofvn/image/upload/v1771574282/ktd_rnaphy.png"

st.set_page_config(
    page_title="Seabass Strategy App",
    page_icon=icon_url,
    layout="wide"
)

# ホーム画面アイコン設定
components.html(
    f"""
    <script>
        var link = window.parent.document.createElement('link');
        link.rel = 'apple-touch-icon';
        link.href = '{icon_url}';
        window.parent.document.getElementsByTagName('head')[0].appendChild(link);
        
        var link2 = window.parent.document.createElement('link');
        link2.rel = 'shortcut icon';
        link2.href = '{icon_url}';
        window.parent.document.getElementsByTagName('head')[0].appendChild(link2);
    </script>
    """,
    height=0,
)

# --- 2. 設定 & 地点データ ---
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
    {"name": "苓北", "lat": 32.4667, "lon": 130.0333, "code": "RH"},
    {"name": "三角", "lat": 32.6167, "lon": 130.4500, "code": "MS"},
    {"name": "本渡瀬戸", "lat": 32.4333, "lon": 130.2167, "code": "HS"},
    {"name": "八代", "lat": 32.5167, "lon": 130.5667, "code": "O5"},
    {"name": "水俣", "lat": 32.2000, "lon": 130.3667, "code": "O7"},
    {"name": "熊本", "lat": 32.7500, "lon": 130.5667, "code": "KU"},
    {"name": "大牟田", "lat": 33.0167, "lon": 130.4167, "code": "O6"},
    {"name": "大浦", "lat": 32.9833, "lon": 130.2167, "code": "OU"},
    {"name": "口之津", "lat": 32.6000, "lon": 130.2000, "code": "KT"},
    {"name": "長崎", "lat": 32.7333, "lon": 129.8667, "code": "NS"},
    {"name": "佐世保", "lat": 33.1500, "lon": 129.7167, "code": "QD"},
    {"name": "博多", "lat": 33.6167, "lon": 130.4000, "code": "QF"},
    {"name": "鹿児島", "lat": 31.6000, "lon": 130.5667, "code": "KG"},
    {"name": "枕崎", "lat": 31.2667, "lon": 130.3000, "code": "MK"},
    {"name": "油津", "lat": 31.5833, "lon": 131.4167, "code": "AB"},
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


def get_exif_data(image_file):
    """画像からExifデータを抽出する"""
    image = Image.open(image_file)
    exif_data = image._getexif()
    if not exif_data:
        return None, None, None

    decoded_exif = {TAGS.get(t, t): v for t, v in exif_data.items()}
    
    # 1. 日時の取得 (DateTimeOriginal)
    dt_str = decoded_exif.get("DateTimeOriginal")
    dt_obj = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S") if dt_str else None

    # 2. 位置情報の取得 (GPSInfo)
    gps_info = decoded_exif.get("GPSInfo")
    lat = lon = None
    
    if gps_info:
        # 度分秒(DMS)を十進法(Decimal)に変換する補助関数が必要
        def convert_to_degrees(value):
            d, m, s = value
            return d + (m / 60.0) + (s / 3600.0)

        lat = convert_to_degrees(gps_info[2])
        if gps_info[1] == 'S': lat = -lat
        lon = convert_to_degrees(gps_info[4])
        if gps_info[3] == 'W': lon = -lon

    return dt_obj, lat, lon
# --- 3. 潮位・気象取得関数群 ---

def get_tide_details(station_code, dt):
    """
    GitHub上のJSONから潮位・フェーズ・イベントを取得 (修正版)
    """
    year = str(dt.year)
    url = f"https://raw.githubusercontent.com/coppyfish-bit/fishing_app/main/data/{year}/{station_code}.json"
    
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200: return None
        data_json = r.json().get('data', [])
        
        target_date_str = dt.strftime("%Y-%m-%d")
        day_info = next((i for i in data_json if i['date'] == target_date_str), None)
        if not day_info: return None

        # 潮位補間計算
        hourly = day_info['hourly']
        h, mi = dt.hour, dt.minute
        t1 = hourly[h]
        t2 = hourly[(h + 1) % 24]
        current_cm = int(round(t1 + (t2 - t1) * (mi / 60.0)))

        # イベント整形
        events = []
        for ev in day_info['events']:
            time_raw = str(ev['time']).replace(" ", "")
            if ":" in time_raw:
                try:
                    h_p, m_p = time_raw.split(":")
                    time_cln = f"{int(h_p):02d}:{int(m_p):02d}"
                    ev_time = datetime.strptime(f"{target_date_str} {time_cln}", "%Y-%m-%d %H:%M")
                    events.append({"time": ev_time, "type": "満潮" if "high" in ev['type'].lower() else "干潮"})
                except: continue
        
        events = sorted(events, key=lambda x: x['time'])
        
        # フェーズ判定（上げ10分を解消）
        phase_text = "不明"
        prev_ev = next((e for e in reversed(events) if e['time'] <= dt), None)
        next_ev = next((e for e in events if e['time'] > dt), None)
        
        if prev_ev and next_ev:
            total_sec = (next_ev['time'] - prev_ev['time']).total_seconds()
            elapsed_sec = (dt - prev_ev['time']).total_seconds()
            
            if total_sec > 0:
                step = int((elapsed_sec / total_sec) * 10)
                # 次のイベントまで10分以内、またはステップが9（ほぼ完了）なら「満潮/干潮」
                time_to_next = (next_ev['time'] - dt).total_seconds()
                if time_to_next < 600 or step >= 9:
                    phase_text = next_ev['type']
                elif elapsed_sec < 600 or step <= 0:
                    phase_text = prev_ev['type']
                else:
                    label = "上げ" if prev_ev['type'] == "干潮" else "下げ"
                    phase_text = f"{label}{step + 1}分"
        elif prev_ev: # 夜中などで次のイベントがない場合
            phase_text = prev_ev['type']

        return {"cm": current_cm, "phase": phase_text, "events": events}
    except:
        return None

def get_moon_age(dt):
    """
    指定された日時の月齢を計算する（簡易式）
    """
    year, month, day = dt.year, dt.month, dt.day
    if month < 3:
        year -= 1
        month += 12
    # 2009年基準の簡易計算式
    age = (((year - 2009) % 19) * 11 + month + day) % 30
    return age  # ← ここが _age になっていないか確認

def get_tide_name(moon_age):
    # 潮名判定ロジック
    if moon_age in [0, 1, 2, 14, 15, 16, 17, 29, 30]: return "大潮"
    if moon_age in [3, 4, 5, 18, 19, 20]: return "中潮"
    if moon_age in [6, 7, 8, 21, 22, 23]: return "小潮"
    if moon_age in [9, 24]: return "長潮"
    if moon_age in [10, 25]: return "若潮"
    return "中潮"

# (既存の補助関数: get_geotagging, get_decimal_from_dms, normalize_float, find_nearest_place, get_moon_age, get_tide_name は維持)
def find_nearest_tide_station(lat, lon):
    distances = []
    for s in TIDE_STATIONS:
        d = np.sqrt((s['lat'] - lat)**2 + (s['lon'] - lon)**2)
        distances.append(d)
    return TIDE_STATIONS[np.argmin(distances)]

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

# --- 4. メイン処理 ---
def main():
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    
    @st.cache_data(ttl=600)
    def get_all_data(_conn, _url):
        d_main = _conn.read(spreadsheet=_url, ttl="10m")
        d_master = _conn.read(spreadsheet=_url, worksheet="place_master", ttl="1h")
        return d_main, d_master
    
    df, df_master = get_all_data(conn, url)
    
    tabs = st.tabs(["記録", "編集", "ギャラリー", "分析", "統計", "戦略", "マッチング", "デーモン佐藤"])
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = tabs

    with tab1:
        # ロゴとスタイルの表示（略：既存のHTML/CSS）
        st.markdown(f"""<div style="text-align: center; padding: 20px 0;"><img src="{icon_url}" style="width: 120px;"><h1 style="color:#ffffff;">Kinetic Tide <span style="color:#00ffd0;">Data</span></h1></div>""", unsafe_allow_html=True)

        if "length_val" not in st.session_state: st.session_state.length_val = 0.0
        if "lat" not in st.session_state: st.session_state.lat = 0.0
        if "lon" not in st.session_state: st.session_state.lon = 0.0
        if "target_dt" not in st.session_state: st.session_state.target_dt = datetime.now()

        uploaded_file = st.file_uploader("魚の写真を選択してください", type=["jpg", "jpeg", "png"])
        
        if uploaded_file:
            img_for_upload = Image.open(uploaded_file)
            exif = img_for_upload._getexif()
            if exif:
                # 日時・場所解析ロジック（略：既存と同じ）
                for tag_id, value in exif.items():
                    tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                    if tag_name == 'DateTimeOriginal':
                        try:
                            clean_val = str(value).strip()[:16].replace(":", "/", 2)
                            st.session_state.target_dt = datetime.strptime(clean_val, '%Y/%m/%d %H:%M')
                        except: pass
                # GPS解析（略）

            st.success(f"📸 解析完了: {st.session_state.target_dt.strftime('%Y/%m/%d %H:%M')}")

            # 入力フィールド群（略：既存と同じ魚種、場所、全長、釣り人、メモ）
            fish_options = ["スズキ", "ヒラスズキ", "ボウズ", "バラシ", "カサゴ", "ターポン", "タチウオ", "マダイ", "チヌ", "キビレ", "ブリ", "アジ", "（手入力）"]
            selected_fish = st.selectbox("🐟 魚種を選択", fish_options)
            final_fish_name = st.text_input("魚種名を入力") if selected_fish == "（手入力）" else selected_fish
            
            # 場所名取得（略：既存と同じ）
            place_name = st.text_input("場所名を確認/修正", value=getattr(st.session_state, 'detected_place', '新規地点'))
            target_group_id = getattr(st.session_state, 'group_id', 'default')

            # 全長入力
            c1, c2, c3 = st.columns([1, 2, 1])
            if c1.button("➖ 0.5"): st.session_state.length_val = max(0.0, st.session_state.length_val - 0.5)
            length_text = c2.text_input("全長(cm)", value=str(st.session_state.length_val))
            st.session_state.length_val = float(length_text) if length_text else 0.0
            if c3.button("➕ 0.5"): st.session_state.length_val += 0.5

            lure = st.text_input("🪝 ルアー/仕掛け")
            angler = st.selectbox("👤 釣り人", ["長元", "川口", "山川"])
            memo = st.text_area("🗒️ 備考")

            if st.button("🚀 釣果を記録する", use_container_width=True, type="primary"):
                try:
                    with st.spinner("📊 潮汐・気象データを照合中..."):
                        target_dt = st.session_state.target_dt
                        
                        # 気象取得
                        temp, wind_s, wind_d, rain_48 = get_weather_data_openmeteo(st.session_state.lat, st.session_state.lon, target_dt)
                        moon_val = get_moon_age(dt_obj) 

                        new_data = {
                            "月齢": moon_val, 
                            ...
                        }
                        t_name = get_tide_name(m_age)
                        station_info = find_nearest_tide_station(st.session_state.lat, st.session_state.lon)
                        
                        # 潮汐取得 (GitHub JSON方式)
                        t_data = get_tide_details(station_info['code'], target_dt)
                        
                        if t_data:
                            tide_cm = t_data['cm']
                            tide_phase = t_data['phase']
                            all_events = t_data['events']
                            
                            # 次の干満・直前の干満を特定
                            next_h = next((e['time'] for e in all_events if e['time'] > target_dt and e['type'] == "満潮"), None)
                            next_l = next((e['time'] for e in all_events if e['time'] > target_dt and e['type'] == "干潮"), None)
                            prev_h = next((e['time'] for e in reversed(all_events) if e['time'] <= target_dt and e['type'] == "満潮"), None)
                            prev_l = next((e['time'] for e in reversed(all_events) if e['time'] <= target_dt and e['type'] == "干潮"), None)
                            
                            val_next_high = int((next_h - target_dt).total_seconds() / 60) if next_h else ""
                            val_next_low = int((next_l - target_dt).total_seconds() / 60) if next_l else ""
                        else:
                            st.error("潮汐データの取得に失敗しました。")
                            return

                        # 画像リサイズ・Cloudinary保存（略：既存と同じ）
                        img_final = Image.open(uploaded_file)
                        img_bytes = io.BytesIO()
                        img_final.convert('RGB').save(img_bytes, format='JPEG', quality=70)
                        img_bytes.seek(0)
                        res = cloudinary.uploader.upload(img_bytes, folder="fishing_app")

                        # 保存データ作成
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

                        # Sheets保存
                        df_main = conn.read(spreadsheet=url)
                        updated_df = pd.concat([df_main, pd.DataFrame([save_data])], ignore_index=True)
                        conn.update(spreadsheet=url, data=updated_df)
                        
                        st.cache_data.clear()
                        st.success("✅ 潮汐も含め正確に記録されました！")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()

                except Exception as e:
                    st.error(f"❌ 保存失敗: {e}")

    # 他のタブ（編集、ギャラリー等）は既存のまま
# --- tab2: 登録情報の修正・削除 ---
    with tab2:
        # edit_module.py の show_edit_page を呼び出す
        show_edit_page(
            conn, 
            url, 
            get_weather_data_openmeteo,   # weather_func に対応
            find_nearest_tide_station,   # station_func に対応
            get_tide_details,            # tide_func に対応
            get_moon_age,                # moon_func に対応
            get_tide_name                # tide_name_func に対応
        )
    # --- tab3: ギャラリーページ ---
    with tab3:
        # ギャラリーも最新の状態を反映させるため、保存直後などの場合は
        # キャッシュなしのデータを渡すようにします
        df_for_gallery = conn.read(spreadsheet=url, ttl="0s")
        show_gallery_page(df_for_gallery)
    with tab4: show_analysis_page(df)
    with tab5: show_monthly_stats(df)
    with tab6:
        from strategy_analysis import show_strategy_analysis
        show_strategy_analysis(df)
    with tab7: show_matching_page(df)
    with tab8:
        import ai_module
        ai_module.show_ai_page(conn, url, df)

if __name__ == "__main__":
    main()










