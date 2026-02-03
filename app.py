# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import os
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import requests
from io import BytesIO
import base64
import re

def get_image_for_display(file_val):
    if pd.isna(file_val) or str(file_val).strip() == "":
        return None
    val_str = str(file_val).strip()

    if "drive.google.com" in val_str:
        match = re.search(r'[-\w]{25,}', val_str)
        if match:
            file_id = match.group(0)
            # 【ここを修正】uc?id= ではなく thumbnail リンクを使用します
            # sz=w1000 とすることで、高画質な画像を取得できます
            return f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"
    
    local_path = os.path.join(PHOTO_DIR, val_str)
    if os.path.exists(local_path):
        return local_path
    return None
    
    # URLでない場合はローカルフォルダを探す
    local_path = os.path.join(PHOTO_DIR, val_str)
    if os.path.exists(local_path):
        return local_path
    
    return None
    
# --- 1. 基本設定 ---
st.set_page_config(page_title="天草スズキ・ログ管理", layout="wide")
LOG_CSV = "final_fishing_log.csv"
MASTER_CSV = "group_place_master.csv"
PHOTO_DIR = "input_photos"

# --- 2. スプレッドシート連携の設定 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/12hcg7hagi0oLq3nS-K27OqIjBYmzMYXh_FcoS8gFFyE/"

# 【重要！】この一行が抜けているか、関数の「中」に入っていませんか？
# 関数の「外」に置いておく必要があります。
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=600)
def load_data_from_gs():
    # ここで conn を使います
    df = conn.read(spreadsheet=SHEET_URL) 
    
    if "datetime" in df.columns:
        df["datetime"] = pd.to_datetime(df["datetime"], errors='coerce')
    if "全長_cm" in df.columns:
        df["全長_cm"] = pd.to_numeric(df["全長_cm"], errors='coerce')
    # df["場所"] = df["場所"].fillna("未設定")  # 必要なら追加
    return df
    # --- 計算用の安全な関数を追加 ---
def calc_elapsed_v2(r):
    try:
        # datetimeと直前の満潮_時刻が両方存在し、かつ計算可能な場合のみ実行
        if pd.notna(r['datetime']) and pd.notna(r['直前の満潮_時刻']):
            return (r['datetime'] - r['直前の満潮_時刻']).total_seconds() / 60 % 744
    except:
        pass
    return 0 # エラーや空データの場合は0を返す

def save_all(df, m_df):
    # スプレッドシートを更新（上書き）
    conn.update(spreadsheet=SHEET_URL, data=df)
    # 更新後はキャッシュをクリアして最新状態を表示させる
    st.cache_data.clear()

# マスターデータ（場所リスト）もシートで管理するか、固定にするか選べますが
# とりあえず既存のCSV読み込みのままでも動きます

# --- 3. メイン処理開始 ---
# ファイルの最終更新時刻を取得（これで自動更新を実現）
log_mtime = os.path.getmtime(LOG_CSV) if os.path.exists(LOG_CSV) else 0
master_mtime = os.path.getmtime(MASTER_CSV) if os.path.exists(MASTER_CSV) else 0

df = load_data_from_gs()
m_df = pd.read_csv("group_place_master.csv")

