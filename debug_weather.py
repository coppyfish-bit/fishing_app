# -*- coding: utf-8 -*-
import pandas as pd
import os

# --- 設定 ---
PHOTO_CSV = "photo_exif.csv"
WEATHER_CSV = "data_weather_archive/weather_daily_long.csv"
OUT_CSV = "check_weather.csv" # 動作確認用の別名ファイル

def main():
    if not os.path.exists(PHOTO_CSV) or not os.path.exists(WEATHER_CSV):
        print("⚠️ 必要なCSVファイルが足りません。")
        return

    # 1. データの読み込み
    df_photo = pd.read_csv(PHOTO_CSV)
    df_weather = pd.read_csv(WEATHER_CSV)

    # 2. 気象データ側の前処理（提示されたデータ形式に合わせる）
    # station列をweather_station_nameに変換し、空白を除去
    df_weather = df_weather.rename(columns={"station": "weather_station_name"})
    df_weather["weather_station_name"] = df_weather["weather_station_name"].astype(str).str.strip()
    
    # 日付(2023/1/1など)を統一形式(2023-01-01)に変換
    df_weather["join_date"] = pd.to_datetime(df_weather["date"]).dt.strftime('%Y-%m-%d')

    # 3. 写真データ側の前処理
    # 観測所名の空白を除去
    if "weather_station_name" in df_photo.columns:
        df_photo["weather_station_name"] = df_photo["weather_station_name"].astype(str).str.strip()
    
    # 日付を統一形式に変換
    if "datetime" in df_photo.columns:
        df_photo["join_date"] = pd.to_datetime(df_photo["datetime"]).dt.strftime('%Y-%m-%d')
    else:
        df_photo["join_date"] = pd.to_datetime(df_photo["date"]).dt.strftime('%Y-%m-%d')

    # 4. 列名の名寄せ（レポート作成用）
    df_weather = df_weather.rename(columns={
        "平均気温": "平均気温",
        "降水量の合計": "降水量",
        "最多風向": "風向",
        "平均風速": "最大風速"
    })

    # 5. 結合を実行
    # 重複を避けるため必要な列だけを抽出
    weather_cols = ["join_date", "weather_station_name", "平均気温", "降水量", "風向", "最大風速"]
    df_weather_unique = df_weather[weather_cols].drop_duplicates()

    df_out = df_photo.merge(
        df_weather_unique,
        on=["join_date", "weather_station_name"],
        how="left"
    )

    # 6. 作業用列の削除と保存
    df_out = df_out.drop(columns=["join_date"])
    df_out.to_csv(OUT_CSV, index=False, encoding="utf-8-sig")

    # --- 診断メッセージ ---
    print(f"📊 診断レポート 📊")
    print(f"写真データの地点名例: '{df_photo['weather_station_name'].iloc[0]}'")
    print(f"気象データの地点名例: '{df_weather['weather_station_name'].iloc[0]}'")
    
    match_count = df_out["平均気温"].notna().sum()
    print(f"一致成功数: {match_count} / {len(df_out)} 件")
    
    if match_count > 0:
        print(f"✨ 成功！ '{OUT_CSV}' を確認してください。")
    else:
        print(f"❌ 1件も一致しませんでした。地点名が完全に一致しているか確認してください。")

if __name__ == "__main__":
    main()