# -*- coding: utf-8 -*-
import pandas as pd
import numpy as np
import os

PHOTO_CSV = "photo_exif.csv"
TIDE_CSV = "stations/tide_stations.csv"
OUT_CSV = "photo_exif.csv"

def distance(lat1, lon1, lat2, lon2):
    """
    ハブサイン公式による2点間の距離(km)計算
    """
    R = 6371.0
    
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    
    a = np.sin(dphi / 2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    return R * c

def find_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    raise ValueError(f"列が見つかりません: {candidates}")

def main():
    if not os.path.exists(PHOTO_CSV) or not os.path.exists(TIDE_CSV):
        print(f"⚠️ 必要なCSVが見つかりません。")
        return

    df = pd.read_csv(PHOTO_CSV)
    tides_master = pd.read_csv(TIDE_CSV)

    # ---- 列名吸収 ----
    tide_lat_col = find_col(tides_master, ["lat", "latitude", "緯度"])
    tide_lon_col = find_col(tides_master, ["lon", "longitude", "経度"])
    tide_station_col = find_col(tides_master, ["station", "観測所名", "地点名"])
    tide_code_col = find_col(tides_master, ["code", "潮汐コード"])

    tides_master = tides_master.dropna(subset=[tide_lat_col, tide_lon_col])

    # ---- 処理 ----
    df = df.drop(columns=["tide_station", "tide_code"], errors="ignore")
    df["tide_station"] = None
    df["tide_code"] = None

    print(f"🔍 全{len(df)}件の写真に対して最寄りの潮位観測所を判定中...")
    print("💡 本渡瀬戸が25km以内の場合は、口之津より優先して選択します。")

    for i, row in df.iterrows():
        lat, lon = row.get("lat"), row.get("lon")
        
        if pd.isna(lat) or pd.isna(lon) or lat == 0 or lon == 0:
            continue

        temp_tides = tides_master.copy()

        # 全観測所との距離を計算
        temp_tides["dist"] = temp_tides.apply(
            lambda s: distance(lat, lon, s[tide_lat_col], s[tide_lon_col]),
            axis=1
        )

        # 距離順にソート
        sorted_tides = temp_tides.sort_values("dist")

        # --- 【優先判定ロジック】 ---
        # 25km以内に「本渡瀬戸」があるかチェック
        # ※「本渡瀬戸」という名前はCSV内の表記と一致させてください
        hondo_check = sorted_tides[
            (sorted_tides[tide_station_col] == "本渡瀬戸") & 
            (sorted_tides["dist"] < 25.0)
        ]

        if not hondo_check.empty:
            # 25km圏内なら本渡瀬戸を優先採用
            nearest = hondo_check.iloc[0]
        else:
            # それ以外は純粋に一番近い地点を採用
            nearest = sorted_tides.iloc[0]
        # ----------------------------

        df.at[i, "tide_station"] = nearest[tide_station_col]
        df.at[i, "tide_code"] = nearest[tide_code_col]

    # 保存
    df.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")
    print(f"✅ 判定完了: {OUT_CSV} に保存しました。")

if __name__ == "__main__":
    main()