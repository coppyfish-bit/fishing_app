import streamlit as st
from PIL import Image, ExifTags
import pandas as pd

st.title("👿 デーモン佐藤のEXIF解析室")
st.write("古い写真の『正体』を暴いてやる。画像をアップロードせよ。")

uploaded_file = st.file_uploader("解析したい画像を選択", type=["jpg", "jpeg", "png", "heic"])

if uploaded_file:
    st.image(uploaded_file, caption="解析対象の画像", width=300)
    
    try:
        img = Image.open(uploaded_file)
        exif = img._getexif()
        
        if exif is None:
            st.error("❌ この画像にはEXIF情報が一切含まれていないぞ！")
            st.info("SNS経由や加工アプリを通すと、データが消されることが多い。別の元画像を探せ。")
        else:
            st.success("✅ EXIF情報の抽出に成功した。中身は以下の通りだ。")
            
            # 生データを整形して表示
            exif_data = []
            for tag_id, value in exif.items():
                tag_name = ExifTags.TAGS.get(tag_id, tag_id)
                exif_data.append({"ID": tag_id, "Tag Name": tag_name, "Value": str(value)})
            
            df_exif = pd.DataFrame(exif_data)
            st.table(df_exif) # 全データをテーブル表示
            
            # --- 特に重要な情報の抜き出しテスト ---
            st.subheader("📍 捜索対象の重要タグ")
            
            # 1. 日時 (DateTimeOriginal)
            dt_tag = next((item for item in exif_data if item["Tag Name"] == "DateTimeOriginal"), None)
            if dt_tag:
                st.write(f"📅 **撮影日時:** {dt_tag['Value']}")
            else:
                st.warning("⚠️ 撮影日時 (DateTimeOriginal) が見つからない。")

            # 2. GPS情報 (GPSInfo)
            gps_tag = next((item for item in exif_data if item["Tag Name"] == "GPSInfo"), None)
            if gps_tag:
                st.write("🌍 **GPSデータ:** 存在するぞ。")
                st.json(exif[34853]) # GPSInfoの生データを表示
            else:
                st.warning("⚠️ GPS情報が見つからない。")

    except Exception as e:
        st.error(f"💀 解析中にエラーが発生した: {e}")
