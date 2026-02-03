# -*- coding: utf-8 -*-
import subprocess
import os
import pandas as pd
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def run_script(name):
    if os.path.exists(name):
        print(f"\n--- {name} を実行中 ---")
        result = subprocess.run(["python", name])
        if result.returncode != 0:
            print(f"❌ {name} の実行中にエラーが発生しました。")
    else:
        print(f"⚠️ {name} が見つかりません")

def main():
    EXIF_CSV = "photo_exif.csv"
    FINAL_CSV = "final_fishing_log.csv"

    print("🚀 釣りログ・データ解析パイプラインを開始します...")

    scripts = [
        "photo_exif_check.py",
        "add_weather_station.py",
        "add_recent_weather.py",
        "add_past_weather.py",
        "add_tide.py",
        "add_tide_level.py",
        "add_tide_name.py",
        "add_tide_events.py",
        "add_tide_phase.py"
    ]

    for s in scripts:
        run_script(s)

    print(f"\n--- データの保護・最新気象データの同期処理 ---")
    if os.path.exists(EXIF_CSV):
        df_exif = pd.read_csv(EXIF_CSV)
        
        if os.path.exists(FINAL_CSV):
            df_final = pd.read_csv(FINAL_CSV)
            
            # 1. 未登録の新しい写真を追加
            new_files = df_exif[~df_exif['filename'].isin(df_final['filename'])].copy()
            manual_cols = ["場所", "魚種", "全長_cm", "ルアー", "備考"]
            
            if not new_files.empty:
                for col in manual_cols:
                    new_files[col] = ""
                df_final = pd.concat([df_final, new_files], ignore_index=True)
                print(f"✨ 新規追加: {len(new_files)} 件")

            # 2. 既存データの「空欄の気象情報」を同期
            sync_cols = ["天気", "気温", "風速", "風向", "lat", "lon", "station_code"]
            
            # --- 【修正ポイント】final側に列がない場合は空で作成しておく ---
            for col in sync_cols:
                if col not in df_final.columns:
                    df_final[col] = None

            # 同期処理
            df_final = df_final.set_index('filename')
            df_exif_sub = df_exif.set_index('filename')
            
            for col in sync_cols:
                if col in df_exif_sub.columns:
                    # 空の部分(NaN)だけをexif側のデータで埋める
                    df_final[col] = df_final[col].fillna(df_exif_sub[col])
            
            df_final = df_final.reset_index()
            df_final.to_csv(FINAL_CSV, index=False, encoding="utf-8-sig")
            print(f"✅ 気象データの同期が完了しました。")
            
        else:
            df_exif.to_csv(FINAL_CSV, index=False, encoding="utf-8-sig")
            print(f"✨ 初回データ {FINAL_CSV} を作成しました。")
    else:
        print(f"❌ {EXIF_CSV} が見つかりません。")

if __name__ == "__main__":
    main()