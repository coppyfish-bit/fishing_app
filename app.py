import streamlit as st
import pandas as pd
import time
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime, timedelta
import requests
import math
import io
import cloudinary
import cloudinary.uploader
import plotly.graph_objects as go
import numpy as np

# --- 1. 位置情報・解析系関数 ---

def get_geotagging(exif):
    """EXIFからGPS情報を抽出し、辞書形式で返す"""
    if not exif:
        return None
    # GPSInfoのタグIDは 34853
    gps_info = exif.get(34853)
    if not gps_info:
        return None
    
    # 辞書のキーが数値(int)の場合と文字列("1")の場合の両方に対応
    geotagging = {
        'GPSLatitudeRef': gps_info.get(1) or gps_info.get("1"),
        'GPSLatitude':    gps_info.get(2) or gps_info.get("2"),
        'GPSLongitudeRef': gps_info.get(3) or gps_info.get("3"),
        'GPSLongitude':   gps_info.get(4) or gps_info.get("4")
    }
    
    if not geotagging['GPSLatitude'] or not geotagging['GPSLongitude']:
        return None
        
    return geotagging

def get_decimal_from_dms(dms, ref):
    """度分秒(DMS)形式を十進法に変換"""
    if not dms or not ref:
        return None
    try:
        # 要素がリストやタプルであることを想定
        d = float(dms[0])
        m = float(dms[1])
        s = float(dms[2])
        decimal = d + (m / 60.0) + (s / 3600.0)
        if ref in ['S', 'W']:
            decimal = -decimal
        return decimal
    except:
        return None

