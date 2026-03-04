from PIL import Image
from PIL.ExifTags import TAGS

# --- 📸 EXIFから撮影日時を抜き出す魔術 ---
def get_exif_datetime(uploaded_file):
    try:
        img = Image.open(uploaded_file)
        exif_data = img._getexif()
        if not exif_data:
            return None
        
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            if tag == "DateTimeOriginal":  # 撮影日時のタグ
                # EXIF形式 "YYYY:MM:DD HH:MM:SS" を datetime に変換
                return datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
        return None
    except Exception:
        return None

# --- 🧪 タイムトラベル解析セクション ---
st.title("📸 写真から海況を復元せよ")
uploaded_file = st.file_uploader("EXIF付きの釣果写真を捧げよ...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # 1. 撮影日時を特定
    photo_dt = get_exif_datetime(uploaded_file)
    
    if photo_dt:
        st.success(f"🎯 撮影日時を特定：{photo_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 2. その日の潮汐データを召喚（load_and_calculate_tideを少し改造して使う）
        # ※本来はphoto_dtの日付でJSONを読み直す必要があるが、まずは「今日」のデータでテスト
        result, err = load_and_calculate_tide("HS") # 内部で photo_dt を使うように微調整が必要
        
        if result:
            # 撮影時の「分単位」潮位を再計算
            h = photo_dt.hour
            mi = photo_dt.minute
            h1_tide = result['hourly'][h]
            h2_tide = result['hourly'][(h + 1) % 24]
            photo_tide = h1_tide + ((h2_tide - h1_tide) * (mi / 60.0))
            
            # 撮影時のフェーズを算出
            phase_text, _ = calculate_tide_phase_10(photo_dt, result['events'])

            # --- 📊 復元結果の表示 ---
            st.markdown(f"""
                <div style="text-align: center; padding: 20px; background: rgba(255, 255, 255, 0.05); border: 2px dashed #00ff00; border-radius: 15px;">
                    <h3 style="color: #00ff00; margin: 0;">⌛️ 撮影時の海況復元</h3>
                    <h1 style="color: #ffffff; margin: 10px 0;">{photo_tide:.1f} cm</h1>
                    <h2 style="color: #00ff00; margin:0;">{phase_text}</h2>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.error("🚨 EXIFデータが見つからない。SNSで加工された写真は情報が消えている可能性があるぞ。")
