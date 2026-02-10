import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime, timedelta
import requests
import math
import io
import cloudinary
import cloudinary.uploader
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import requests
import pandas as pd
import plotly.graph_objects as go

# キャッシュを有効化（1時間は同じリクエストを再送しない）
@st.cache_data(ttl=3600)
def fetch_tide_data_safe(lat, lon, date_str):
    url = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&hourly=tide_height&start_date={date_str}&end_date={date_str}"
    try:
        response = requests.get(url, timeout=3.0) # タイムアウトを短く設定
        if response.status_code == 200:
            return response.json()
    except:
        return None
    return None

def display_tide_graph(lat, lon, date_str, hit_time_str):
    try:
        # 1. データの整形（念のためここでも行う）
        clean_date = str(date_str).split(' ')[0].replace('/', '-')
        
        # 2. URL作成
        url = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&hourly=tide_height&start_date={clean_date}&end_date={clean_date}"
        
        # 3. 通信実行
        response = requests.get(url, timeout=5.0)
        
        # 4. API自体のエラー（404や400）をチェック
        if response.status_code != 200:
            st.error(f"❌ API接続エラー (Code: {response.status_code})")
            st.write("理由:", response.json().get('reason', '不明なエラー'))
            return

        data = response.json()

        # 5. グラフ描画（ここが以前の「読み込めませんでした」の正体である可能性大）
        times = pd.to_datetime(data['hourly']['time'])
        heights = data['hourly']['tide_height']
        tide_df = pd.DataFrame({'time': times, 'height': heights})

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=tide_df['time'], y=tide_df['height'], fill='tozeroy'))
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        # 💡 ここがポイント：本当のエラーメッセージを画面に出す
        st.error(f"❌ 詳細エラー: {e}")
        # もし座標が原因ならここにヒントが出るはずです
        if "NoneType" in str(e):
            st.warning("緯度・経度が空（None）になっている可能性があります。")
    # (この下に既存のグラフ描画コードを続ける)

