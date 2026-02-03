# -*- coding: utf-8 -*-
import pandas as pd
import datetime
import requests

PHOTO_CSV = "photo_exif.csv"

# =========================
# 毎時潮位TXT読込
# =========================
def read_hourly_tide(year, tide_code):
    url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{year}/{tide_code}.txt"
    res = requests.get(url)
    res.encoding = "utf-8"

    data = {}

    for line in res.text.splitlines():
        if len(line) < 80:
            continue

        try:
            y = int(line[72:74]) + 2000
            m = int(line[74:76])
            d = int(line[76:78])
        except:
            continue

        for h in range(24):
            v = line[h*3 : h*3 + 3].strip()
            if not v:
                continue
            try:
                dt = datetime.datetime(y, m, d, h, 0)
                data[dt] = int(v)
            except:
                pass

    return data


# =========================
# 潮位フェーズ判定
# =========================
def tide_phase(photo_dt, tides):
    t0 = photo_dt.replace(minute=0, second=0)

    if t0 not in tides:
        return "不明", None

    h = tides[t0]

    # 前後6時間を探索
    times = sorted(tides.keys())
    window = [t for t in times if abs((t - t0).total_seconds()) <= 6*3600]

    if len(window) < 5:
        return "不明", None

    levels = [tides[t] for t in window]

    # 満潮・干潮
    max_lv = max(levels)
    min_lv = min(levels)

    if h == max_lv:
        return "満潮前", 0
    if h == min_lv:
        return "干潮後", 0

    # 上げ or 下げ
    idx = window.index(t0)
    before = tides.get(window[idx-1])
    after  = tides.get(window[idx+1])

    if before is None or after is None:
        return "不明", None

    if after > before:
        phase = "上げ"
        ratio = (h - min_lv) / (max_lv - min_lv)
    else:
        phase = "下げ"
        ratio = (max_lv - h) / (max_lv - min_lv)

    step = max(1, min(9, round(ratio * 10)))
    return f"{phase}{step}分", ratio


# =========================
# メイン処理
# =========================
df = pd.read_csv(PHOTO_CSV, encoding="utf-8-sig")
cache = {}

for i, row in df.iterrows():
    if pd.isna(row.get("datetime")) or pd.isna(row.get("tide_code")):
        df.at[i, "潮位フェーズ"] = "不明"
        continue

    photo_dt = pd.to_datetime(row["datetime"])
    tide_code = row["tide_code"]
    year = photo_dt.year

    key = (year, tide_code)
    if key not in cache:
        cache[key] = read_hourly_tide(year, tide_code)

    phase, ratio = tide_phase(photo_dt, cache[key])
    df.at[i, "潮位フェーズ"] = phase

df.to_csv(PHOTO_CSV, index=False, encoding="utf-8-sig")
print("✅ 潮位フェーズ（上げ◯分／下げ◯分）を追加しました")
