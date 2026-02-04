import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 初期設定
st.set_page_config(page_title="Fishing App", layout="wide")

# 2. データ読み込み
conn = st.connection("gsheets", type=GSheetsConnection)
url = st.secrets["connections"]["gsheets"]["spreadsheet"]
df = conn.read(spreadsheet=url, ttl=0)
m_df = pd.read_csv("group_place_master.csv")

if df is not None:
    # --- データ整形（これがないとグラフが動きません） ---
    df["datetime"] = pd.to_datetime(df["datetime"])
    df["全長_cm"] = pd.to_numeric(df["全長_cm"], errors='coerce')
    
    # --- タブの作成 ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📝 登録・一覧", "📈 統計分析", "🌊 潮汐・時合", "🖼️ ギャラリー", "🎯 PREDICT"
    ])

    with tab1:
        st.subheader("現在の登録データ")
        st.dataframe(df.sort_values("datetime", ascending=False))
        # ここに以前の「入力フォーム」のコードを戻します

    with tab2:
        st.subheader("釣果統計")
        # 例: 魚種別の集計
        if "魚種" in df.columns:
            fish_counts = df["魚種"].value_counts()
            st.bar_chart(fish_counts)

    with tab3:
        st.subheader("タイドグラフ分析")
        st.write("潮位フェーズの分布")
        st.bar_chart(df["潮位フェーズ"].value_counts())

# --- 最後にパスワード機能を戻したい場合は、ここに check_password() を追加 ---
