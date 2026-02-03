# -*- coding: utf-8 -*-
import pandas as pd
import datetime
import requests

# =========================
# 設定
# =========================
PHOTO_CSV = "photo_exif.csv"

# =========================
# 潮汐TXT読込（満潮・干潮）
# =========================
def read_tide_events(year, tide_code):
    url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{year}/{tide_code}.txt"
    res = requests.get(url, timeout=20)
    res.encoding = "utf-8"

    events = {}

    for line in res.text.splitlines():
        if len(line) < 136:
            continue

        try:
            y = int(line[72:74]) + 2000
            m = int(line[74:76])
            d = int(line[76:78])
            date = datetime.date(y, m, d)
        except:
            continue

        day_events = []

        # ---------- 満潮 ----------
        for i in range(4):
            t = line[80 + i*7 : 84 + i*7].strip()
            if t == "9999" or len(t) != 4:
                continue
            try:
                hh = int(t[:2])
                mm = int(t[2:])
                if 0 <= hh <= 23 and 0 <= mm <= 59:
                    day_events.append(("満潮", datetime.datetime(y, m, d, hh, mm)))
            except:
                pass

        # ---------- 干潮 ----------
        for i in range(4):
            t = line[108 + i*7 : 112 + i*7].strip()
            if t == "9999" or len(t) != 4:
                continue
            try:
                hh = int(t[:2])
                mm = int(t[2:])
                if 0 <= hh <= 23 and 0 <= mm <= 59:
                    day_events.append(("干潮", datetime.datetime(y, m, d, hh, mm)))
            except:
                pass

        if day_events:
            events[date] = day_events

    return events


# =========================
# 前後イベント探索
# =========================
def find_nearest_events(events, photo_dt):
    date = photo_dt.date()

    candidates = []
    for d in [
        date - datetime.timedelta(days=1),
        date,
        date + datetime.timedelta(days=1),
    ]:
        if d in events:
            candidates.extend(events[d])

    prev_high = prev_low = None
    next_high = next_low = None

    for kind, dt in sorted(candidates, key=lambda x: x[1]):
        if dt <= photo_dt:
            if kind == "満潮":
                prev_high = dt
            else:
                prev_low = dt
        else:
            if kind == "満潮" and next_high is None:
                next_high = dt
            if kind == "干潮" and next_low is None:
                next_low = dt

    return prev_high, next_high, prev_low, next_low


# =========================
# メイン処理
# =========================
df = pd.read_csv(PHOTO_CSV, encoding="utf-8-sig")

# ★ 列を必ず作る（最重要）
for col in [
    "次の満潮まで_分",
    "次の干潮まで_分",
    "直前の満潮_時刻",
    "直前の干潮_時刻",
]:
    if col not in df.columns:
        df[col] = pd.NA

cache = {}

for i, row in df.iterrows():
    if pd.isna(row.get("datetime")) or pd.isna(row.get("tide_code")):
        continue

    photo_dt = pd.to_datetime(row["datetime"])
    tide_code = str(row["tide_code"]).strip()
    year = photo_dt.year

    key = (year, tide_code)
    if key not in cache:
        cache[key] = read_tide_events(year, tide_code)

    prev_h, next_h, prev_l, next_l = find_nearest_events(cache[key], photo_dt)

    if next_h:
        df.at[i, "次の満潮まで_分"] = int((next_h - photo_dt).total_seconds() / 60)
    if next_l:
        df.at[i, "次の干潮まで_分"] = int((next_l - photo_dt).total_seconds() / 60)
    if prev_h:
        df.at[i, "直前の満潮_時刻"] = prev_h.strftime("%Y-%m-%d %H:%M")
    if prev_l:
        df.at[i, "直前の干潮_時刻"] = prev_l.strftime("%Y-%m-%d %H:%M")

df.to_csv(PHOTO_CSV, index=False, encoding="utf-8-sig")
print("✅ 満潮・干潮イベントを追加しました（存在しない場合は空欄）")
