# -*- coding: utf-8 -*-
import datetime
import requests

# =========================
# 潮汐TXTを読み込む
# =========================
def read_tide_txt(year, tide_code):
    """
    気象庁 潮汐TXTを読み込む
    return:
      {
        date: {hour: tide_cm}
      }
    """
    url = f"https://www.data.jma.go.jp/kaiyou/data/db/tide/suisan/txt/{year}/{tide_code}.txt"
    res = requests.get(url)
    res.encoding = "utf-8"

    tide_data = {}

    for line in res.text.splitlines():
        if len(line) < 80:
            continue

        # 年月日（73～78）
        try:
            y = int(line[72:74]) + 2000
            m = int(line[74:76])
            d = int(line[76:78])
            date = datetime.date(y, m, d)
        except:
            continue

        # 毎時潮位（1～72：3桁×24）
        hourly = {}
        for h in range(24):
            pos = h * 3
            val = line[pos:pos + 3].strip()
            if val:
                hourly[h] = int(val)

        tide_data[date] = hourly

    return tide_data


# =========================
# 写真時刻 → 最寄り潮位
# =========================
def get_nearest_tide_cm(tide_data, photo_dt):
    """
    photo_dt: datetime.datetime
    return: 潮位(cm) or None
    """
    date = photo_dt.date()
    hour = photo_dt.hour
    minute = photo_dt.minute

    if date not in tide_data:
        return None

    h1 = hour
    h2 = min(hour + 1, 23)

    # どちらの正時に近いか
    if minute <= 30:
        return tide_data[date].get(h1)
    else:
        return tide_data[date].get(h2)


# =========================
# テスト実行
# =========================
if __name__ == "__main__":
    tide = read_tide_txt(2026, "HS")

    photo_dt = datetime.datetime(2026, 1, 1, 22, 46)
    cm = get_nearest_tide_cm(tide, photo_dt)

    print("写真時刻:", photo_dt)
    print("最寄り潮位(cm):", cm)