# --- 🌊 APIから潮位を取得してグラフ化する関数 ---
def display_tide_graph(lat, lon, date_str, hit_time_str):
    try:
        # Open-Meteo API (海洋データ)
        url = f"https://marine-api.open-meteo.com/v1/marine?latitude={lat}&longitude={lon}&hourly=tide_height&start_date={date_str}&end_date={date_str}"
        response = requests.get(url, timeout=5)
        data = response.json()

        times = pd.to_datetime(data['hourly']['time'])
        heights = data['hourly']['tide_height']
        tide_df = pd.DataFrame({'time': times, 'height': heights})

        # グラフ作成
        fig = go.Figure()

        # 潮汐曲線（塗りつぶしありで海っぽく）
        fig.add_trace(go.Scatter(
            x=tide_df['time'], y=tide_df['height'],
            mode='lines',
            fill='tozeroy',
            line=dict(color='#007BFF', width=3),
            name='潮位'
        ))

        # ヒット時刻のマーカー
        if hit_time_str:
            hit_datetime = pd.to_datetime(f"{date_str} {hit_time_str}")
            # 最も近い時間の潮位を取得
            idx = (tide_df['time'] - hit_datetime).abs().idxmin()
            hit_height = tide_df.loc[idx, 'height']

            fig.add_trace(go.Scatter(
                x=[hit_datetime], y=[hit_height],
                mode='markers+text',
                text=["HIT!"], textposition="top center",
                marker=dict(color='red', size=12, symbol='star'),
                name='ヒット時刻'
            ))

        fig.update_layout(
            height=250,
            margin=dict(l=0, r=0, t=20, b=0),
            xaxis=dict(tickformat="%H:%M", font=dict(size=10)),
            yaxis=dict(title="潮位 (m)", side="right"),
            showlegend=False,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.caption(f"⚠️ タイドグラフを読み込めませんでした")

def upload_to_drive(uploaded_file):
    # Secretsから設定を読み込み（関数を呼ぶたびに確実に設定）
    import cloudinary.uploader # 追加
    cloudinary.config(
        cloud_name = st.secrets["cloudinary"]["cloud_name"],
        api_key = st.secrets["cloudinary"]["api_key"],
        api_secret = st.secrets["cloudinary"]["api_secret"],
        secure = True
    )
    
    # Cloudinaryへアップロード
    response = cloudinary.uploader.upload(
        uploaded_file,
        folder = "fishing_app",
        transformation = [
            {'width': 800, 'crop': "limit"},
            {'quality': "auto", 'fetch_format': "auto"}
        ]
    )
    return response['secure_url']
    
    # 保存された画像のURLを返す（スプレッドシートにはこの短いURLが書かれます）
    return response['secure_url']
    
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

def update_spreadsheet(df):
    """
    アプリ上で編集・削除した後のDataFrameをスプレッドシートに丸ごと上書きする
    """
    try:
        # スプレッドシートを開く
        sh = gc.open_by_key(st.secrets["gcp_service_account"]["spreadsheet_id"])
        worksheet = sh.get_worksheet(0)
        
        # 既存の内容を消去して、新しいデータを書き込む
        worksheet.clear()
        # ヘッダーとデータをリスト形式に変換して書き込み
        set_with_dataframe(worksheet, df)
        st.success("スプレッドシートを更新しました！")
    except Exception as e:
        st.error(f"更新に失敗しました: {e}")


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

    # --- 3. 場所の判定と入力 ---
    detected_name, detected_id = find_nearest_place(auto_lat, auto_lon, m_df)
    is_new_place = False

    st.markdown("### 📍 釣り場")
    if detected_name:
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

    # --- 4. 魚種登録 ---
    st.subheader("🐟 魚種")
    fish_options = ["スズキ", "ヒラスズキ", "ターポン", "タチウオ", "コチ", "ヒラメ","カサゴ", "クロダイ", "キビレ","キジハタ","マダイ","その他（手入力）"]
    selected_fish = st.selectbox("魚種を選択", fish_options)
    manual_fish_name = st.text_input("魚種名（手入力）", placeholder="例：アカハタ、または魚種の補足など")

    if manual_fish_name:
        final_fish_name = manual_fish_name
    else:
        final_fish_name = selected_fish

# --- 4. 魚種登録 ---
    st.subheader("🐟 魚種")
    fish_options = ["スズキ", "ヒラスズキ", "ターポン", "タチウオ", "コチ", "ヒラメ","カサゴ", "クロダイ", "キビレ","キジハタ","マダイ","その他（手入力）"]
    selected_fish = st.selectbox("魚種を選択", fish_options, key="fish_sel_final")
    manual_fish_name = st.text_input("魚種名（手入力）", placeholder="例：アカハタなど", key="fish_manual_final")

    final_fish_name = manual_fish_name if manual_fish_name else selected_fish

# ==========================================
    # 📏 全長入力：見切れないプレースホルダー版
    # ==========================================
    
    # デザイン調整：入力後の数字は大きく、プレースホルダーは収まるサイズに
    st.markdown("""
        <style>
        /* 入力後の数字のデザイン */
        div[data-testid="stNumberInput"] input {
            font-size: 40px !important; /* 少しだけ小さくして安定感を出す */
            height: 70px !important;
            font-weight: bold !important;
            color: #FF4B4B !important;
            text-align: center !important;
        }
        /* 入力前の説明文字（プレースホルダー）のサイズだけを小さく調整 */
        div[data-testid="stNumberInput"] input::placeholder {
            font-size: 18px !important; 
            font-weight: normal !important;
            color: #888 !important;
        }
        /* ラベルの調整 */
        div[data-testid="stNumberInput"] label p {
            font-size: 16px !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # メイン入力
    val = st.number_input(
        "全長 (cm)", 
        min_value=0.0, 
        max_value=300.0, 
        value=None, 
        placeholder="ここをタップして入力",
        step=0.1, 
        format="%.1f",
        key="final_len_input_fixed"
    )

    # 保存用の値確定
    final_length = val if val is not None else 0.0
    # --- 6. その他入力項目 ---
    st.markdown("---")
    st.markdown("**ルアー・仕掛け**")
    lure_sel = st.text_input("ルアー名  コピペ用 50s 55 60f 60s 60ES 70f 70s 70ES 73 80f 80s 82s 87 88 90f 90s 95f 95ss 100f 100s 100ss 110f 110s 111f 120f 120s 124f 125f 125ss 130f 130s 140f 140s 150f 150s 156MD 160f 160s 165f 170f 170J 180f 190f 190ss",placeholder="例：カゲロウ125MD ←数字、英字は半角でお願いします", key="lure_name_final")
    lure_extra = st.text_input("詳細・カラー (任意)", key="lure_color_final")
    lure_in = lure_sel + (f" ({lure_extra})" if lure_extra else "")

    angler = st.selectbox("👤 釣り人", ["長元", "川口", "山川"], key="angler_final")

    st.markdown("**メモ**")
    memo_in = st.text_area("", placeholder="ヒットパターンなど", label_visibility="collapsed", key="memo_final")


   # --- 7. 保存ボタンのデザイン（青色に変更） ---
    st.markdown("""
        <style>
        /* 保存ボタン（Primaryボタン）の色を青に変更 */
        div.stButton > button[kind="primary"] {
            background-color: #007BFF !important; /* 鮮やかな青 */
            color: white !important;
            border: none !important;
            height: 60px !important;
            font-size: 20px !important;
            font-weight: bold !important;
            border-radius: 10px !important;
            transition: 0.3s;
        }
        /* ホバー時（指で触れた時）の色調整 */
        div.stButton > button[kind="primary"]:hover {
            background-color: #0056b3 !important;
            border-color: #0056b3 !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.write("")
    # type="primary" を指定することで、上記の青色CSSが適用されます
    submit = st.button("釣果を記録する", type="primary", use_container_width=True, key="blue_submit_btn")

    # --- 8. 保存処理実行 ---
    if submit:
        # 必須入力チェック（final_place_nameが定義されていることを確認してください）
        if 'final_place_name' not in locals() or not final_place_name:
            st.error("⚠️ 釣り場名を入力してください。")
        else:
            drive_url = "" 
            # 1. 画像アップロード (Cloudinary)
            if uploaded_file:
                with st.spinner('📸 画像を処理中...'):
                    try:
                        import io
                        from PIL import Image
                        import cloudinary
                        import cloudinary.uploader

                        # ファイルを先頭から読み直す
                        uploaded_file.seek(0)
                        input_image = Image.open(uploaded_file)
                        rgb_image = input_image.convert('RGB')
                        
                        img_byte_arr = io.BytesIO()
                        rgb_image.save(img_byte_arr, format='JPEG', quality=85)
                        img_data = img_byte_arr.getvalue()

                        # Cloudinary設定
                        cloudinary.config(
                            cloud_name = st.secrets["cloudinary"]["cloud_name"],
                            api_key = st.secrets["cloudinary"]["api_key"],
                            api_secret = st.secrets["cloudinary"]["api_secret"],
                            secure = True
                        )
                        
                        upload_result = cloudinary.uploader.upload(
                            img_data,
                            folder = "fishing_app",
                            transformation = [
                                {'width': 800, 'crop': "limit"},
                                {'quality': "auto", 'fetch_format': "auto"}
                            ]
                        )
                        drive_url = upload_result.get("secure_url")
                        
                    except Exception as e:
                        st.error(f"❌ 画像アップロード失敗: {e}")
                        st.stop()

            # 2. データの解析と保存
            with st.spinner('📊 データを解析して保存中...'):
                try:
                    target_dt = datetime.combine(date_in, time_in)
                    t_name = get_tide_name(target_dt)
                    t_info = get_tide_details(lat_in, lon_in, target_dt, final_place_name)
                    temp, wind_s, wind_d, prec = get_weather_data(lat_in, lon_in, target_dt)

                    # 保存用データ（26項目：釣り人を含む）
                    save_data = {
                        "filename": drive_url,
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
                        "魚種": final_fish_name,
                        "全長_cm": length_in, 
                        "ルアー": lure_in, 
                        "備考": memo_in,
                        "group_id": final_group_id, 
                        "観測所": t_info.get("観測所", "不明"),
                        "釣り人": angler
                    }

                    # カラムリスト
                    cols = ["filename", "datetime", "date", "time", "lat", "lon", "気温", "風速", "風向", "降水量", "潮位_cm", "月齢", "潮名", "次の満潮まで_分", "次の干潮まで_分", "直前の満潮_時刻", "直前の干潮_時刻", "潮位フェーズ", "場所", "魚種", "全長_cm", "ルアー", "備考", "group_id", "観測所", "釣り人"]
                    
                    new_row_df = pd.DataFrame([save_data])[cols]
                    
                    # スプレッドシート更新
                    updated_df = pd.concat([st.session_state.df, new_row_df], ignore_index=True)
                    conn.update(spreadsheet=url, data=updated_df)
                    
                    # 場所マスター更新（新規地点の場合）
                    if is_new_place:
                        new_m = pd.DataFrame([{"group_id": final_group_id, "place_name": final_place_name, "latitude": lat_in, "longitude": lon_in}])
                        updated_m = pd.concat([st.session_state.m_df, new_m], ignore_index=True)
                        conn.update(spreadsheet=url, worksheet="place_master", data=updated_m)

                    st.success(f"🎉 {final_place_name} での釣果を保存しました！")
                    st.balloons()
                    
                    # キャッシュをクリア
                    st.cache_data.clear()
                    if "df" in st.session_state: 
                        del st.session_state.df
                    
                    # 【重要】少し待ってから画面をリロードしてメッセージを消す
                    import time
                    time.sleep(2) 
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ 保存エラーが発生しました: {e}")
# ==========================================
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
                    # --- 1. 画像表示 ---
                    img_url = str(row.get('filename', '')).strip()
                    if img_url.startswith('http'):
                        st.image(img_url, use_container_width=True)
                        # タブ3のループ内、st.image(img_url...) のすぐ下あたりに追加
                        # 仮の場所データ（釣り場の緯度経度があればそれを使う）
                        test_lat = 33.5  # 例：長崎周辺
                        test_lon = 129.8
                        
                        # グラフ表示関数の実行
                        display_tide_graph(
                            lat=test_lat, 
                            lon=test_lon, 
                            date_str=row.get('date', '2024-01-01'), # スプレッドシートの日付
                            hit_time_str=row.get('時刻', '12:00')   # スプレッドシートの時刻
                        )
                    else:
                        st.caption("📷 画像なし")
                    
                    # --- 2. 修正用入力フォーム（項目を4つに厳選） ---
                    new_size = st.number_input(
                        "📏 サイズ (cm)", 
                        value=float(s_val), 
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

                    # --- 3. ボタンエリア（修正と削除を横並びに） ---
                    st.write("")
                    col_btn1, col_btn2 = st.columns(2)
                    
                    with col_btn1:
                        if st.button("🆙 修正保存", key=f"update_btn_{original_index}", type="primary", use_container_width=True):
                            # データ更新
                            df.at[original_index, '全長_cm'] = new_size
                            df.at[original_index, '釣り人'] = new_angler
                            df.at[original_index, 'ルアー'] = new_lure
                            df.at[original_index, '備考'] = new_memo
                            
                            # 保存実行（conn, url が定義されている前提）
                            conn.update(spreadsheet=url, data=df)
                            st.success("修正しました！")
                            st.cache_data.clear()
                            if 'df' in st.session_state: del st.session_state.df
                            st.rerun()

                    with col_btn2:
                        # 削除ボタン。誤操作防止のため type="secondary"（または指定なし）が推奨ですが、統一のため記述
                        if st.button("🗑️ 削除する", key=f"del_btn_{original_index}", use_container_width=True):
                            with st.spinner('🗑️ 削除中...'):
                                try:
                                    updated_df = df.drop(original_index)
                                    conn.update(spreadsheet=url, data=updated_df)
                                    st.cache_data.clear()
                                    if 'df' in st.session_state: del st.session_state.df
                                    st.success("削除しました")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"削除失敗: {e}")

    except Exception as e:
        st.error(f"タブ2でエラーが発生しました: {e}")

# ==========================================
# タブ3: ギャラリー（動的タイドグラフ搭載版）
# ==========================================
with tab3:
    st.subheader("🖼️ 釣果フォトギャラリー")

    if 'df' in st.session_state and not st.session_state.df.empty:
        # --- 変数定義 ---
        SIZE_COL = "全長_cm"
        FISH_COL = "魚種"
        PLACE_COL = "場所"
        PHASE_COL = "潮位フェーズ"
        TIDE_NAME_COL = "潮名"
        TIDE_CM_COL = "潮位_cm"
        LURE_COL = "ルアー"
        WIND_SPD_COL = "風速"
        WIND_DIR_COL = "風向"
        RAIN_COL = "降水量"
        ANGLER_COL = "釣り人"

        df_gallery = st.session_state.df.copy()
        df_gallery['date'] = pd.to_datetime(df_gallery['date']).dt.date

        # --- 絞り込みセクション ---
        st.write("🔍 絞り込み条件")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            min_d, max_d = df_gallery['date'].min(), df_gallery['date'].max()
            date_range = st.date_input("日付範囲", value=(min_d, max_d), key="gal_date")
        with col_f2:
            unique_places = ["すべて"] + sorted(df_gallery[PLACE_COL].dropna().unique().tolist())
            select_place = st.selectbox("場所を選択", unique_places, key="gal_place_select")

        col_f3, col_f4, col_f5 = st.columns(3)
        with col_f3:
            unique_fish = ["すべて"] + sorted(df_gallery[FISH_COL].dropna().unique().tolist())
            select_fish = st.selectbox("魚種を選択", unique_fish, key="gal_fish_select")
        with col_f4:
            min_size = st.number_input("◯◯cm以上", min_value=0.0, step=1.0, value=0.0, key="gal_size_input")
        with col_f5:
            tide_filter = st.radio("潮位方向", ["すべて", "上げ", "下げ"], horizontal=True, key="gal_tide_dir")

        # --- フィルタリング実行 ---
        if isinstance(date_range, tuple) and len(date_range) == 2:
            df_gallery = df_gallery[(df_gallery['date'] >= date_range[0]) & (df_gallery['date'] <= date_range[1])]
        if select_place != "すべて":
            df_gallery = df_gallery[df_gallery[PLACE_COL] == select_place]
        if select_fish != "すべて":
            df_gallery = df_gallery[df_gallery[FISH_COL] == select_fish]
        if SIZE_COL in df_gallery.columns:
            df_gallery[SIZE_COL] = pd.to_numeric(df_gallery[SIZE_COL], errors='coerce').fillna(0)
            df_gallery = df_gallery[df_gallery[SIZE_COL] >= min_size]
        if tide_filter != "すべて":
            df_gallery = df_gallery[df_gallery[PHASE_COL].str.contains(tide_filter, na=False)]

        # 最新順
        df_gallery = df_gallery.iloc[::-1]

        # --- 1. 直近10件の表示 ---
        st.write("### 🆕 最新の釣果（10件）")
        latest_10 = df_gallery.head(10)
        
        for idx, row in latest_10.iterrows():
            with st.container(border=True):
                col_img, col_info = st.columns([1, 1])
                with col_img:
                    img_url = str(row.get('filename', '')).strip()
                    if img_url.startswith('http'):
                        st.image(img_url, use_container_width=True)
                    else:
                        st.info("📷 画像なし")
                
                with col_info:
                    st.markdown(f"### {row.get(FISH_COL, '不明')} ({row.get(SIZE_COL, '---')}cm)")
                    st.write(f"📅 {row.get('date', '---')} {row.get('time', '')}")
                    st.write(f"📍 {row.get(PLACE_COL, '---')} | 👤 {row.get(ANGLER_COL, '---')}")
                    st.write(f"🌊 {row.get(TIDE_NAME_COL, '---')} ({row.get(PHASE_COL, '---')})")
                    if row.get(LURE_COL):
                        st.caption(f"🎣 {row[LURE_COL]}")

                # --- 動的タイドグラフ（詳細タブの中に配置） ---
                with st.expander("📊 この時のタイドグラフを表示"):
                    # 緯度経度（データにない場合はデフォルト値を設定）
                    lat = row.get('lat', 33.5) 
                    lon = row.get('lon', 129.8)
                    date_str = str(row.get('date'))
                    time_str = str(row.get('time', '12:00'))
                    
                    # API関数を呼び出し（以前作成した関数 display_tide_graph がある前提）
                    display_tide_graph(lat, lon, date_str, time_str)

        # --- 2. 11件目以降のリスト表示 ---
        if len(df_gallery) > 10:
            st.write("---")
            st.write("### 📜 過去の履歴リスト（11件目以降）")
            past_logs = df_gallery.iloc[10:].copy()
            past_logs['list_label'] = past_logs['date'].astype(str) + " | " + past_logs[FISH_COL].astype(str) + " | " + past_logs[SIZE_COL].astype(str) + "cm"
            
            selected_log_label = st.selectbox("記録を選択して詳細を表示", ["選択してください"] + past_logs['list_label'].tolist())
            
            if selected_log_label != "選択してください":
                selected_row = past_logs[past_logs['list_label'] == selected_log_label].iloc[0]
                
                with st.container(border=True):
                    st.info(f"📋 詳細: {selected_log_label}")
                    col_p_img, col_p_info = st.columns([1, 1])
                    with col_p_img:
                        p_img_url = str(selected_row.get('filename', '')).strip()
                        if p_img_url.startswith('http'):
                            st.image(p_img_url, use_container_width=True)
                        else:
                            st.info("📷 画像なし")
                    
                    with col_p_info:
                        st.write(f"👤 **釣り人:** {selected_row.get(ANGLER_COL, '---')}")
                        st.write(f"🎣 **ルアー:** {selected_row.get(LURE_COL, '---')}")
                        st.write(f"💬 **備考:** {selected_row.get('備考', '---')}")

                    # 過去ログ用タイドグラフ
                    st.write("---")
                    st.caption("🌊 当時のタイドグラフ")
                    display_tide_graph(
                        selected_row.get('lat', 33.5), 
                        selected_row.get('lon', 129.8), 
                        str(selected_row.get('date')), 
                        str(selected_row.get('time', '12:00'))
                    )

    else:
        st.info("履歴がまだありません。")

































































































































































































