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

# --- 1. マスターデータの読み込み (CSVからスプレッドシートに変更) ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    
    # 釣果データ
    df = conn.read(spreadsheet=url, ttl=0)
    
    # 【変更】場所マスターシートを読み込む
    m_df = conn.read(spreadsheet=url, worksheet="place_master", ttl=0)
    place_options = sorted(m_df["place_name"].unique().tolist())
except Exception as e:
    st.error(f"データの読み込みに失敗しました: {e}")
    st.stop()

# --- 2. 釣り場追加機能 ---
st.write("---")
st.subheader("📍 釣り場マスターの管理")

with st.expander("新しい釣り場を追加する"):
    new_place = st.text_input("追加する釣り場名", placeholder="例：〇〇堤防")
    
    if st.button("マスターに登録"):
        if new_place:
            if new_place in m_df["place_name"].values:
                st.warning("その場所は既に登録されています。")
            else:
                try:
                    # 新しい行を作成
                    new_row = pd.DataFrame([{"place_name": new_place}])
                    # 既存のマスターと結合
                    updated_m_df = pd.concat([m_df, new_row], ignore_index=True)
                    
                    # 【重要】スプレッドシートの "place_master" シートを更新
                    conn.update(spreadsheet=url, worksheet="place_master", data=updated_m_df)
                    
                    st.success(f"✅ 「{new_place}」を登録しました！")
                    st.cache_data.clear() # キャッシュをクリアして選択肢を更新
                    st.rerun()
                except Exception as e:
                    st.error(f"登録エラー: {e}")

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


