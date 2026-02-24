Skip to content
coppyfish-bit
fishing_app
Repository navigation
Code
Issues
Pull requests
Actions
Projects
Security
Insights
Settings
fishing_app
/
app.py
in
main

Edit

Preview
Indent mode

Spaces
Indent size

4
Line wrap mode

No wrap
Editing app.py file contents
520
521
522
523
524
525
526
527
528
529
530
531
532
533
534
535
536
537
538
539
540
541
542
543
544
545
546
547
548
549
550
551
552
553
554
555
556
557
558
559
560
561
562
563
564
565
566
567
568
569
570
571
572
573
574
575
576
577
578
579
580
581
582
583
584
585
586
587
588
589
590
591
592
593
594
595
596
597
        api_secret = st.secrets["cloudinary"]["api_secret"],
        
        # 線形補間
        t1 = hourly[dt.hour]
        t2 = hourly[dt.hour+1] if dt.hour < 23 else hourly[dt.hour]
        current_cm = int(round(t1 + (t2 - t1) * (dt.minute / 60.0)))

        # 満干潮抽出 (満潮: 81-108, 干潮: 109-136)
        event_times = []
        base_date_str = dt.strftime('%Y%m%d')
        # 満潮
        for i in range(4):
            start = 80 + (i * 7)
            t_str = day_data[start : start+4].strip()
            if t_str and t_str != "9999":
                ev_time = datetime.strptime(base_date_str + t_str.zfill(4), '%Y%m%d%H%M')
                event_times.append({"time": ev_time, "type": "満潮"})
        # 干潮
        for i in range(4):
            start = 108 + (i * 7)
            t_str = day_data[start : start+4].strip()
            if t_str and t_str != "9999":
                ev_time = datetime.strptime(base_date_str + t_str.zfill(4), '%Y%m%d%H%M')
                event_times.append({"time": ev_time, "type": "干潮"})

        return {"cm": current_cm, "events": event_times}
    except: return None

def get_weather_data_openmeteo(lat, lon, dt):
    try:
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": lat, "longitude": lon,
            "start_date": (dt - timedelta(days=2)).strftime('%Y-%m-%d'),
            "end_date": dt.strftime('%Y-%m-%d'),
            "hourly": "temperature_2m,windspeed_10m,winddirection_10m,precipitation",
            "timezone": "Asia/Tokyo"
        }
        res = requests.get(url, params=params, timeout=10).json()
        h = res['hourly']
        idx = (len(h['temperature_2m']) - 25) + dt.hour
        temp = h['temperature_2m'][idx]
        wind_speed = round(h['windspeed_10m'][idx] / 3.6, 1)
        wind_deg = h['winddirection_10m'][idx]
        precip_48h = round(sum(h['precipitation'][:idx+1][-48:]), 1)

        def get_wind_dir(deg):
            dirs = ["北", "北北東", "北東", "東北東", "東", "東南東", "南東", "南南東", "南", "南南西", "南西", "西南西", "西", "西北西", "北西", "北北西"]
            return dirs[int((deg + 11.25) / 22.5) % 16]
        return temp, wind_speed, get_wind_dir(wind_deg), precip_48h
    except: return None, None, "不明", 0.0

# --- 4. データ接続 ---
try:
    cloudinary.config(
        cloud_name = st.secrets["cloudinary"]["cloud_name"],
        api_key = st.secrets["cloudinary"]["api_key"],
        api_secret = st.secrets["cloudinary"]["api_secret"],
        secure = True
    )
except: st.error("Cloudinary secrets missing.")

conn = st.connection("gsheets", type=GSheetsConnection)
url = st.secrets["connections"]["gsheets"]["spreadsheet"]

@st.cache_data(ttl=600)
def get_all_data(_conn, _url):
    d_main = _conn.read(spreadsheet=_url, ttl="10m")
    d_master = _conn.read(spreadsheet=_url, worksheet="place_master", ttl="1h")
    return d_main, d_master

df, df_master = get_all_data(conn, url)

# --- 5. メイン UI ---
tabs = st.tabs(["記録", "編集", "ギャラリー", "分析（時合）", "月別統計", "スズキ戦略分析"])
tab1, tab2, tab3, tab4, tab5, tab6 = tabs

with tab1:
    st.title("🎣 KTDシステム")
Use Control + Shift + m to toggle the tab key moving focus. Alternatively, use esc then tab to move to the next interactive element on the page.
 
