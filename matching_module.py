# --- フェーズ判定部分のみ修正 ---
if prev_e and next_e:
    duration = (next_e['time'] - prev_e['time']).total_seconds()
    elapsed = (now - prev_e['time']).total_seconds()
    ratio = elapsed / duration
    
    # 10段階計算
    progress = max(1, min(9, int(ratio * 10)))
    direction = "下げ" if prev_e['type'] == "満潮" else "上げ"
    
    # 潮止まりの判定を5%に短縮（より実戦的に）
    if ratio < 0.05: 
        phase_label = f"{prev_e['type']}（止まり）"
    elif ratio > 0.95: 
        phase_label = f"{next_e['type']}（止まり）"
    else:
        # 下げ9分・上げ9分までしっかり表示
        phase_label = f"{direction}{progress}分"

    with col2:
        st.metric("現在のフェーズ", phase_label)
        # 次のイベントが「止まり」で表示されているものと同じなら、その次のイベントを表示
        display_next = next_e
        if ratio > 0.95:
            # 次の次のイベントを探す
            idx = events.index(next_e)
            if idx + 1 < len(events):
                display_next = events[idx + 1]
        
        st.write(f"次は **{display_next['type']}** ({display_next['time'].strftime('%m/%d %H:%M')})")
