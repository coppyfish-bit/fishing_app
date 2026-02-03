# -*- coding: utf-8 -*-
import pandas as pd
import os
import requests
from datetime import datetime, timedelta

PHOTO_CSV = "photo_exif.csv"

def get_weather_at_time(station_code: int, photo_dt):
    # アメダスJSONは10分刻み
    target_dt = photo_dt.replace(minute=(photo_dt.minute // 10) * 10, second=0, microsecond=0)
    result = {"平均気温": None, "降水量": None, "風速": None, "風向": None}
    
    found_data = None
    # 1時間前から順に探す
    for i in range(6):
        check_dt = target_dt - timedelta(minutes=10 * i)
        timestamp = check_dt.strftime("%Y%m%d%H%M00")
        
        # --- URLを「全国統合データ」に変更 ---
        url = f"https://www.jma.go.jp/bosai/amedas/data/map/{timestamp}.json"
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                found_data = response.json()
                break
        except:
            continue

    if not found_data:
        return result

    # --- 修正：全国統合JSONから観測所を探す ---
    # 熊本(本渡)の場合、44032 ではなく、アメダス番号(86316)で格納されている場合が多いです
    # 両方の可能性をチェックします
    st_val = int(station_code)
    # 本渡(44032)と統計用(86316)を相互変換して試行
    search_keys = [str(st_val), str(st_val).zfill(5)]
    if st_val == 44032: search_keys.append("86316")
    if st_val == 86316: search_keys.append("44032")

    st_data = None
    for key in search_keys:
        if key in found_data:
            st_data = found_data[key]
            break

    if st_data:
        # 気温: [値, 品質コード] の形式なので [0] を取る
        if "temp" in st_data: result["平均気温"] = st_data["temp"][0]
        if "wind" in st_data: result["風速"] = st_data["wind"][0]
        if "windDirection" in st_data:
            dir_code = st_data["windDirection"][0]
            directions = ["静穏", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西", "北"]
            if 0 <= dir_code < len(directions):
                result["風向"] = directions[dir_code]
    else:
        # それでも見つからない場合、全キーの中から「熊本(86)」で始まるものを探してデバッグ
        kumamoto_keys = [k for k in found_data.keys() if k.startswith("86") or k.startswith("44")]
        print(f"  ⚠️ コード {st_val} 不一致。JSON内の近隣コード例: {kumamoto_keys[:5]}")

    return result

def main():
    if not os.path.exists(PHOTO_CSV): return
    df = pd.read_csv(PHOTO_CSV)
    
    print("☁️ 直近気象データの解析を開始します...")
    updated_count = 0

    for i, row in df.iterrows():
        # 未取得データのみ対象
        if pd.notna(row.get("気温")) and str(row.get("気温")) != "":
            continue

        try:
            dt_str = f"{row['date']} {row['time']}"
            photo_dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            
            # 10日以内のみ
            if (datetime.now() - photo_dt).days > 10:
                continue

            st_code = int(float(row["station_code"]))
            w = get_weather_at_time(st_code, photo_dt)
            
            if w["平均気温"] is not None:
                df.at[i, "気温"] = w["平均気温"]
                df.at[i, "風速"] = w["風速"]
                df.at[i, "風向"] = w["風向"]
                df.at[i, "天気"] = "取得成功(直近)"
                updated_count += 1
                print(f"  ✅ {row['filename']}: 気温 {w['平均気温']}度 を取得")
        except:
            continue

    df.to_csv(PHOTO_CSV, index=False, encoding="utf-8-sig")
    print(f"✅ 完了: {updated_count}件更新")

if __name__ == "__main__":
    main()