import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime 

# ページ設定
st.set_page_config(page_title="Fishing App", layout="wide")

st.title("📱 釣果登録")

# --- 1. 初期設定とデータ読み込み ---
default_datetime = datetime.now()

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    
    # 釣果データ読み込み
    df = conn.read(spreadsheet=url, ttl=0)
    
    # 場所マスター読み込み
    m_df = conn.read(spreadsheet=url, worksheet="place_master", ttl=0)
    place_options = sorted(m_df["place_name"].unique().tolist())
except Exception as e:
    st.error(f"データの読み込みに失敗しました: {e}")
    st.stop()

# --- 2. 釣り場追加機能（自動採番付き） ---
st.write("---")
with st.expander("📍 新規地点をマスターに追加する"):
    new_place = st.text_input("追加する釣り場名", placeholder="例：〇〇堤防")
    if st.button("マスターに登録"):
        if new_place:
            if new_place in m_df["place_name"].values:
                st.warning("その場所は既に登録されています。")
            else:
                # 自動採番ロジック
                new_id = m_df["group_id"].max() + 1 if not m_df.empty else 0
                new_place_row = pd.DataFrame([{"group_id": int(new_id), "place_name": new_place}])
                updated_m_df = pd.concat([m_df, new_place_row], ignore_index=True)
                
                conn.update(spreadsheet=url, worksheet="place_master", data=updated_m_df)
                st.success(f"✅ 「{new_place}」(ID:{new_id}) を登録しました！")
                st.cache_data.clear()
                st.rerun()

st.write("---")

# --- 3. 写真アップローダー（EXIF解析） ---
uploaded_file = st.file_uploader("📸 写真を選択（日時を自動反映）", type=['jpg', 'jpeg', 'png'])

if uploaded_file:
    img = Image.open(uploaded_file)
    exif = img._getexif()
    if exif:
        for tag_id, value in exif.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == 'DateTimeOriginal':
                default_datetime = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                st.success(f"✅ 写真から日時を読み取りました: {default_datetime.strftime('%Y-%m-%d %H:%M')}")

# --- 4. 釣果登録フォーム（ID紐付け） ---
with st.form("input_form", clear_on_submit=True):
    date_in = st.date_input("📅 日付", value=default_datetime.date())
    time_in = st.time_input("⏰ 時刻", value=default_datetime.time())
    
    place_in = st.selectbox("📍 場所", options=place_options)
    
    # 選ばれた場所からIDを自動特定（ここがポイント！）
    current_id = m_df.loc[m_df["place_name"] == place_in, "group_id"].values[0] if not m_df.empty else None
    
    fish_in = st.text_input("🐟 魚種", placeholder="スズキ")
    lure_in = st.text_input("🎣 ルアー", placeholder="カゲロウ125MD")
    length_in = st.slider("📏 全長 (cm)", 0.0, 150.0, 40.0, 1.0)
    memo_in = st.text_area("📝 備考")
    
    submit_button = st.form_submit_button("🚀 スプレッドシートに保存", use_container_width=True)

# --- 5. 保存処理 ---
if submit_button:
    try:
        new_data = pd.DataFrame([{
            "datetime": f"{date_in} {time_in}",
            "場所": place_in,
            "group_id": int(current_id), # 特定したIDを保存
            "魚種": fish_in,
            "ルアー": lure_in,
            "全長_cm": length_in,
            "備考": memo_in
        }])
        
        updated_df = pd.concat([df, new_data], ignore_index=True)
        conn.update(spreadsheet=url, data=updated_df)
        
        st.success(f"✅ {place_in} での釣果を登録しました！")
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"登録失敗: {e}")
