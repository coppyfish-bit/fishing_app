# -*- coding: utf-8 -*-
import pandas as pd
import os

def generate_html():
    CSV_FILE = "final_fishing_log.csv"
    OUTPUT_HTML = "fishing_report.html"
    PHOTO_DIR = "input_photos" 

    if not os.path.exists(CSV_FILE):
        print(f"⚠️ {CSV_FILE} が見つかりません。先に 釣りログ.bat を実行してください。")
        return
        
    # CSV読み込み（未入力はハイフンにする）
    df = pd.read_csv(CSV_FILE).fillna("-")

    html_content = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>釣果レポート - Fishing Analysis</title>
        <style>
            body { font-family: 'Helvetica Neue', Arial, sans-serif; background: #f0f4f8; color: #333; margin: 0; padding: 20px; }
            h1 { text-align: center; color: #2c3e50; margin-bottom: 30px; }
            .container { display: flex; flex-wrap: wrap; gap: 25px; justify-content: center; }
            .card { background: white; border-radius: 15px; width: 350px; box-shadow: 0 10px 20px rgba(0,0,0,0.05); overflow: hidden; }
            .fish-img { width: 100%; height: 230px; object-fit: cover; }
            .info { padding: 20px; }
            
            .header-info { border-bottom: 2px solid #3498db; margin-bottom: 15px; padding-bottom: 10px; }
            .place-name { font-size: 1.3em; font-weight: bold; color: #1a73e8; }
            .fish-name { font-size: 1.1em; font-weight: bold; color: #2c3e50; margin-top: 5px; }
            .date-time { font-size: 0.85em; color: #7f8c8d; }

            .section-label { font-size: 0.8em; font-weight: bold; color: #555; margin-top: 15px; border-left: 4px solid #3498db; padding-left: 8px; margin-bottom: 8px; }
            .data-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.85em; }
            .data-box { padding: 12px; border-radius: 10px; }
            .tide-box { background: #e3f2fd; color: #01579b; }
            .weather-box { background: #fffde7; color: #f57f17; }
            .memo-box { background: #f5f5f5; color: #424242; line-height: 1.5; }
            
            .map-button { display: block; text-align: center; background: #3498db; color: white; text-decoration: none; padding: 12px; border-radius: 8px; margin-top: 15px; font-weight: bold; }
            .map-button:hover { background: #2980b9; }
        </style>
    </head>
    <body>
        <h1>🎣 マイ釣果レポート</h1>
        <div class="container">
    """

    for _, row in df.iterrows():
        # 画像の設定
        filename = str(row.get('filename', ''))
        img_url = os.path.join(PHOTO_DIR, filename).replace("\\", "/")
        
        # 表示項目の整理
        place = row.get('場所') if row.get('場所') != "-" else "釣果記録"
        fish = f"{row.get('魚種')} {row.get('全長_cm')}cm" if row.get('魚種') != "-" else "魚種未入力"
        
        # 緯度経度からマップURL生成
        lat, lon = row.get('lat'), row.get('lon')
        map_link = f'<a class="map-button" href="http://www.google.com/maps?q={lat},{lon}" target="_blank">📍 釣り場を確認</a>' if lat != "-" else ""

        html_content += f"""
            <div class="card">
                <img class="fish-img" src="{img_url}" onerror="this.src='https://via.placeholder.com/350x230?text=No+Photo'">
                <div class="info">
                    <div class="header-info">
                        <div class="date-time">📅 {row.get('date')} {row.get('time')}</div>
                        <div class="place-name">{place}</div>
                        <div class="fish-name">🐟 {fish}</div>
                    </div>
                    
                    <div class="section-label">潮汐状況</div>
                    <div class="data-box tide-box">
                        <div class="data-grid">
                            <span>🌊 潮名: <strong>{row.get('潮名')}</strong></span>
                            <span>📊 状況: {row.get('潮位フェーズ')}</span>
                            <span>🌙 月齢: {row.get('月齢')}</span>
                            <span>📏 潮位: {row.get('潮位_cm')}cm</span>
                        </div>
                        <div style="font-size:0.75em; margin-top:5px; opacity:0.8;">
                            満干: {row.get('直前の満潮_時刻', '-')}(満) / {row.get('直前の干潮_時刻', '-')}(干)
                        </div>
                    </div>

                    <div class="section-label">気象・タックル</div>
                    <div class="data-box weather-box">
                        <div class="data-grid">
                            <span>🌡️ 気温: {row.get('平均気温')}℃</span>
                            <span>💨 風速: {row.get('風速')}m/s</span>
                            <span>🚩 風向: {row.get('風向')}</span>
                            <span>🎣 ルアー: {row.get('ルアー')}</span>
                        </div>
                    </div>

                    <div class="section-label">備考</div>
                    <div class="data-box memo-box" style="font-size:0.85em;">
                        {row.get('備考')}
                    </div>

                    {map_link}
                </div>
            </div>
        """

    html_content += """
        </div>
        <footer style="text-align:center; margin-top:50px; color:#95a5a6; font-size:0.8em; padding-bottom:30px;">
            Fishing Log Analysis System
        </footer>
    </body>
    </html>
    """

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"✨ レポートを生成しました！場所名「{place}」などが反映されています。")

if __name__ == "__main__":
    generate_html()