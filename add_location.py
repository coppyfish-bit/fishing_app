# -*- coding: utf-8 -*-
import pandas as pd

PHOTO_CSV = "photo_exif.csv"
STATION_CSV = "stations/weather_stations.csv"
OUT_CSV = "photo_exif.csv" # 次の工程に渡すために上書き、または名称統一

def distance(lat1, lon1, lat2, lon2):
    return ((lat1 - lat2)**2 + (lon1 - lon2)**2) ** 0.5

df = pd.read_csv(PHOTO_CSV)
stations = pd.read_csv(STATION_CSV)

# ---- 列の準備（エラー回避） ----
if "location_name" not in df.columns:
    df["location_name"] = pd.NA

# ---- 列名を吸収する ----
def find_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    raise ValueError(f"列が見つかりません: {candidates}")

station_lat_col = find_col(stations, ["lat", "latitude", "緯度"])
station_lon_col = find_col(stations, ["lon", "longitude", "経度"])
station_name_col = find_col(stations, ["station", "観測所名", "地点名"])

# ---- 処理 ----
for i, row in df.iterrows():
    if pd.isna(row["lat"]) or pd.isna(row["lon"]):
        continue
    
    # ここを修正：列が存在しないか、空の場合のみ計算する
    if pd.notna(row.get("location_name")):
        continue

    lat, lon = row["lat"], row["lon"]

    # 最寄りの地点を探す
    stations["dist"] = stations.apply(
        lambda s: distance(lat, lon, s[station_lat_col], s[station_lon_col]),
        axis=1
    )
    idx = stations["dist"].idxmin()
    df.at[i, "location_name"] = stations.loc[idx, station_name_col]

# 保存
df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
print(f"✅ 地点名付与完了: {OUT_CSV}")