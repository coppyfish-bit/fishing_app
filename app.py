import pandas as pd
import requests
import traceback

def debug_tide_fetch(lat, lon, datetime_str):
    """
    スプレッドシートの値を元に、潮位取得ができるか検証するデバッグ関数
    """
    try:
        # 1. 日時のパース
        dt = pd.to_datetime(datetime_str)
        year = dt.year
        
        # 2. 観測所の特定（簡易版ロジック）
        # 本渡瀬戸(HS)をデフォルトに設定
        station_code = "HS" 
        
        # 3. URLの生成
        user = "coppyfish-bit"
        repo = "fishing_app"
        url = f"https://raw.githubusercontent.com/{user}/{repo}/main/data/{year}/{station_code}.json"
        
        print(f"🔍 検証URL: {url}")
        
        # 4. 通信（ここが重要：res自体を取得する）
        res = requests.get(url)
        
        if res.status_code != 200:
            return f"❌ HTTPエラー: {res.status_code} (URLが間違っているかファイルがありません)"

        # 5. 解析関数の実行（resオブジェクトを渡す）
        # 前回の「究極修正版」の get_tide_details を呼び出す想定
        result = get_tide_details(res, dt)
        
        return {
            "入力日時": datetime_str,
            "取得潮位": f"{result.get('cm')} cm",
            "フェーズ": result.get('phase'),
            "ステータス": "✅ 成功"
        }

    except Exception as e:
        return f"❌ エラー発生: {str(e)}\n{traceback.format_exc()}"

# --- テスト実行 (スプレッドシートのデータ例) ---
# 例: 2025/06/17 17:16:04, 32.3978, 130.3296
test_result = debug_tide_fetch("32.39782778", "130.3296222", "2025/06/17 17:16:04")
print(test_result)