if df is not None:
    # 61行目：ここを if の中に入れるか、if の外に出すか確認してください
    # 通常、タブ定義は if の外（左端）に書くのが一般的です
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10= st.tabs([
    "📝 登録", 
    "📈 統計", 
    "🗺️ エリア分析", 
    "🌊 潮汐相関", 
    "🌬️ 気象影響", 
    "📊 統合レポート", 
    "🧪 LABO", 
    "🚩 風向別ポイント", 
    "🏆 RANKER ROAD",
    "🎯 PREDICT"
])
    place_options = sorted(m_df["place_name"].unique().tolist())

    # --- タブ1: 地点登録 ---
    with tab1:
        st.subheader("📸 写真と地点の紐付け")
        with st.expander("🆕 新しい釣り場をマスターに追加"):
            with st.form("add_master"):
                new_p = st.text_input("新しい場所名")
                if st.form_submit_button("マスター登録"):
                    if new_p and new_p not in m_df["place_name"].values:
                        new_id = m_df["group_id"].max() + 1 if not m_df.empty else 0
                        new_row = pd.DataFrame({"group_id": [new_id], "place_name": [new_p]})
                        m_df = pd.concat([m_df, new_row], ignore_index=True)
                        save_all(df, m_df)
                        st.success(f"「{new_p}」を登録！")
                        st.rerun()

        edit_filter = st.selectbox("場所で絞り込み", ["すべて"] + place_options)
        edit_df = df if edit_filter == "すべて" else df[df["場所"] == edit_filter]

        for idx, row in edit_df.sort_values("datetime", ascending=False).iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([1, 2])
                with c1:
                    img_source = get_image_for_display(row["filename"])
                    if img_source:
                        # 画像の下にURLを直接表示して、クリックできるか確認する
                        st.image(img_source, use_container_width=True)
                        st.caption(f"[画像リンク]({img_source})") 
                    else:
                        st.info("画像が見つかりません")
                with c2:
                    with st.form(key=f"edit_{idx}"):
                        f_fish = st.text_input("魚種", value=row["魚種"])
                        cur_size = float(row["全長_cm"]) if pd.notna(row["全長_cm"]) else 0.0
                        f_size = st.number_input("全長(cm)", value=cur_size, step=0.1)
                        cur_p = row["場所"] if row["場所"] in place_options else (place_options[0] if place_options else "未設定")
                        f_place = st.selectbox("場所", place_options, index=place_options.index(cur_p) if cur_p in place_options else 0)
                        if st.form_submit_button("保存"):
                            df.at[idx, "魚種"], df.at[idx, "全長_cm"], df.at[idx, "場所"] = f_fish, f_size, f_place
                            save_all(df, m_df)
                            st.rerun()

    # --- タブ2: 一覧 ---
    with tab2:
        st.subheader("📋 釣果一覧")
        available_cols = [c for c in ["datetime", "場所", "魚種", "全長_cm", "潮名", "天気", "ルアー"] if c in df.columns]
        st.dataframe(df[available_cols].sort_values("datetime", ascending=False), use_container_width=True, hide_index=True)

    # --- タブ3：ギャラリー表示（データ満載版） ---
        with tab3:
        st.header("釣果ギャラリー")

        # --- 1. まずデータを準備する (この行が抜けているとNameErrorになります) ---
        if 'df' in locals() and not df.empty:
            filtered_df = df.copy()  # ここで filtered_df を作成！
            
            # 最新を上にしたい場合は並び替え
            filtered_df = filtered_df.iloc[::-1]

            # --- 2. その後にループを回す ---
            for index, row in filtered_df.iterrows():
                img_source = get_image_for_display(row["filename"])
                
                # ...（以下、先ほどお送りした潮位や気象のコードを続ける）...

        else:
            st.info("データが読み込めていないか、まだ登録されていません。")
        for index, row in filtered_df.iterrows():
            img_source = get_image_for_display(row["filename"])
            
            # 基本データの取得
            fish_name = row.get('魚種', '不明')
            fish_size = row.get('全長_cm', '-')
            fish_date = row.get('datetime', '-')
            fish_place = row.get('場所', '不明')

            with st.container(border=True):
                if img_source:
                    st.image(img_source, use_container_width=True)
                    
                    # 1. メイン情報
                    st.markdown(f"### {fish_name} {fish_size}cm")
                    st.caption(f"📅 {fish_date} 📍 {fish_place}")

                    # 2. 気象条件（2列でコンパクトに表示）
                    st.markdown("---")
                    st.markdown("**🌡️ 気象コンディション**")
                    w1, w2, w3 = st.columns(3)
                    w1.metric("気温", f"{row.get('気温', '-')}℃")
                    w2.metric("風速", f"{row.get('風速', '-')}m/s", row.get('風向', ''))
                    w3.metric("天気", f"{row.get('天気', '-')}")

                    # 3. 潮汐データ（タイドグラフの代わりになる詳細数値）
                    st.markdown("**🌊 潮汐・タイドデータ**")
                    t1, t2 = st.columns(2)
                    with t1:
                        st.write(f"**潮名:** {row.get('潮名', '-')}")
                        st.write(f"**月齢:** {row.get('月齢', '-')}")
                        st.write(f"**フェーズ:** {row.get('潮位フェーズ', '-')}")
                    with t2:
                        st.write(f"**満潮:** {row.get('直前の満潮_時刻', '-')}")
                        st.write(f"**干潮:** {row.get('直前の干潮_時刻', '-')}")
                        st.write(f"**潮位:** {row.get('潮位_cm', '-')} cm")

                    # 4. 備考・ルアー
                    if pd.notna(row.get('備考')):
                        st.info(f"📝 {row.get('備考')}")
                    st.caption(f"🎣 使用ルアー: {row.get('ルアー', '-')}")

                else:
                    st.warning(f"画像が見つかりません: {fish_name}")
                    
    # --- タブ4: 攻略メモリー ---
    with tab4:
        st.subheader("🗺️ ポイント別攻略メモリー")
        target_place = st.selectbox("場所を選択", place_options, key="memo_p")
        
        # 1. 抽出
        suzuki_df = df[(df["場所"] == target_place) & (df["魚種"].str.contains("スズキ|シーバス|ヒラスズキ", na=False))].copy()
        
        # 【重要】データが空じゃないかチェック
        if suzuki_df.empty:
            st.warning(f"「{target_place}」でのスズキ・シーバスの釣果データが見つかりません。シートの魚種や場所の文字を確認してください。")
        else:
            # 2. 型の変換（スプレッドシート対策）
            suzuki_df['datetime'] = pd.to_datetime(suzuki_df['datetime'], errors='coerce')
            if '直前の満潮_時刻' in suzuki_df.columns:
                suzuki_df['直前の満潮_時刻'] = pd.to_datetime(suzuki_df['直前の満潮_時刻'], errors='coerce')
            
            # 数値列も念のため強制変換
            suzuki_df['全長_cm'] = pd.to_numeric(suzuki_df['全長_cm'], errors='coerce')
            suzuki_df['潮位_cm'] = pd.to_numeric(suzuki_df['潮位_cm'], errors='coerce')

            # 3. 計算実行
            suzuki_df['elapsed_mins'] = suzuki_df.apply(calc_elapsed_v2, axis=1)
            
            # 4. グラフ作成
            x_curve = np.linspace(0, 720, 100)
            y_curve = np.cos(2 * np.pi * x_curve / 720) * 130 + 180
            
            fig = go.Figure()
            # 潮汐カーブ
            fig.add_trace(go.Scatter(x=x_curve, y=y_curve, mode='lines', line=dict(color='gray', dash='dash'), name='潮汐目安'))
            
            # 釣果ポイント
            fig.add_trace(go.Scatter(
                x=suzuki_df['elapsed_mins'], 
                y=suzuki_df['潮位_cm'], 
                mode='markers+text', 
                marker=dict(size=12, color='cyan', line=dict(width=1, color='white')),
                text=suzuki_df['全長_cm'].astype(str) + "cm", 
                textposition="top center", 
                name='釣果'
            ))
            
            fig.update_layout(
                title=f"{target_place} の時合分析",
                xaxis_title="満潮からの経過時間 (分)",
                yaxis_title="潮位 (cm)",
                template="plotly_dark", 
                yaxis=dict(range=[0, 450]), 
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # デバッグ用：うまくいかない時に表を表示して確認
            if st.checkbox("抽出データを確認"):
                st.write(suzuki_df[['datetime', '魚種', '全長_cm', 'elapsed_mins']])

    # --- タブ5: 画像出力 ---
    with tab5:
        st.subheader("💾 攻略メモ入り画像の生成")
        if df is not None and not df.empty:
            sel_p = st.selectbox("1. 場所を選択", ["すべて"] + place_options, key="sb_tab5_p")
            filtered_df = df if sel_p == "すべて" else df[df["場所"] == sel_p]
            
            if not filtered_df.empty:
                filtered_df = filtered_df.copy()
                filtered_df['date_str'] = pd.to_datetime(filtered_df['datetime']).dt.strftime('%Y/%m/%d %H:%M').fillna('日付不明')
                
                target_idx = st.selectbox(
                    "2. 釣果を選択", 
                    filtered_df.index, 
                    format_func=lambda x: f"{filtered_df.loc[x,'date_str']} - {filtered_df.loc[x,'魚種']}",
                    key="sb_tab5_f"
                )
                
                if st.button("🖼️ 攻略画像を生成する", key="btn_gen_tab5"):
                    try:
                        row = df.loc[target_idx]
                        img_path = os.path.join(PHOTO_DIR, str(row["filename"]))
                        if os.path.exists(img_path):
                            with st.spinner("生成中..."):
                                with Image.open(img_path) as tmp_img:
                                    tmp_img.thumbnail((1400, 1400))
                                    base_img = tmp_img.convert("RGBA")
                                
                                w, h = base_img.size
                                txt_layer = Image.new("RGBA", base_img.size, (0,0,0,0))
                                d = ImageDraw.Draw(txt_layer)
                                is_vertical = h > w
                                overlay_h = int(h * 0.28) if is_vertical else int(h * 0.22)
                                d.rectangle([(0, h - overlay_h), (w, h)], fill=(0, 0, 0, 160))

                              # --- フォント設定のWeb対応版 ---
                                # Linuxサーバー(Streamlit Cloud)で一般的に入っている日本語フォントを指定
                                fonts = [
                                    "/usr/share/fonts/fonts-goethe/TakaoGothic.ttf",
                                    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
                                    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
                                    "C:\\Windows\\Fonts\\msgothic.ttc" # PC実行時用
                                ]
                                
                                f_path = None
                                for f in fonts:
                                    if os.path.exists(f):
                                        f_path = f
                                        break
                                
                                f_scale = 0.85 if is_vertical else 1.0
                                try:
                                    if f_path:
                                        f_large = ImageFont.truetype(f_path, int(h * 0.045 * f_scale))
                                        f_mid = ImageFont.truetype(f_path, int(h * 0.038 * f_scale))
                                        f_small = ImageFont.truetype(f_path, int(h * 0.032 * f_scale))
                                    else:
                                        f_large = f_mid = f_small = ImageFont.load_default()
                                except:
                                    f_large = f_mid = f_small = ImageFont.load_default()

                                hit_dt = pd.to_datetime(row['datetime'])
                                high_dt = pd.to_datetime(row['直前の満潮_時刻'])
                                tide_txt = "Tide: Unknown"
                                if pd.notna(hit_dt) and pd.notna(high_dt):
                                    diff_mins = (hit_dt - high_dt).total_seconds() / 60 % 744
                                    tide_dir = "下げ" if diff_mins <= 372 else "上げ"
                                    step = int((diff_mins / 372 * 10) if diff_mins <= 372 else ((diff_mins-372)/372*10))
                                    tide_txt = f"{tide_dir} {max(0, min(10, step))}   ({row.get('潮位_cm', '-')}cm)"

                                margin = 60
                                if is_vertical:
                                    text_x, text_y = margin, h - overlay_h + 30
                                    graph_w, graph_h = int(w * 0.75), int(h * 0.08)
                                    graph_x, graph_y = (w - graph_w) // 2, h - graph_h - 40
                                    line_spacing = int(h * 0.045)
                                else:
                                    text_x, text_y = margin, h - overlay_h + 30
                                    graph_w, graph_h = int(w * 0.35), int(h * 0.12)
                                    graph_x, graph_y = w - graph_w - margin, h - graph_h - 50
                                    line_spacing = 65

                                d.text((text_x, text_y), f"{row['場所']} / {filtered_df.loc[target_idx, 'date_str']}", fill=(255,255,255), font=f_large)
                                d.text((text_x, text_y + line_spacing), tide_txt, fill=(255,255,255), font=f_mid)
                                d.text((text_x, text_y + line_spacing + 50), f"Temp: {row.get('気温','-')}C  Wind: {row.get('風向','-')}{row.get('風速','-')}m", fill=(255,255,255,220), font=f_small)
                                d.text((text_x, text_y + line_spacing + 95), f"Lure: {row.get('ルアー','-')}", fill=(255,255,255,220), font=f_small)

                                # タイドグラフ描画
                                fill_pts = [(graph_x + x, graph_y + (graph_h/2) - (np.cos(2 * np.pi * (x/graph_w)) * (graph_h/2.5))) for x in range(graph_w)]
                                fill_pts.extend([(graph_x + graph_w, graph_y + graph_h), (graph_x, graph_y + graph_h)])
                                d.polygon(fill_pts, fill=(0, 191, 255, 80))
                                d.line(fill_pts[:-2], fill=(255, 255, 255, 200), width=3)
                                
                                out_img = Image.alpha_composite(base_img, txt_layer).convert("RGB")
                                st.image(out_img, use_container_width=True)
                                buf = io.BytesIO()
                                out_img.save(buf, format="JPEG", quality=95)
                                st.download_button("📥 完成画像を保存", buf.getvalue(), f"FishingLog_{target_idx}.jpg", "image/jpeg")
                    except Exception as e:
                        st.error(f"エラー: {e}")

    # --- タブ6: 統合攻略レポート（風向き実績・数ベース修正版） ---
    with tab6:
        st.subheader("📊 攻略統計 & 統合分析レポート")
        
        # 1. 計算関数の定義
        def calc_tide_step(row):
            if pd.isna(row['datetime']) or pd.isna(row.get('直前の満潮_時刻')): return "-"
            try:
                diff = (row['datetime'] - row['直前の満潮_時刻']).total_seconds() / 60 % 744
                direction = "下げ" if diff <= 372 else "上げ"
                step_val = int((diff / 372 * 10) if diff <= 372 else ((diff-372)/372*10))
                return f"{direction} {max(0, min(10, step_val))}"
            except: return "-"

        # 2. データの準備
        target_fish_pattern = "スズキ|シーバス|ヒラスズキ"
        stats_df = df[df["魚種"].str.contains(target_fish_pattern, na=False) & (df["全長_cm"] > 0)].copy()
        
        if stats_df.empty:
            st.info("統計用の釣果データがまだありません。")
        else:
            # --- ここから書き換え ---
            # 1. 計算の前に日付型へ強制変換（スプレッドシートからの読み込み対策）
            stats_df['datetime'] = pd.to_datetime(stats_df['datetime'], errors='coerce')
            # 潮汐データがない行でもエラーにならないよう、存在する列だけ変換
            if '直前の満潮_時刻' in stats_df.columns:
                stats_df['直前の満潮_時刻'] = pd.to_datetime(stats_df['直前の満潮_時刻'], errors='coerce')

            # 2. .dt.month などの処理を安全に行う
            stats_df['月'] = stats_df['datetime'].dt.month
            stats_df['潮時ステップ'] = stats_df.apply(calc_tide_step, axis=1)

            # 3. エラーが出ていた計算式（空データや型違いをガードする）
            def calc_elapsed(r):
                try:
                    # 両方の時刻が存在する場合のみ計算
                    if pd.notna(r['datetime']) and pd.notna(r['直前の満潮_時刻']):
                        return (r['datetime'] - r['直前の満潮_時刻']).total_seconds() / 60 % 744
                except:
                    pass
                return 0

            stats_df['elapsed_mins'] = stats_df.apply(calc_elapsed, axis=1)
            # --- ここまで書き換え ---

            selected_p = st.selectbox("分析ターゲットを選択", ["すべての場所"] + place_options, key="final_refined_report_p")
            f_df = stats_df if selected_p == "すべての場所" else stats_df[stats_df["場所"] == selected_p]

            # --- 3. 最大魚 & 攻略指標サマリー ---
            if not f_df.empty:
                big_fish = f_df.loc[f_df['全長_cm'].idxmax()]
                st.write(f"### 🏆 {selected_p} 攻略指標")
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("最大サイズ", f"{big_fish['全長_cm']} cm")
                m2.metric("最大ヒット潮位", f"{big_fish.get('潮位_cm','-')} cm")
                top_tide = f_df['潮時ステップ'].value_counts().idxmax()
                f_df['潮位レンジ'] = (f_df['潮位_cm'] // 20 * 20).astype(int)
                top_level = f_df['潮位レンジ'].value_counts().idxmax()
                m3.metric("最多ヒット潮時", top_tide)
                m4.metric("最多ヒット潮位", f"{top_level}cm～")

            # --- 4. メイン潮汐相関図 ---
            st.write("---")
            st.write("### 🗺️ 潮汐相関図（満潮からの時間 × 潮位）")
            if not f_df.empty:
                x_curve = np.linspace(0, 720, 100)
                y_curve = np.cos(2 * np.pi * x_curve / 720) * 130 + 180
                fig_tide = go.Figure()
                fig_tide.add_trace(go.Scatter(x=x_curve, y=y_curve, mode='lines', line=dict(color='red', dash='dash'), name='潮汐曲線'))
                fig_tide.add_trace(go.Scatter(
                    x=f_df['elapsed_mins'], y=f_df['潮位_cm'], mode='markers+text', 
                    marker=dict(size=14, color='silver', line=dict(width=2, color='cyan')),
                    text=f_df['全長_cm'], textposition="top center", name='釣果'
                ))
                fig_tide.update_layout(template="plotly_dark", yaxis=dict(range=[0, 400], title="潮位 (cm)"), 
                                       xaxis=dict(title="満潮からの経過時間 (分)"), height=500, showlegend=False)
                st.plotly_chart(fig_tide, use_container_width=True)

            # --- 5. 月別実績トレンド ---
            st.write("---")
            st.write("### 📅 月別実績トレンド")
            monthly_stats = f_df.groupby('月')['全長_cm'].agg(['count', 'mean']).reset_index()
            monthly_stats = pd.merge(pd.DataFrame({'月': range(1, 13)}), monthly_stats, on='月', how='left').fillna(0)
            fig_monthly = go.Figure()
            fig_monthly.add_trace(go.Bar(x=monthly_stats['月'], y=monthly_stats['count'], name='数', marker_color='rgba(0, 204, 255, 0.6)'))
            fig_monthly.add_trace(go.Scatter(x=monthly_stats['月'], y=monthly_stats['mean'], name='平均サイズ', line=dict(color='#FFCC00', width=3), yaxis='y2'))
            fig_monthly.update_layout(template="plotly_dark", height=350, yaxis2=dict(overlaying='y', side='right', range=[0, 100]), 
                                       xaxis=dict(tickmode='linear', dtick=1), showlegend=False)
            st.plotly_chart(fig_monthly, use_container_width=True)

            # --- 6. 詳細分析（潮名・風向き(数ベース)・ルアーTop10） ---
            st.write("---")
            st.write("### 🔍 詳細実績分析")
            c1, c2, c3 = st.columns(3)
            
            with c1:
                st.write("#### 🌊 潮名別実績（数）")
                if "潮名" in f_df.columns:
                    t_counts = f_df["潮名"].value_counts().reset_index()
                    fig_t_bar = px.bar(t_counts, x='潮名', y='count', template="plotly_dark", color_discrete_sequence=['#00CCFF'])
                    fig_t_bar.update_layout(height=300, showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_t_bar, use_container_width=True)
            
            with c2:
                st.write("#### 🌬️ 風向き別実績（数）")
                if "風向" in f_df.columns:
                    # 縦軸を数、色を最大サイズに設定
                    w_stats = f_df.groupby('風向')['全長_cm'].agg(['count', 'max']).reset_index()
                    fig_w = px.bar(w_stats, x='風向', y='count', color='max', 
                                   labels={'count':'キャッチ数', 'max':'最大サイズ'},
                                   template="plotly_dark", color_continuous_scale='Viridis')
                    fig_w.update_layout(height=300, showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig_w, use_container_width=True)
            
            with c3:
                st.write("#### 🎣 ルアーTop10")
                if "ルアー" in f_df.columns:
                    l_counts = f_df["ルアー"].value_counts().head(10).reset_index()
                    fig_l = px.bar(l_counts, x='count', y='ルアー', orientation='h', template="plotly_dark", color_discrete_sequence=['#FFCC00'])
                    fig_l.update_layout(height=300, showlegend=False, margin=dict(t=0, b=0, l=0, r=0), yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig_l, use_container_width=True)

            # --- 7. 画像レポート生成 ---
            if st.button("🖼️ 統合レポート画像を生成"):
                try:
                    from plotly.subplots import make_subplots
                    fig_rep = make_subplots(
                        rows=3, cols=2,
                        subplot_titles=("【潮汐相関図】", "【月別トレンド】", "【潮名実績】", "【風向き実績】", "【ルアーTop10】"),
                        specs=[[{"colspan": 2}, None], [{}, {}], [{"colspan": 2}, None]]
                    )
                    fig_rep.add_trace(go.Scatter(x=x_curve, y=y_curve, mode='lines', line=dict(color='red', dash='dash')), row=1, col=1)
                    fig_rep.add_trace(go.Scatter(x=f_df['elapsed_mins'], y=f_df['潮位_cm'], mode='markers+text', text=f_df['全長_cm']), row=1, col=1)
                    fig_rep.add_trace(go.Bar(x=monthly_stats['月'], y=monthly_stats['count']), row=2, col=1)
                    tc = f_df["潮名"].value_counts(); fig_rep.add_trace(go.Bar(x=tc.index, y=tc.values), row=2, col=2)
                    wc = f_df["風向"].value_counts(); fig_rep.add_trace(go.Bar(x=wc.index, y=wc.values), row=3, col=1)
                    fig_rep.update_layout(template="plotly_dark", height=1000, width=900, showlegend=False)
                    img_bytes = fig_rep.to_image(format="png", engine="kaleido")
                    st.image(img_bytes)
                    st.download_button("この画像を保存", img_bytes, "Fishing_Final_Report.png", "image/png")
                except:
                    st.error("画像生成エラー。")
# --- タブ7: LABO（ルアー別・サイズ相関分析） ---
    with tab7:
        st.subheader("🧪 ルアー選択 × ターゲットサイズ相関")
        
        # データの準備（ルアー名が入っているものに限定）
        lure_df = stats_df[stats_df["ルアー"].notna() & (stats_df["全長_cm"] > 0)].copy()
        
        if lure_df.empty:
            st.info("ルアー別の釣果データが不足しています。")
        else:
            # 1. ルアー別・サイズ分布比較（箱ひげ図）
            st.write("### 🎣 ルアー別：平均・最大サイズ分布")
            # 出現頻度が高い上位15個のルアーに絞って表示
            top_lures = lure_df["ルアー"].value_counts().nlargest(15).index
            lure_sub_df = lure_df[lure_df["ルアー"].isin(top_lures)]
            
            fig_lure_box = px.box(
                lure_sub_df, x="ルアー", y="全長_cm", color="ルアー",
                points="all", # 全データ点を表示
                template="plotly_dark",
                title="ルアーごとのサイズ実績（上位15種）"
            )
            fig_lure_box.update_layout(showlegend=False, xaxis={'categoryorder':'total descending'})
            st.plotly_chart(fig_lure_box, use_container_width=True)

            # 2. ルアー名から「長さ(mm)」を推測した相関分析（実験的）
            # ※ルアー名に '120' や '140' などの数字が含まれている場合を抽出
            import re
            def extract_lure_size(name):
                nums = re.findall(r'\d+', str(name))
                for n in nums:
                    if 50 <= int(n) <= 250: # 一般的なルアーサイズ範囲
                        return int(n)
                return None

            lure_df['lure_size_mm'] = lure_df['ルアー'].apply(extract_lure_size)
            lure_size_df = lure_df.dropna(subset=['lure_size_mm'])

            st.write("---")
            st.write("### 📈 ルアー自体の大きさと魚のサイズの相関")
            if not lure_size_df.empty:
                fig_size_corr = px.scatter(
                    lure_size_df, x="lure_size_mm", y="全長_cm", 
                    color="魚種", size="全長_cm",
                    trendline="ols",
                    template="plotly_dark",
                    labels={"lure_size_mm": "ルアーの全長 (mm)", "全長_cm": "魚の全長 (cm)"},
                    title="『大きなルアーには大きな魚』は本当か？"
                )
                st.plotly_chart(fig_size_corr, use_container_width=True)
            else:
                st.info("ルアー名にサイズ（mm）が含まれるデータが少ないため、散布図はスキップします。")

            # 3. テキストサマリー
            st.write("---")
            st.write("### 📝 ルアー別サイズ・サマリー")
            
            # 各ルアーの平均サイズTOP5
            lure_stats = lure_df.groupby('ルアー')['全長_cm'].agg(['count', 'mean', 'max']).reset_index()
            # 3匹以上釣っているルアーに限定して、平均サイズ順にソート
            best_lures = lure_stats[lure_stats['count'] >= 3].sort_values('mean', ascending=False).head(5)
            
            c1, c2 = st.columns(2)
            with c1:
                st.success("**🏆 平均サイズが高いルアー (3本以上実績)**")
                for _, row in best_lures.iterrows():
                    st.write(f"- **{row['ルアー']}**: 平均 {row['mean']:.1f}cm (最大 {row['max']}cm)")
            
            with c2:
                # 最も「数」が釣れているルアー
                prolific_lure = lure_stats.sort_values('count', ascending=False).iloc[0]
                st.info("**🐟 最も数が釣れているエースルアー**")
                st.write(f"- **{prolific_lure['ルアー']}**")
                st.write(f"  合計 {prolific_lure['count']} 匹 (平均 {prolific_lure['mean']:.1f}cm)")

# --- タブ8: 風向別・ポイント分析 (漢字対応版) ---
    with tab8:
        st.subheader("🚩 風向き別・最適ポイント分析")
        
        # データの準備（漢字の風向・場所が揃っているデータのみ）
        wind_place_df = stats_df.dropna(subset=['風向', '場所']).copy()

        if wind_place_df.empty:
            st.warning("風向と場所の両方が入力されているデータがまだありません。")
        else:
            # 1. 表示順序を漢字の「風配図順」に定義
            wind_order_jp = ["北", "北東", "東", "南東", "南", "南西", "西", "北西"]
            
            # 実績が存在する風向きをリストアップ（セレクトボックス用）
            existing_winds = [w for w in wind_order_jp if w in wind_place_df['風向'].unique()]
            
            if not existing_winds:
                st.info("集計可能な風向きデータ（北、南西など）がまだありません。")
            else:
                # 2. 【風向 × 場所】ヒートマップ
                st.write("### 🌡️ 風向 × 場所 実績分布")
                
                # ピボットテーブルの作成
                heatmap_data = wind_place_df.groupby(['場所', '風向']).size().reset_index(name='ヒット数')
                heatmap_pivot = heatmap_data.pivot(index='場所', columns='風向', values='ヒット数').fillna(0)
                
                # 存在する風向きだけでカラムを並び替え
                available_order = [w for w in wind_order_jp if w in heatmap_pivot.columns]
                heatmap_pivot = heatmap_pivot[available_order]

                fig_hp = px.imshow(
                    heatmap_pivot, 
                    color_continuous_scale="Reds", 
                    template="plotly_dark",
                    labels=dict(x="風向き", y="場所", color="ヒット数")
                )
                st.plotly_chart(fig_hp, use_container_width=True)

                # 3. 風向き選択と詳細分析
                st.write("---")
                selected_wind = st.selectbox("🎯 調査する風向きを選択", existing_winds, key="wind_select_tab8")
                
                # 選択された風向きのデータを抽出
                target_wind_df = wind_place_df[wind_place_df['風向'] == selected_wind]
                
                # データが存在する場合のみグラフとアドバイスを表示
                if not target_wind_df.empty:
                    place_ranking = target_wind_df.groupby('場所')['全長_cm'].agg(['count', 'mean', 'max']).reset_index()
                    place_ranking = place_ranking.sort_values('count', ascending=False)
                    
                    st.write(f"### 🏆 【{selected_wind}】の時の推奨ポイント")
                    
                    fig_rank = px.bar(
                        place_ranking, x='場所', y='count', color='mean',
                        labels={'count': 'ヒット数', 'mean': '平均サイズ(cm)'},
                        template="plotly_dark", 
                        color_continuous_scale="Viridis"
                    )
                    st.plotly_chart(fig_rank, use_container_width=True)

                    # 💡 安全に「1位の場所」を表示する（IndexError対策）
                    if len(place_ranking) > 0:
                        top_place = place_ranking.iloc[0]['場所']
                        st.info(f"💡 **アドバイス:** {selected_wind}の風の時は、**{top_place}** が最も実績があります。")
                else:
                    st.info(f"【{selected_wind}】の風での実績データはまだありません。")

# --- タブ9: RANKER ROAD（自己記録分析） ---
    with tab9:
        st.subheader("🏆 RANKER ROAD - 自己記録への挑戦")
        
        # サイズデータがあるものに限定
        ranker_df = stats_df[stats_df["全長_cm"] > 0].copy()
        
        if ranker_df.empty:
            st.info("釣果データが不足しています。まずは1匹登録しましょう！")
        else:
            # 1. 記録のサマリー
            best_3 = ranker_df.sort_values("全長_cm", ascending=False).head(3)
            current_max = best_3.iloc[0]["全長_cm"]
            
            c_r1, c_r2, c_r3 = st.columns(3)
            with c_r1:
                st.metric("自己ベスト", f"{current_max} cm")
            with c_r2:
                # 80cmをランカーとした場合
                to_80 = max(0, 80 - current_max)
                st.metric("ランカーまで", f"あと {to_80} cm" if to_80 > 0 else "🎉 達成済み！")
            with c_r3:
                st.metric("平均サイズ", f"{ranker_df['全長_cm'].mean():.1f} cm")

            # 2. 上位20%の「大型魚」のみに絞った共通点分析
            threshold = ranker_df["全長_cm"].quantile(0.8) # 上位20%のサイズ
            big_fish_df = ranker_df[ranker_df["全長_cm"] >= threshold]

            st.write("---")
            st.write(f"### 🎯 大型（{threshold:.0f}cm以上）のヒットパターン")
            
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                st.write("**【鉄板ルアー】**")
                top_lures = big_fish_df["ルアー"].value_counts().head(3)
                for l, count in top_lures.items():
                    st.write(f"🔥 {l} ({count}件)")
                    
            with col_b2:
                st.write("**【最強の潮位】**")
                # 潮位を10cm刻みで集計
                big_fish_df['潮位帯'] = (big_fish_df['潮位_cm'] // 10 * 10).astype(str) + "cm台"
                top_tide = big_fish_df["潮位帯"].value_counts().idxmax()
                st.info(f"もっとも大型が釣れる潮位は **{top_tide}** です。")

            # 3. サイズ分布の可視化（ヒストグラム）
            st.write("---")
            st.write("### 📏 全釣果のサイズ分布")
            fig_size_dist = px.histogram(
                ranker_df, x="全長_cm", 
                nbins=20, 
                color_discrete_sequence=['#FFD700'], # ゴールド
                template="plotly_dark",
                marginal="rug" # 下に個別のデータ点も表示
            )
            fig_size_dist.update_layout(bargap=0.1)
            # 80cmのラインに赤い縦線を引く
            fig_size_dist.add_vline(x=80, line_dash="dash", line_color="red", annotation_text="RANKER LINE")
            st.plotly_chart(fig_size_dist, use_container_width=True)

            # 4. 月別・最大サイズ推移
            st.write("---")
            st.write("### 📅 月別・サイズポテンシャル")
            monthly_max = ranker_df.groupby(ranker_df['datetime'].dt.month)['全長_cm'].agg(['max', 'mean']).reset_index()
            monthly_max.columns = ['月', '最大', '平均']
            
            fig_monthly = px.line(
                monthly_max, x='月', y=['最大', '平均'],
                markers=True,
                color_discrete_map={'最大': '#FF4B4B', '平均': '#00CCFF'},
                template="plotly_dark",
                title="どの月に大物が期待できるか？"
            )
            st.plotly_chart(fig_monthly, use_container_width=True)
# 4. あなただけの「勝利の方程式」を自動生成
        st.write("---")
        st.markdown("### 🧬 勝利の方程式 (Your Winning DNA)")
        
        # 過去の70cm以上のデータから、最も頻度の高い組み合わせを抽出
        expert_df = ranker_df[ranker_df["全長_cm"] >= 70]
        
        if not expert_df.empty:
            best_place = expert_df["場所"].mode()[0]
            best_wind = expert_df["風向"].mode()[0]
            best_lure = expert_df["ルアー"].mode()[0]
            
            st.info(f"""
            あなたのデータが導き出した、ランカー捕獲の最短ルートはこれです：
            - **狙うべき場所**: {best_place}
            - **必要な風向き**: {best_wind}
            - **信頼すべきルアー**: {best_lure}
            
            この3条件が重なる日は、仕事を休んででも磯に立つ価値があります。
            """)
        else:
            st.write("70cm以上のデータが蓄積されると、あなただけの『方程式』がここに表示されます。")
# --- タブ9: RANKER ROAD（詳細条件分析） ---
    with tab9:
        st.subheader("🏆 RANKER ROAD - 場所別・大型狙撃条件")
        
        # データの準備
        df_ranker = stats_df[stats_df["全長_cm"] > 0].copy()
        
        if df_ranker.empty:
            st.info("データが不足しています。")
        else:
            # 場所の選択（大型の実績がある場所に絞る）
            big_threshold = 70  # 大型とみなすサイズ
            places_with_big = df_ranker[df_ranker["全長_cm"] >= big_threshold]["場所"].unique()
            
            if len(places_with_big) == 0:
                st.warning(f"{big_threshold}cm以上の実績がまだありません。全データから傾向を表示します。")
                target_places = df_ranker["場所"].unique()
            else:
                target_places = places_with_big

            selected_p = st.selectbox("📍 調査するポイントを選択", target_places)
            
            # 選択した場所の大型データ（なければ全データ）
            p_df = df_ranker[df_ranker["場所"] == selected_p]
            p_big_df = p_df[p_df["全長_cm"] >= big_threshold]
            
            # 大型データが少ない場合は場所の全データを使用
            analysis_df = p_big_df if len(p_big_df) >= 2 else p_df

            st.write(f"### 🎯 【{selected_p}】の大型ヒット・プロファイル")
            
            # --- 4つのカラムで詳細表示 ---
            r_col1, r_col2, r_col3, r_col4 = st.columns(4)
            
            with r_col1:
                st.write("**📅 時期・月齢**")
                m_best = analysis_df['datetime'].dt.month.mode()[0]
                # 月齢データがあれば表示（備考欄などから抽出している場合）
                st.write(f"- 最強月: {m_best}月")
                if '月齢' in analysis_df.columns:
                    st.write(f"- 月齢: {analysis_df['月齢'].mode()[0]}")
            
            with r_col2:
                st.write("**🌊 潮汐条件**")
                t_name = analysis_df['潮名'].mode()[0]
                t_dir = analysis_df['潮時ステップ'].apply(lambda x: '下げ' if '下げ' in str(x) else '上げ').mode()[0]
                st.write(f"- 潮名: {t_name}")
                st.write(f"- 動き: {t_dir}")

            with r_col3:
                st.write("**🌬️ 気象条件**")
                w_dir = analysis_df['風向'].mode()[0]
                w_spd = analysis_df['風速'].mean()
                st.write(f"- 風向: {w_dir}")
                st.write(f"- 風速: {w_spd:.1f}m/s")

            with r_col4:
                st.write("**📏 潮位帯**")
                t_level = (analysis_df['潮位_cm'] // 10 * 10).mode()[0]
                st.write(f"- 潮位: {t_level:.0f}cm台")

            # --- 視覚化：場所ごとのサイズ分布（月別・潮位別） ---
            st.write("---")
            st.write(f"#### 【{selected_p}】月別・サイズ分布マップ")
            
            fig_p_heat = px.density_heatmap(
                p_df, x=p_df['datetime'].dt.month, y="全長_cm",
                labels={'x': '月', 'y': 'サイズ'},
                color_continuous_scale="Viridis",
                template="plotly_dark",
                nbinsx=12, nbinsy=10
            )
            st.plotly_chart(fig_p_heat, use_container_width=True)

            # --- 結論アドバイス ---
            st.info(f"""
            💡 **{selected_p} の攻略法:**
            この場所では、**{m_best}月**の**{t_name}**、特に**{t_dir}**のタイミングで**潮位{t_level:.0f}cm付近**を狙うのが、
            過去の統計上、最も大型に出会える確率が高い「黄金の時合い」です。
            """)

# --- タブ10: PREDICT（精密予測シミュレーター） ---
    with tab10:
        st.subheader("🎯 本日の精密予測")
        st.write("今日の予報を入力すると、過去の全データから「最も条件が近いパターン」を算出します。")

        # --- 入力セクション ---
        c_i1, c_i2, c_i3 = st.columns(3)
        with c_i1:
            in_wind = st.selectbox("予報の風向き", ["北", "北東", "東", "南東", "南", "南西", "西", "北西"], key="p_v2_wind")
            in_tide_move = st.radio("狙うタイミング", ["上げ", "下げ"], horizontal=True, key="p_v2_move")
        with c_i2:
            in_tide_name = st.selectbox("潮回り", ["大潮", "中潮", "小潮", "長潮", "若潮"], key="p_v2_tide")
            in_moon = st.slider("今日の月齢 (目安)", 0, 30, 15, key="p_v2_moon")
        with c_i3:
            in_rain = st.checkbox("雨（または雨後）", key="p_v2_rain")
            in_target_size = st.slider("目標サイズ (cm)", 50, 90, 70)

        # --- 柔軟なフィルタリングロジック ---
        # 1. 風向きのグループ化（北なら北東・北西も含む）
        wind_groups = {
            "北": ["北", "北東", "北西"],
            "南": ["南", "南東", "南西"],
            "東": ["東", "北東", "南東"],
            "西": ["西", "北西", "南西"],
            "北東": ["北東", "北", "東"],
            "南東": ["南東", "南", "東"],
            "南西": ["南西", "南", "西"],
            "北西": ["北西", "北", "西"]
        }
        target_winds = wind_groups.get(in_wind, [in_wind])

        # 2. 過去データの抽出（風向きグループ + 潮の動き）
        p_df = stats_df[
            (stats_df["風向"].isin(target_winds)) & 
            (stats_df["潮時ステップ"].str.contains(in_tide_move, na=False))
        ].copy()

        st.write("---")

        if not p_df.empty:
            # 3. スコアリング機能（各条件の一致度を点数化）
            def calculate_score(row):
                score = 0
                if row["潮名"] == in_tide_name: score += 30
                if abs(row.get("月齢", in_moon) - in_moon) <= 2: score += 20
                if in_rain and row.get("降水量", 0) > 0: score += 20
                if row["全長_cm"] >= in_target_size: score += 30
                return score

            p_df["期待度スコア"] = p_df.apply(calculate_score, axis=1)
            
            # 場所ごとの期待値を集計
            predict_ranking = p_df.groupby("場所").agg({
                "期待度スコア": "mean",
                "全長_cm": ["count", "max", "mean"],
                "潮位_cm": lambda x: x.mode()[0] if not x.mode().empty else x.mean()
            }).reset_index()
            
            # カラム名を整理
            predict_ranking.columns = ["場所", "スコア", "実績数", "最大サイズ", "平均サイズ", "推奨潮位"]
            predict_ranking = predict_ranking.sort_values("スコア", ascending=False)

            # --- 結果表示 ---
            best = predict_ranking.iloc[0]
            
            col_res1, col_res2 = st.columns([2, 1])
            with col_res1:
                st.success(f"### 🔥 今日の最適ポイント: 【{best['場所']}】")
                st.write(f"風向きグループ（{', '.join(target_winds)}）と潮の動きを優先し、過去の{in_tide_name}の実績から算出しました。")
            with col_res2:
                st.metric("マッチング期待度", f"{int(best['スコア'])}%")

            # 推奨される詳細条件
            st.info(f"""
            📌 **{best['場所']} の精密エントリーデータ**
            - **推奨潮位**: {best['推奨潮位']:.0f} cm 付近
            - **狙いのタイミング**: {in_tide_name} の {in_tide_move}
            - **過去の最大サイズ**: {best['最大サイズ']} cm
            - **実績ルアー**: {p_df[p_df['場所']==best['場所']]['ルアー'].mode()[0]}
            """)

            # ランキング表示
            st.write("#### 🥈 その他の候補ポイント")
            st.dataframe(predict_ranking[["場所", "実績数", "最大サイズ", "スコア"]].head(5), use_container_width=True)

        else:

            st.warning("⚠️ 指定された風向きグループでの実績がまだありません。")

