def calculate_distance(lat1, lon1, lat2, lon2):
    if None in [lat1, lon1, lat2, lon2]: return 999.0
    R = 6371.0
    dlat, dlon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return R * (2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

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

# --- 2. 気象・潮汐系関数 ---

def get_best_station(lat, lon, place_name):
    STATIONS = [
        {"name": "本渡瀬戸", "lat": 32.26, "lon": 130.13, "code": "HS"},
        {"name": "苓北",     "lat": 32.28, "lon": 130.20, "code": "RH"},
        {"name": "口之津",   "lat": 32.36, "lon": 130.12, "code": "KT"},
        {"name": "八代",     "lat": 32.31, "lon": 130.34, "code": "O5"},
    ]
    p_name = place_name if place_name else ""
    if any(k in p_name for k in ["苓北", "富岡", "都呂々", "通詞"]): return STATIONS[1]
    if any(k in p_name for k in ["本渡", "瀬戸", "下浦", "栖本"]): return STATIONS[0]
    if any(k in p_name for k in ["八代", "鏡", "日奈久", "不知火"]): return STATIONS[3]
    if any(k in p_name for k in ["口之津", "島原", "南島原", "加津佐"]): return STATIONS[2]

    best_s, min_dist = STATIONS[0], float('inf')
    for s in STATIONS:
        dist = ((lat - s["lat"])**2 + (lon - s["lon"])**2)**0.5
        if dist < min_dist:
            min_dist, best_s = dist, s
    return best_s

def get_tide_details(lat, lon, dt, place_name=""):
    station = get_best_station(lat, lon, place_name)
    st_code = str(station['code'])
    urls = [
        f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{dt.year}/{st_code.upper()}.txt",
        f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{dt.year}/{st_code.lower()}.txt"
    ]
    for url in urls:
        try:
            res = requests.get(url, timeout=10)
            if res.status_code != 200: continue
            lines = res.text.splitlines()
            date_marker = f"{str(dt.year)[2:]}{dt.month:2}{dt.day:2}{st_code.upper()}"
            target_line = next((l for l in lines if date_marker.replace(" ","") in l.replace(" ","")), None)
            if not target_line: continue

            tide_part = target_line[dt.hour*3 : (dt.hour*3)+3].strip()
            tide_cm = int(tide_part) if tide_part else 0

            events = []
            for i in range(4):
                m_start, k_start = 80 + (i*7), 108 + (i*7)
                m_str, k_str = target_line[m_start:m_start+4].strip(), target_line[k_start:k_start+4].strip()
                if m_str and m_str != "9999": events.append({"type": "満潮", "time": datetime(dt.year, dt.month, dt.day, int(m_str[:2]), int(m_str[2:]))})
                if k_str and k_str != "9999": events.append({"type": "干潮", "time": datetime(dt.year, dt.month, dt.day, int(k_str[:2]), int(k_str[2:]))})
            
            events.sort(key=lambda x: x["time"])
            next_ev = next((e for e in events if e["time"] > dt), None)
            phase = "上げ潮" if (next_ev and next_ev["type"] == "満潮") else "下げ潮"

            return {"潮位フェーズ": phase, "潮位_cm": tide_cm, "観測所": station["name"]}
        except: continue
    return {"潮位フェーズ": "取得失敗", "潮位_cm": 0, "観測所": station["name"]}

def get_weather_data(lat, lon, dt):
    try:
        is_past = dt.date() < datetime.now().date()
        url = "https://archive-api.open-meteo.com/v1/archive" if is_past else "https://api.open-meteo.com/v1/forecast"
        params = {"latitude": lat, "longitude": lon, "start_date": dt.strftime('%Y-%m-%d'), "end_date": dt.strftime('%Y-%m-%d'), "hourly": "temperature_2m,windspeed_10m,winddirection_10m,precipitation", "timezone": "Asia/Tokyo"}
        res = requests.get(url, params=params).json()
        h, idx = res.get('hourly', {}), dt.hour
        return h.get('temperature_2m')[idx], h.get('windspeed_10m')[idx], h.get('winddirection_10m')[idx], h.get('precipitation')[idx]
    except: return None, None, None, None

def get_moon_age(dt):
    base = datetime(2023, 1, 22, 5, 53)
    return round(((dt - base).total_seconds() / 86400) % 29.530588, 1)

def get_tide_name(dt):
    age = get_moon_age(dt)
    if age < 3.0 or age > 26.5: return "大潮"
    elif age < 7.0: return "中潮"
    elif age < 11.0: return "小潮"
    elif age < 13.0: return "長潮"
    elif age < 14.0: return "若潮"
    elif age < 18.0: return "大潮"
    elif age < 22.0: return "中潮"
    else: return "小潮"

def get_wind_direction_label(degree):
    if degree is None: return "不明"
    labels = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
    return labels[int((degree + 11.25) / 22.5) % 16]

# --- 3. 接続とメイン処理 ---

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    if "df" not in st.session_state: st.session_state.df = conn.read(spreadsheet=url, ttl="60s")
    if "m_df" not in st.session_state: st.session_state.m_df = conn.read(spreadsheet=url, worksheet="place_master", ttl="60s")
    df, m_df = st.session_state.df, st.session_state.m_df
except Exception as e:
    st.error(f"接続失敗: {e}")
    st.stop()



            save_data = {
                "filename": drive_url,
                "datetime": target_dt.strftime('%Y-%m-%d %H:%M'),
                "lat": float(lat_to_save), # 数値型を保証
                "lon": float(lon_to_save),
                "気温": temp,
                "風速": wind_s,
                "風向": get_wind_direction_label(wind_d),
                "潮位_cm": t_info.get("潮位_cm", 0),
                "潮名": get_tide_name(target_dt),
                "場所": final_place_name,
                "魚種": final_fish_name,
                "釣り人": angler
                # ... その他必要項目を追加 ...
            }
            
            # スプレッドシート更新ロジック（省略せずに既存のものを使用してください）
            st.success(f"保存完了！座標: {lat_to_save}, {lon_to_save}")
        except Exception as e:
            st.error(f"保存失敗: {e}")
    
# --- 2. メイン UI 制御 ---
st.set_page_config(page_title="Fishing AI Log", layout="centered")
st.title("🎣 釣果統合ログシステム")

# --- タブの作成 ---
tab1, tab2, tab3 = st.tabs(["📝 釣果登録", "🔧 履歴の修正・削除","🖼️ ギャラリー"])

# ==========================================
# タブ1: 釣果登録
# ==========================================
with tab1:
    # --- 1. データの読み込み ---
    try:
        # 接続と設定の再読み込み（セッション状態を活用）
        conn = st.connection("gsheets", type=GSheetsConnection)
        url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        # メインデータ
        if "df" not in st.session_state:
            st.session_state.df = conn.read(spreadsheet=url, ttl="5m")
        # 場所マスター
        if "m_df" not in st.session_state:
            st.session_state.m_df = conn.read(spreadsheet=url, worksheet="place_master", ttl="10m")
        
        df = st.session_state.df
        m_df = st.session_state.m_df
    except Exception as e:
        st.error(f"スプレッドシート接続エラー: {e}")
        st.stop()

# --- 📸 写真アップロード設定 ---
    # デザイン（青色ボタン）
    st.markdown("""
        <style>
        div[data-testid="stFileUploader"] section button {
            background-color: #007BFF !important;
            color: white !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
# --- 2. ファイルアップロードとEXIF解析 ---
    uploaded_file = st.file_uploader("📸 写真を選択", type=['jpg', 'jpeg'], key="main_uploader")
    
    # 【修正ポイント】ここで定義した変数を最後まで使う
    final_lat = 32.5
    final_lon = 130.0
    default_dt = datetime.now()

    if uploaded_file:
        img = Image.open(uploaded_file)
        exif = img._getexif()
        if exif:
            # --- デバッグ用コードここから ---
            st.write("🔍 EXIF解析ログ:")
            st.write(f"- EXIFタグの総数: {len(exif)}")
            # GPSInfoのタグIDは 34853 です
            if 34853 in exif:
                st.success("✅ 画像内にGPSタグ（34853）を発見しました！")
                st.write("- GPSInfoの中身:", exif[34853])
            else:
                st.error("❌ この画像にはGPS情報が書き込まれていません。")
            # --- デバッグ用コードここまで ---
        if exif:
            geotags = get_geotagging(exif)
            if geotags:
                # DMS形式から十進法へ変換
                lat_res = get_decimal_from_dms(geotags.get('GPSLatitude'), geotags.get('GPSLatitudeRef'))
                lon_res = get_decimal_from_dms(geotags.get('GPSLongitude'), geotags.get('GPSLongitudeRef'))
                if lat_res:
                    final_lat = lat_res
                    final_lon = lon_res
            
            # 日時も取得
            dt_str = exif.get(36867)
            if dt_str:
                try: default_dt = datetime.strptime(dt_str, '%Y:%m:%d %H:%M:%S')
                except: passpass

    # --- 3. 場所の判定と入力（修正版） ---
    detected_name, detected_id = find_nearest_place(final_lat, final_lon, m_df)
    
    st.markdown("### 📍 釣り場")

    # A: 登録済みリスト（初期値を「選択なし」にする）
    place_to_id = dict(zip(m_df['place_name'], m_df['group_id'])) if not m_df.empty else {}
    manual_sel = st.selectbox(
        "過去の登録地点から選ぶ", 
        ["-- リストから選ぶ場合はこちら --"] + list(place_to_id.keys()),
        key="place_manual_select_v4"
    )

    # B: 入力・表示欄
    if manual_sel != "-- リストから選ぶ場合はこちら --":
        final_place_name = manual_sel
        final_group_id = place_to_id[manual_sel]
        is_new_place = False
        st.info(f"✅ 過去の地点を選択中: {final_place_name}")
    else:
        # 自動判定された名前があれば表示、なければ空欄
        default_val = detected_name if detected_name else ""
        final_place_name = st.text_input("釣り場名（修正・新規入力可）", value=default_val)
        
        if detected_name and final_place_name == detected_name:
            final_group_id = detected_id
            is_new_place = False
            st.success(f"📌 GPSから「{detected_name}」と判定しました")
        else:
            final_group_id = int(m_df["group_id"].max() + 1) if not m_df.empty else 1
            is_new_place = True
            if final_place_name:
                st.warning(f"🆕 「{final_place_name}」を新規登録します")
# --- 4. 魚種登録（重複を削除し、1つに統合） ---
    st.subheader("🐟 魚種")
    fish_options = ["ボウズ","スズキ", "ヒラスズキ", "ターポン", "タチウオ", "コチ", "ヒラメ","カサゴ", "クロダイ", "キビレ","キジハタ","マダイ","その他（手入力）"]
    
    # 選択肢と手入力をスッキリ並べる
    selected_fish = st.selectbox("魚種を選択", fish_options, key="fish_sel_final")
    
    # 「その他」を選んだ時や、補足したい時だけ入力する欄
    manual_fish_name = st.text_input("魚種名（手入力・補足）", placeholder="例：アカハタ、またはサイズ補足など", key="fish_manual_final")

    # 最終的な保存名を決定（手入力があればそちらを優先）
    final_fish_name = manual_fish_name if manual_fish_name else selected_fish

# --- 5. 全長入力 ---
    st.markdown("""
        <style>
        div[data-testid="stNumberInput"] input {
            font-size: 40px !important;
            height: 70px !important;
            font-weight: bold !important;
            color: #FF4B4B !important;
            text-align: center !important;
        }
        div[data-testid="stNumberInput"] input::placeholder {
            font-size: 18px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    final_length = st.number_input(
        "全長 (cm)", 
        min_value=0.0, max_value=300.0, value=None, 
        placeholder="ここをタップして入力",
        step=0.1, format="%.1f", key="final_len_input_fixed"
    )

    # --- 6. その他入力項目 ---
    st.markdown("---")
    lure_sel = st.text_input("ルアー名", placeholder="例：カゲロウ125MD", key="lure_name_final")
    lure_extra = st.text_input("詳細・カラー (任意)", key="lure_color_final")
    lure_in = lure_sel + (f" ({lure_extra})" if lure_extra else "")

    angler = st.selectbox("👤 釣り人", ["長元", "川口", "山川"], key="angler_final")
    memo_in = st.text_area("メモ", placeholder="ヒットパターンなど", key="memo_final")

    # 日時入力（写真から取得したdefault_dtを初期値に）
    c1, c2 = st.columns(2)
    with c1: date_in = st.date_input("日付", default_dt.date())
    with c2: time_in = st.time_input("時刻", default_dt.time())

    # --- 7. 保存処理（1つの青いボタンに統合） ---
    st.markdown("""
        <style>
        div.stButton > button[kind="primary"] {
            background-color: #007BFF !important;
            color: white !important;
            height: 60px !important;
            font-size: 20px !important;
            font-weight: bold !important;
            border-radius: 10px !important;
        }
        </style>
    """, unsafe_allow_html=True)

# --- 保存ボタン内の処理（ここが重要！） ---

# （中略：UI部分で manual_sel や final_lat, final_lon が定義されている前提）

if st.button("🚀 釣果を記録する", type="primary", use_container_width=True):
    # 保存用の座標を確定させる
    lat_to_save = final_lat
    lon_to_save = final_lon

    # 手動選択がある場合、マスターの座標で上書き
    if manual_sel not in ["-- リストから選ぶ場合はこちら --", "-- 自動判定・新規入力 --", ""] and not m_df.empty:
        matched = m_df[m_df['place_name'] == manual_sel]
        if not matched.empty:
            lat_to_save = matched.iloc[0]['latitude']
            lon_to_save = matched.iloc[0]['longitude']

    # 座標が確定したら保存処理へ
    if lat_to_save is not None:
        try:
            target_dt = datetime.combine(date_in, time_in)
            t_info = get_tide_details(lat_to_save, lon_to_save, target_dt, final_place_name)
            temp, wind_s, wind_d, prec = get_weather_data(lat_to_save, lon_to_save, target_dt)
            save_data = {
                "filename": drive_url, 
                "datetime": target_dt.strftime('%Y-%m-%d %H:%M'),
                "date": date_in.strftime('%Y-%m-%d'), 
                "time": time_in.strftime('%H:%M'),
                "lat": lat_val, 
                "lon": lon_val, 
                "気温": temp, 
                "風速": wind_s, 
                "風向": get_wind_direction_label(wind_d) if wind_d is not None else "不明", 
                "降水量": prec,
                "潮位_cm": t_info.get("潮位_cm", 0), 
                "月齢": get_moon_age(target_dt), 
                "潮名": t_name,
                "潮位フェーズ": t_info.get("潮位フェーズ", "不明"), 
                "場所": final_place_name, 
                "魚種": final_fish_name, 
                "全長_cm": final_length if final_length is not None else 0.0,
                "ルアー": lure_in, 
                "備考": memo_in, 
                "group_id": final_group_id, 
                "観測所": t_info.get("観測所", "不明"), 
                "釣り人": angler
            }

            # --- 4. スプレッドシートへの書き込み ---
            cols = ["filename", "datetime", "date", "time", "lat", "lon", "気温", "風速", "風向", "降水量", "潮位_cm", "月齢", "潮名", "潮位フェーズ", "場所", "魚種", "全長_cm", "ルアー", "備考", "group_id", "観測所", "釣り人"]
            new_row_df = pd.DataFrame([save_data])[cols]
            
            # メインシートの更新
            current_df = conn.read(spreadsheet=url, ttl=0)
            updated_df = pd.concat([current_df, new_row_df], ignore_index=True)
            conn.update(spreadsheet=url, data=updated_df)
            
            # 新規地点の場合、場所マスターも自動更新
            if is_new_place and final_place_name:
                new_m = pd.DataFrame([{
                    "group_id": final_group_id, 
                    "place_name": final_place_name, 
                    "latitude": lat_val, 
                    "longitude": lon_val
                }])
                try:
                    current_m = conn.read(spreadsheet=url, worksheet="place_master", ttl=0)
                    updated_m = pd.concat([current_m, new_m], ignore_index=True)
                    conn.update(spreadsheet=url, worksheet="place_master", data=updated_m)
                except:
                    st.warning("⚠️ 場所マスターの更新に失敗しました（シートが存在しない可能性があります）")

            # --- 5. 完了通知と画面リセット ---
            st.success("🎉 釣果を保存しました！")
            st.balloons()
            
            # キャッシュをクリアして最新データを反映させる
            st.cache_data.clear()
            if 'df' in st.session_state:
                del st.session_state.df
            time.sleep(2)
            st.rerun()

        except Exception as e:
            st.error(f"❌ 保存エラー: {e}")
            import traceback
            st.code(traceback.format_exc())
# タブ2: 釣果の修正・削除
# ==========================================
with tab2:
    st.subheader("📸 釣果履歴（直近5件展開）")

    # API制限対策：手動リロードボタン
    if st.button("🔄 最新の履歴に更新", key="reload_history", use_container_width=True):
        st.cache_data.clear()
        if 'df' in st.session_state:
            del st.session_state.df
        st.rerun()

    # タブ2全体を包む大きな try ブロック
    try:
        # セッション状態からデータを取得
        df = st.session_state.get('df', None)
        
        if df is None or df.empty:
            st.info("履歴がまだありません。")
        else:
            # 削除時のインデックスのズレを防ぐため、コピーを作成
            target_df = df.copy()
            # 表示用に新しい順（最新が上）にする
            display_df = target_df.iloc[::-1]
            
            for i, (original_index, row) in enumerate(display_df.iterrows()):
                # 直近5件だけ最初から開く
                is_expanded = True if i < 5 else False
                
                # 表示用ラベルの作成
                d_val = row.get('date', '不明')
                f_val = row.get('魚種', '不明')
                s_val = row.get('全長_cm', row.get('全長', '0'))
                expander_label = f"📌 {d_val} | {f_val} | {s_val}cm"
                
                with st.expander(expander_label, expanded=is_expanded):
                    # --- 1. 画像と潮汐グラフ表示 ---
                    img_url = str(row.get('filename', '')).strip()
                    if img_url.startswith('http'):
                        st.image(img_url, use_container_width=True)
                        
                        # シートから潮汐データを取得してグラフ表示
                        current_lat = row.get('lat', 32.5)
                        current_lon = row.get('lon', 130.0)
                        current_tide = row.get('潮位_cm', 0)
                        current_phase = row.get('潮位フェーズ', '不明')
                        current_time = row.get('time', row.get('時刻', '12:00'))
                        current_date = row.get('date', '2026-01-01')
                        
                        display_tide_graph(
                            lat=current_lat, 
                            lon=current_lon, 
                            date_str=str(current_date), 
                            hit_time_str=str(current_time),
                            tide_val=current_tide,
                            tide_phase=current_phase
                        )
                    else:
                        st.caption("📷 画像なし")
                    
                    # --- 2. 修正用入力フォーム ---
                    # サイズ入力（数値変換エラー対策付き）
                    try:
                        f_s_val = float(s_val)
                    except:
                        f_s_val = 0.0

                    new_size = st.number_input(
                        "📏 サイズ (cm)", 
                        value=f_s_val, 
                        step=0.1, 
                        format="%.1f",
                        key=f"edit_size_{original_index}"
                    )

                    angler_list = ["長元", "川口", "山川"]
                    current_angler = row.get('釣り人', '長元')
                    new_angler = st.selectbox(
                        "👤 釣り人", 
                        angler_list, 
                        index=angler_list.index(current_angler) if current_angler in angler_list else 0,
                        key=f"edit_angler_{original_index}"
                    )

                    new_lure = st.text_input(
                        "🎣 ルアー", 
                        value=str(row.get('ルアー', '')), 
                        key=f"edit_lure_{original_index}"
                    )

                    new_memo = st.text_area(
                        "📝 備考", 
                        value=str(row.get('備考', '')), 
                        key=f"edit_memo_{original_index}"
                    )

                    # --- 3. ボタンエリア ---
                    st.write("")
                    col_btn1, col_btn2 = st.columns(2)
                    
                    with col_btn1:
                        if st.button("🆙 修正保存", key=f"update_btn_{original_index}", type="primary", use_container_width=True):
                            with st.spinner('修正中...'):
                                try:
                                    df.at[original_index, '全長_cm'] = new_size
                                    df.at[original_index, '釣り人'] = new_angler
                                    df.at[original_index, 'ルアー'] = new_lure
                                    df.at[original_index, '備考'] = new_memo
                                    conn.update(spreadsheet=url, data=df)
                                    st.success("修正しました！")
                                    st.cache_data.clear()
                                    if 'df' in st.session_state: del st.session_state.df
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"修正失敗: {e}")

                    with col_btn2:
                        if st.button("🗑️ 削除する", key=f"del_btn_{original_index}", use_container_width=True):
                            with st.spinner('削除中...'):
                                try:
                                    updated_df = df.drop(original_index)
                                    conn.update(spreadsheet=url, data=updated_df)
                                    st.success("削除しました")
                                    st.cache_data.clear()
                                    if 'df' in st.session_state: del st.session_state.df
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"削除失敗: {e}")

    except Exception as e:
        st.error(f"タブ2でエラーが発生しました: {e}")
# --- ここからタブ3 ---
with tab3:
    st.subheader("📸 釣果フォトギャラリー")
    # インデントを 'with' より4マス右に統一
    display_count = st.slider("表示件数", 5, 50, 10)
    
    if not df.empty:
        # 最新のデータから順に取得
        latest_data = df.sort_values(by=['date', 'time'], ascending=False).head(display_count)
        
        for idx, row in latest_data.iterrows():
            # --- 1. データの準備 ---
            img = str(row.get('filename', '')).strip()
            if not img.startswith('http'): 
                continue
            
            # 表示用テキストの作成
            fish_text = f"{row.get('魚種', '不明')} {row.get('全長_cm', '---')}cm"
            f_date = str(row.get('date'))
            f_time = str(row.get('time'))[:5]
            
            info_text = f"📅 {f_date} {f_time} / 📍 {row.get('場所', '---')}"
            tide_detail = f"🌊 {row.get('潮位_cm','--')}cm ({row.get('潮位フェーズ','--')})"
            env_info = f"🍃 {row.get('風向','--')} {row.get('風速','--')}m/s | 🎣 {row.get('ルアー','--')} | ☔ {row.get('降水量','--')}mm"

            # --- 2. 写真にデータを重ねて表示 (HTML) ---
            html_block = (
                f'<div style="position:relative; width:100%; border-radius:15px; overflow:hidden; margin-top:20px; box-shadow:0 4px 12px rgba(0,0,0,0.3);">'
                f'<img src="{img}" style="width:100%; display:block;">'
                # 左上：魚種タグ
                f'<div style="position:absolute; top:12px; left:12px; z-index:10; background:rgba(220,20,60,0.95); color:white; padding:5px 14px; border-radius:20px; font-weight:bold; font-size:15px;">'
                f'{fish_text}</div>'
                # 下部：グラデーションパネル
                f'<div style="position:absolute; bottom:0; left:0; right:0; z-index:5; background:linear-gradient(transparent, rgba(0,0,0,0.95) 50%); color:white; padding:40px 15px 15px 15px;">'
                f'<div style="font-size:15px; font-weight:bold; margin-bottom:8px; text-shadow: 1px 1px 2px rgba(0,0,0,0.8);">{info_text}</div>'
                f'<div style="display:flex; flex-wrap:wrap; gap:10px; font-size:12px; font-weight:500;">'
                f'<div style="background:rgba(255,255,255,0.2); padding:3px 10px; border-radius:6px; border:0.5px solid rgba(255,255,255,0.3);">{tide_detail}</div>'
                f'<div style="background:rgba(255,255,255,0.2); padding:3px 10px; border-radius:6px; border:0.5px solid rgba(255,255,255,0.3);">{env_info}</div>'
                f'</div></div></div>'
            )
            st.markdown(html_block, unsafe_allow_html=True)

            # --- 3. 潮汐グラフを表示 ---
            display_tide_graph(
                lat=row.get('lat', 32.5),
                lon=row.get('lon', 130.0), 
                date_str=f_date, 
                hit_time_str=f_time,
                tide_val=row.get('潮位_cm', 150),
                tide_phase=row.get('潮位フェーズ', '---')
            )
            
            st.write("---")
    else:
        st.info("釣果データがありません。")
























































































































































































































































































