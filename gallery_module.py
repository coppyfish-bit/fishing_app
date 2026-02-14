# --- タブ3: ギャラリー ---
with tab3:
    st.subheader("🖼️ 精密データオーバーレイ")
    
    # データを最新順にソート
    df_gallery = df.copy()
    df_gallery['datetime'] = pd.to_datetime(df_gallery['datetime'])
    df_gallery = df_gallery.sort_values("datetime", ascending=False)

    cols = st.columns(3)
    
    for i, (idx, row) in enumerate(df_gallery.iterrows()):
        img_url = row["filename"]  # CloudinaryのURL
        
        if img_url:
            with cols[i % 3]:
                try:
                    # 潮汐ディテールの計算（エラー回避用に関数化せずその場で処理）
                    dt = row['datetime']
                    prev_h = pd.to_datetime(row['直前の満潮_時刻']) if pd.notna(row['直前の満潮_時刻']) else None
                    
                    if prev_h:
                        diff_mins = int((dt - prev_h).total_seconds() / 60)
                        # 簡易的な上げ下げ判定（より正確なフェーズがあればそちらを優先）
                        tide_detail = row.get('潮位フェーズ', f"{diff_mins}分経過")
                    else:
                        tide_detail = row.get('潮位フェーズ', "-")

                    # HTMLオーバーレイ表示
                    # CloudinaryのURLを直接img srcに指定
                    overlay_html = f"""
                    <div style="position: relative; width: 100%; margin-bottom: 20px; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.5);">
                        <img src="{img_url}" style="width: 100%; aspect-ratio: 1/1; object-fit: cover; display: block;">
                        <div style="position: absolute; bottom: 0; width: 100%; padding: 8px; background: rgba(0,0,0,0.6); color: white; font-size: 0.7rem; backdrop-filter: blur(2px);">
                            <b style="color: #00ffd0; font-size: 0.8rem;">{row['魚種']} {row['全長_cm']}cm</b><br>
                            📍 {row['場所']}<br>
                            🕒 {tide_detail} / 🌡️ {row.get('気温','-')}℃
                        </div>
                    </div>"""
                    st.markdown(overlay_html, unsafe_allow_html=True)
                except Exception as e:
                    # エラー時は通常の画像表示を試みる
                    st.image(img_url, caption=f"Error: {row['魚種']}")