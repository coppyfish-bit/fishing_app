# -*- coding: utf-8 -*-
import pandas as pd
import os

def edit_log():
    CSV_FILE = "final_fishing_log.csv"
    PHOTO_DIR = "input_photos"

    if not os.path.exists(CSV_FILE):
        print("⚠️ CSVファイルが見つかりません。先に 釣りログ.bat を実行してください。")
        return

    df = pd.read_csv(CSV_FILE)

    # 必要な列がなければ作成（「場所」を追加）
    for col in ["場所", "魚種", "全長_cm", "ルアー", "備考"]:
        if col not in df.columns:
            df[col] = ""

    print("📝 釣果データの編集を開始します（Enterで維持、'q'で保存して終了）")

    for i, row in df.iterrows():
        filename = row['filename']
        print(f"\n" + "="*50)
        print(f"📷 対象写真: {filename}")
        print(f"📅 日時: {row['date']} {row['time']}")
        
        # 写真を表示
        photo_path = os.path.join(PHOTO_DIR, filename)
        if os.path.exists(photo_path):
            os.startfile(photo_path)
        
        # 入力関数
        def get_input(label, current_val):
            val = input(f"{label} [{current_val}]: ").strip()
            if val.lower() == 'q': return 'EXIT'
            return val if val != "" else current_val

        # 各項目の入力
        new_place = get_input("📍 場所", row["場所"])
        if new_place == 'EXIT': break
        
        new_fish = get_input("🐟 魚種", row["魚種"])
        if new_fish == 'EXIT': break
        
        new_size = get_input("📏 全長(cm)", row["全長_cm"])
        if new_size == 'EXIT': break
        
        new_lure = get_input("🎣 ルアー", row["ルアー"])
        if new_lure == 'EXIT': break
        
        new_memo = get_input("📝 備考", row["備考"])
        if new_memo == 'EXIT': break

        # 反映
        df.at[i, "場所"] = new_place
        df.at[i, "魚種"] = new_fish
        df.at[i, "全長_cm"] = new_size
        df.at[i, "ルアー"] = new_lure
        df.at[i, "備考"] = new_memo

    # 保存
    df.to_csv(CSV_FILE, index=False, encoding="utf-8-sig")
    print("\n✅ 変更を保存しました。")

if __name__ == "__main__":
    edit_log()