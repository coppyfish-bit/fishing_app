import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# ページ設定
st.set_page_config(page_title="Fishing App", layout="wide")

# --- メイン処理 ---
st.title("📱 スマホ爆速登録")

# 1. まず「デフォルトの日時」を現在の時刻で決めておく（★重要）
default_datetime = datetime.now()

# 2. 写真アップローダー
uploaded_file = st.file_uploader("📸 写真を選択（日時を自動反映）", type=['jpg', 'jpeg', 'png'])

# 3. 写真がアップロードされたら、default_datetime を上書きする
if uploaded_file:
    img = Image.open(uploaded_file)
    exif_dt = get_exif_datetime(img)
    if exif_dt:
        default_datetime = exif_dt
        st.success(f"✅ 写真から日時を読み取りました: {default_datetime.strftime('%Y-%m-%d %H:%M')}")
    else:
        st.warning("⚠️ 写真に日時情報（EXIF）が含まれていませんでした。現在の時刻を使用します。")

# --- 4. スマホ向け縦型フォーム ---
# ここで使う default_datetime は、写真があってもなくても必ず存在するのでエラーになりません
with st.form("input_form", clear_on_submit=True):
    date_in = st.date_input("📅 日付", value=default_datetime.date())
    time_in = st.time_input("⏰ 時刻", value=default_datetime.time())
    
    # ... (以降の場所、魚種、ルアー、全長、備考の入力欄)
    
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


