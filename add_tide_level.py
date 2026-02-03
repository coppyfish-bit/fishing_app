
# -*- coding: utf-8 -*-
import pandas as pd
import datetime
import requests

# =========================
# 設定
# =========================
PHOTO_CSV = "photo_exif.csv"

# =========================
# 潮汐TXT読込
# =========================
def read_tide_txt(year, tide_code):
    url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{year}/{tide_code}.txt"
    res = requests.get(url)
    res.encoding = "utf-8"

    tide_data = {}

    for line in res.text.splitlines():
        if len(line) < 80:
            continue

        try:
            y = int(line[72:74]) + 2000
            m = int(line[74:76])
            d = int(line[76:78])
            date = datetime.date(y, m, d)
        except:
            continue

        hourly = {}
        for h in range(24):
            pos = h * 3
            v = line[pos:pos + 3].strip()
            if v:
                hourly[h] = int(v)

        tide_data[date] = hourly

    return tide_data


def get_nearest_tide_cm(tide_data, photo_dt):
    date = photo_dt.date()
    hour = photo_dt.hour
    minute = photo_dt.minute

    if date not in tide_data:
        return None

    if minute <= 30:
        return tide_data[date].get(hour)
    else:
        return tide_data[date].get(min(hour + 1, 23))


# =========================
# メイン処理
# =========================
df = pd.read_csv(PHOTO_CSV, encoding="utf-8-sig")

tide_cache = {}

for i, row in df.iterrows():
    if pd.isna(row.get("tide_code")) or pd.isna(row.get("datetime")):
        continue

    tide_code = row["tide_code"]
    photo_dt = pd.to_datetime(row["datetime"])

    year = photo_dt.year

    # 年×地点ごとに1回だけ取得
    key = (year, tide_code)
    if key not in tide_cache:
        tide_cache[key] = read_tide_txt(year, tide_code)

    cm = get_nearest_tide_cm(tide_cache[key], photo_dt)
    df.at[i, "潮位_cm"] = cm

df.to_csv(PHOTO_CSV, index=False, encoding="utf-8-sig")
print("✅ 潮位_cm を photo_exif.csv に追加しました")
