# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import os

PHOTO_CSV = "photo_exif.csv"
RECENT_STATIONS_CSV = r"C:\Users\coppy\OneDrive\デスクトップ\FishingPhotos\stations\weather_stations_recent.csv"

def get_distance(lat1, lon1, lat2, lon2):
    p = np.pi / 180
    a = 0.5 - np.cos((lat2 - lat1) * p)/2 + np.cos(lat1 * p) * np.cos(lat2 * p) * (1 - np.cos((lon2 - lon1) * p)) / 2
    return 12742 * np.arcsin(np.sqrt(a))

def main():
    if not os.path.exists(PHOTO_CSV): return
    df = pd.read_csv(PHOTO_CSV)

    # 1. 過去アーカイブ用（add_past_weather用）の5桁コード
    past_stations = [
        {"name": "本渡", "code": 84241, "lat": 32.4533, "lon": 130.1983},
        {"name": "牛深", "code": 84306, "lat": 32.1917, "lon": 130.0267},
        {"name": "三角", "code": 84211, "lat": 32.6100, "lon": 130.4633},
        {"name": "松島", "code": 84246, "lat": 32.5150, "lon": 130.4133}
    ]

    # 2. 直近JSON API用（add_recent_weather用）のCSVを読み込み
    if os.path.exists(RECENT_STATIONS_CSV):
        df_recent = pd.read_csv(RECENT_STATIONS_CSV)
    else:
        print(f"⚠️ {RECENT_STATIONS_CSV} が見つかりません。")
        return

    print("🔎 最寄りの気象観測所（過去用・直近用）を特定中...")

    # 過去用コードを特定する関数
    def find_past(lat, lon):
        if pd.isna(lat) or pd.isna(lon): return None, None
        best_dist = 999
        best_st = None
        for st in past_stations:
            d = get_distance(lat, lon, st["lat"], st["lon"])
            if d < best_dist:
                best_dist = d
                best_st = st
        return best_st["name"], best_st["code"]

    # 直近用コード（44xxxなど）を特定する関数
    def find_recent(lat, lon):
        if pd.isna(lat) or pd.isna(lon): return None
        best_dist = 999
        best_code = None
        for _, st in df_recent.iterrows():
            d = get_distance(lat, lon, st["緯度"], st["経度"])
            if d < best_dist:
                best_dist = d
                best_code = st["コード"]
        return best_code

    # 列を追加
    past_results = df.apply(lambda r: find_past(r["lat"], r["lon"]), axis=1)
    df["weather_station_name"] = [r[0] for r in past_results]
    df["station_code_past"] = [r[1] for r in past_results] # 過去用（84xxx）
    df["station_code"] = df.apply(lambda r: find_recent(r["lat"], r["lon"]), axis=1) # 直近用（44xxx）

    df.to_csv(PHOTO_CSV, index=False, encoding="utf-8-sig")
    print("✅ 過去用(84xxx)と直近用(station_code: 44xxx)のコードを両方付与しました。")

if __name__ == "__main__":
    main()