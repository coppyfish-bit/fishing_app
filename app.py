import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# ページ設定
st.set_page_config(page_title="Fishing App Test", layout="wide")

st.title("🎣 接続テスト")

# 1. 接続の確立
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    
    # 2. 読み込み
    df = conn.read(spreadsheet=url, ttl=0)
    
    if df is not None:
        st.success(f"✅ 読み込み成功！ データ数: {len(df)} 件")
        st.write("### データのプレビュー")
        st.dataframe(df.head()) # 最初の5行を表示
        
        st.write("### 列名の一覧")
        st.write(df.columns.tolist())
    else:
        st.error("❌ データが空（None）です")

except Exception as e:
    st.error(f"❌ エラーが発生しました: {e}")
    st.exception(e)

st.info("これが表示されたら、接続は生きています！")
