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

# --- 2. 入力フォームエリア ---
st.subheader("📝 新規釣果入力")
with st.form("input_form", clear_on_submit=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        date_in = st.date_input("日付")
        time_in = st.time_input("時刻")
    with col2:
        place_in = st.selectbox("場所", options=place_options)
        fish_in = st.text_input("魚種", placeholder="シーバス")
    with col3:
        length_in = st.number_input("全長 (cm)", min_value=0.0, step=0.1)
        submit_button = st.form_submit_button("スプレッドシートに登録")

# --- 3. 登録処理 ---
if submit_button:
    try:
        # 新しい行の作成（既存の115件の列構造に合わせます）
        new_row = pd.DataFrame([{
            "datetime": f"{date_in} {time_in}",
            "場所": place_in,
            "魚種": fish_in,
            "全長_cm": length_in,
            # 他の列（潮位など）は一旦空文字かNoneで埋める
            "備考": "Appから登録"
        }])

        # 既存データと結合
        updated_df = pd.concat([df, new_row], ignore_index=True)

        # スプレッドシートを更新
        conn.update(spreadsheet=url, data=updated_df)
        
        st.success(f"✅ {fish_in} を登録しました！")
        st.cache_data.clear()
        st.rerun()
    except Exception as e:
        st.error(f"登録失敗: {e}")
        st.info("💡 ヒント: スプレッドシートの共有設定が『編集者』になっているか確認してください。")

st.write("---")

# --- 4. データ表示エリア ---
if df is not None:
    st.subheader(f"📊 登録済みデータ ({len(df)}件)")
    # 直近のデータを上に表示
    st.dataframe(df.sort_index(ascending=False).head(10), use_container_width=True)
