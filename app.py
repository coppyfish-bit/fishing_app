import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from PIL.ExifTags import TAGS
# ここを修正！「datetimeライブラリの中からdatetimeクラスを直接持ってくる」
from datetime import datetime 

# ページ設定
st.set_page_config(page_title="Fishing App", layout="wide")

st.title("📱 釣果登録")

# --- 1. まずデフォルトの日時を決める ---
# これで NameError: datetime.now() は解決します
default_datetime = datetime.now()

# 読み込み処理（以前のコードを流用）
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    df = conn.read(spreadsheet=url, ttl=0)
    m_df = pd.read_csv("group_place_master.csv")
    place_options = sorted(m_df["place_name"].unique().tolist())
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# --- 2. 写真アップローダー ---
uploaded_file = st.file_uploader("📸 写真を選択（日時を自動反映）", type=['jpg', 'jpeg', 'png'])

if uploaded_file:
    # EXIFから日時を抜き出す処理
    img = Image.open(uploaded_file)
    exif = img._getexif()
    if exif:
        for tag_id, value in exif.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == 'DateTimeOriginal':
                # EXIFの日時形式を変換
                default_datetime = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                st.success(f"✅ 写真から日時を読み取りました: {default_datetime.strftime('%Y-%m-%d %H:%M')}")

# --- 3. スマホ向け縦型フォーム ---
with st.form("input_form", clear_on_submit=True):
    date_in = st.date_input("📅 日付", value=default_datetime.date())
    time_in = st.time_input("⏰ 時刻", value=default_datetime.time())
    
    place_in = st.selectbox("📍 場所", options=place_options)
    fish_in = st.text_input("🐟 魚種", placeholder="シーバス")
    lure_in = st.text_input("🎣 ルアー", placeholder="セットアッパー 125DR")
    length_in = st.slider("📏 全長 (cm)", 0.0, 150.0, 40.0, 0.5)
    memo_in = st.text_area("📝 備考")
    
    submit_button = st.form_submit_button("🚀 スプレッドシートに保存", use_container_width=True)

# --- 4. 保存処理 ---
if submit_button:
    # (以前作成した pd.concat と conn.update の処理)
    # ...
    st.success("登録完了！")
    st.rerun()

