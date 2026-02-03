# -*- coding: utf-8 -*-
import pandas as pd
import os

PHOTO_CSV = "photo_exif.csv"
WEATHER_SOURCE = "data_weather_archive/weather_daily_long.csv"

def main():
    print("--- add_past_weather (アーカイブ参照) を開始 ---")
    if not os.path.exists(PHOTO_CSV):
        print("⚠️ photo_exif.csv が見つかりません。")
        return
    
    if not os.path.exists(WEATHER_SOURCE):
        print("⚠️ アーカイブファイルが見つからないため、過去データの反映をスキップします。")
        return

    df_p = pd.read_csv(PHOTO_CSV)
    df_w = pd.read_csv(WEATHER_SOURCE)

    # 日付形式の統一
    df_w["join_date"] = pd.to_datetime(df_w["date"]).dt.strftime('%Y-%m-%d')
    date_col = "datetime" if "datetime" in df_p.columns else "date"
    df_p["join_date"] = pd.to_datetime(df_p[date_col]).dt.strftime('%Y-%m-%d')

    # 地点名のクリーニング
    df_w = df_w.rename(columns={"station": "weather_station_name"})
    df_w["weather_station_name"] = df_w["weather_station_name"].astype(str).str.strip()
    df_p["weather_station_name"] = df_p["weather_station_name"].astype(str).str.strip()

    # 項目名の統一（アーカイブ側の名前を一時的に変えて結合）
    df_w = df_w.rename(columns={
        "平均気温": "平均気温_arc",
        "降水量の合計": "降水量_arc",
        "最多風向": "風向_arc",
        "平均風速": "風速_arc" 
    })

    # 必要な列だけを抽出して結合
    df_w_sub = df_w[["join_date", "weather_station_name", "平均気温_arc", "降水量_arc", "風向_arc", "風速_arc"]].drop_duplicates()
    
    df_out = df_p.merge(
        df_w_sub,
        on=["join_date", "weather_station_name"],
        how="left"
    )

    # 直近スクリプトで埋まらなかった場合のみ、アーカイブで埋める
    target_map = {
        "気温": "平均気温_arc",
        "降水量": "降水量_arc",
        "風向": "風向_arc",
        "風速": "風速_arc"
    }

    for col_final, col_arc in target_map.items():
        if col_final not in df_out.columns:
            df_out[col_final] = df_out[col_arc]
        else:
            df_out[col_final] = df_out[col_final].fillna(df_out[col_arc])

    # 作業用列の削除
    drop_cols = ["join_date", "平均気温_arc", "降水量_arc", "風向_arc", "風速_arc"]
    df_out.drop(columns=[c for c in drop_cols if c in df_out.columns], inplace=True)

    # 天気列が空の場合、気温があれば「アーカイブ」と入れる
    if "天気" in df_out.columns:
        mask = (df_out["天気"].isna() | (df_out["天気"] == "")) & df_out["気温"].notna()
        df_out.loc[mask, "天気"] = "アーカイブ"

    df_out.to_csv(PHOTO_CSV, index=False, encoding="utf-8-sig")
    print(f"✅ 過去アーカイブからの補完が完了しました。")

if __name__ == "__main__":
    main()