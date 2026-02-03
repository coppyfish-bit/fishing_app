# -*- coding: utf-8 -*-
import pandas as pd
from astral.moon import phase

PHOTO_CSV = "photo_exif.csv"

# =========================
# 潮名判定
# =========================
def tide_name_from_moon(age):
    if pd.isna(age):
        return pd.NA

    age = float(age)

    if age < 1.5 or age >= 28.5:
        return "大潮"
    elif age < 4.5:
        return "中潮"
    elif age < 7.5:
        return "小潮"
    elif age < 9.5:
        return "長潮"
    elif age < 12.5:
        return "若潮"
    elif age < 15.5:
        return "中潮"
    elif age < 17.5:
        return "大潮"
    elif age < 20.5:
        return "中潮"
    elif age < 23.5:
        return "小潮"
    elif age < 25.5:
        return "長潮"
    else:
        return "若潮"

# =========================
# メイン処理
# =========================
df = pd.read_csv(PHOTO_CSV, encoding="utf-8-sig")

# --- 列を必ず作る ---
if "月齢" not in df.columns:
    df["月齢"] = pd.NA

if "潮名" not in df.columns:
    df["潮名"] = pd.NA

for i, row in df.iterrows():
    if pd.isna(row.get("datetime")):
        continue

    dt = pd.to_datetime(row["datetime"])

    # --- 月齢計算 ---
    age = phase(dt)
    df.at[i, "月齢"] = round(age, 1)

    # --- 潮名 ---
    df.at[i, "潮名"] = tide_name_from_moon(age)

df.to_csv(PHOTO_CSV, index=False, encoding="utf-8-sig")
print("✅ 月齢・潮名 を追加しました")
