# -*- coding: utf-8 -*-
import os
import pandas as pd
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime

PHOTO_DIR = "input_photos"
OUT_CSV = "photo_exif.csv"

def get_exif(path):
    try:
        img = Image.open(path)
        exif = img._getexif()
        if not exif:
            return {}
        return {TAGS.get(k, k): v for k, v in exif.items()}
    except:
        return {}

def get_latlon(exif):
    gps = exif.get("GPSInfo")
    if not gps:
        return None, None

    gps = {GPSTAGS.get(k, k): v for k, v in gps.items()}

    def conv(v):
        d, m, s = v
        return float(d) + float(m) / 60 + float(s) / 3600

    try:
        lat = conv(gps["GPSLatitude"])
        if gps.get("GPSLatitudeRef") == "S":
            lat = -lat

        lon = conv(gps["GPSLongitude"])
        if gps.get("GPSLongitudeRef") == "W":
            lon = -lon

        return lat, lon
    except:
        return None, None

# 実際の処理を main 関数の中に閉じ込めます
def main():
    if not os.path.exists(PHOTO_DIR):
        print(f"⚠️ {PHOTO_DIR} フォルダが見つかりません。")
        return

    rows = []
    print(f"🔍 {PHOTO_DIR} 内の写真をスキャン中...")

    for fn in os.listdir(PHOTO_DIR):
        if not fn.lower().endswith((".jpg", ".jpeg")):
            continue

        path = os.path.join(PHOTO_DIR, fn)
        exif = get_exif(path)

        dt_raw = exif.get("DateTimeOriginal") or exif.get("DateTime")
        if dt_raw:
            try:
                dt = datetime.strptime(dt_raw, "%Y:%m:%d %H:%M:%S")
            except:
                continue
        else:
            continue

        lat, lon = get_latlon(exif)

        rows.append({
            "filename": fn,
            "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
            "date": dt.date().isoformat(),
            "time": dt.time().isoformat(),
            "lat": lat,
            "lon": lon,
        })

    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
        print(f"✅ {OUT_CSV} 作成完了 (行数: {len(df)})")
    else:
        print("⚠️ 有効なEXIF情報を持つ写真が見つかりませんでした。")

# このファイルが直接実行された時だけ main() を呼び出す設定
if __name__ == "__main__":
    main()