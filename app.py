import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Data Check", layout="wide")
st.title("📊 データ接続テスト")

try:
    # 1. 接続の作成
    conn = st.connection("gsheets", type=GSheetsConnection)
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    
    # 2. データの読み込み
    df = conn.read(spreadsheet=url, ttl=0)
    
    if df is not None:
        st.success(f"✅ 成功！ {len(df)}件のデータを取得しました。")
        st.write("### 最新の5件を表示します")
        st.dataframe(df.tail(5)) # 最新のデータを確認
        
        # 3. 列名が正しいかチェック
        st.write("### 認識されている列名")
        st.code(df.columns.tolist())
    else:
        st.warning("接続はできましたが、データが空っぽのようです。")

except Exception as e:
    st.error("❌ エラーが発生しました")
    st.exception(e)
