import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# ページ設定
st.set_page_config(page_title="Fishing App", layout="wide")

st.title("🎣 釣果登録システム")

# 1. 接続とデータの読み込み
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    df = conn.read(spreadsheet=url, ttl=0)
    # 地点マスターも読み込み（以前のCSVがある前提）
    m_df = pd.read_csv("group_place_master.csv")
    place_options = sorted(m_df["place_name"].unique().tolist())
except Exception as e:
    st.error(f"接続エラー: {e}")
    st.stop()

# --- 2. スマホ向け縦型フォーム ---
with st.form("input_form", clear_on_submit=True):
    # 写真から読み取った値を初期値にセット
    date_in = st.date_input("📅 日付", value=default_datetime.date())
    time_in = st.time_input("⏰ 時刻", value=default_datetime.time())
    
    place_in = st.selectbox("📍 場所", options=place_options)
    fish_in = st.text_input("🐟 魚種", placeholder="シーバス")
    
    # 【追加】ルアー入力欄
    lure_in = st.text_input("🎣 ルアー", placeholder="セットアッパー 125DR")
    
    # スマホで打ちやすいスライダー
    length_in = st.slider("📏 全長 (cm)", 0.0, 150.0, 40.0, 0.5)

    # 備考欄
    memo_in = st.text_area("📝 備考", placeholder="ヒットルアー、アクション、周囲の状況など")
    
    st.write("---")
    submit_button = st.form_submit_button("🚀 スプレッドシートに保存", use_container_width=True)

# --- 3. 登録処理 ---
if submit_button:
    try:
        # 新しい行の作成
        new_row = pd.DataFrame([{
            "datetime": f"{date_in} {time_in}",
            "場所": place_in,
            "魚種": fish_in,
            "ルアー": lure_in,  # スプレッドシートの「ルアー」列に紐付け
            "全長_cm": length_in,
            "備考": memo_in,
            # その他の自動補完予定項目
            "気温": "", "風速": "", "潮名": ""
        }])

        # 既存データと結合
        updated_df = pd.concat([df, new_row], ignore_index=True)

        # スプレッドシートを更新
        conn.update(spreadsheet=url, data=updated_df)
        
        st.success(f"✅ {fish_in} (ルアー: {lure_in}) を登録しました！")
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"登録失敗: {e}")

# --- 4. データ表示エリア ---
if df is not None:
    st.subheader(f"📊 登録済みデータ ({len(df)}件)")
    # 直近のデータを上に表示
    st.dataframe(df.sort_index(ascending=False).head(10), use_container_width=True)

