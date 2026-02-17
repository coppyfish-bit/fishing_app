import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def show_analysis_page(df):
    st.subheader("📊 場所別・時合解析（タイド連携）")

    if df.empty:
        st.info("解析するデータがまだありません。")
        return

    # --- 1. 場所の選択 ---
    place_list = sorted(df["場所"].unique().tolist())
    selected_place = st.selectbox("📍 解析する場所を選択", place_list)
    
    df_place = df[df["場所"] == selected_place].copy()
    df_place['datetime'] = pd.to_datetime(df_place['datetime'])
    # 時刻のみを数値（時間）に変換（例: 14:30 -> 14.5）
    df_place['hour_float'] = df_place['datetime'].dt.hour + df_place['datetime'].dt.minute / 60

    # --- 2. 仮想タイドグラフの作成 (サインカーブ) ---
    # 釣りで一般的な6時間周期の干満をシミュレーション
    x_tide = np.linspace(0, 24, 500)
    # 潮位の高さ（-100〜100の範囲で仮想化）
    y_tide = 80 * np.sin(2 * np.pi * x_tide / 12.4) # 潮汐周期は約12.4時間

    fig = go.Figure()

    # タイドグラフの背景線
    fig.add_trace(go.Scatter(
        x=x_tide, y=y_tide,
        mode='lines',
        line=dict(color='rgba(100, 150, 255, 0.5)', width=2, shape='spline'),
        name='仮想タイド曲線',
        hoverinfo='skip'
    ))

    # --- 3. 釣果ポイントのプロット ---
    # 潮位フェーズから縦軸の位置を推測する関数
    def get_y_pos(phase):
        if "上げ" in phase:
            # 上げ1分〜9分を -80 〜 +80 にマップ
            step = int(''.join(filter(str.isdigit, phase))) if any(c.isdigit() for c in phase) else 5
            return -80 + (step * 16)
        elif "下げ" in phase:
            # 下げ1分〜9分を +80 〜 -80 にマップ
            step = int(''.join(filter(str.isdigit, phase))) if any(c.isdigit() for c in phase) else 5
            return 80 - (step * 16)
        return 0

    df_place['y_pos'] = df_place['潮位フェーズ'].apply(get_y_pos)

    # 実際の釣果をプロット
    fig.add_trace(go.Scatter(
        x=df_place['hour_float'],
        y=df_place['y_pos'],
        mode='markers+text',
        marker=dict(
            size=12,
            color='#00ffd0',
            line=dict(width=2, color='white'),
            symbol='diamond'
        ),
        text=df_place['魚種'] + df_place['全長_cm'].astype(str) + "cm",
        textposition="top center",
        hovertemplate="時刻: %{x:.2f}時<br>フェーズ: %{customdata}<br>%{text}<extra></extra>",
        customdata=df_place['潮位フェーズ'],
        name='釣果ポイント'
    ))

    # レイアウト設定
    fig.update_layout(
        xaxis_title="時刻 (0-24h)",
        yaxis_title="潮位イメージ (干潮 ←→ 満潮)",
        xaxis=dict(tickmode='linear', tick0=0, dtick=3, range=[0, 24]),
        yaxis=dict(showticklabels=False, range=[-110, 110]),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=20, b=20),
        height=400,
        showlegend=False
    )

    # グリッド線の追加
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.1)')
    
    st.plotly_chart(fig, use_container_width=True)

    # --- 4. 統計情報の表示 ---
    st.write(f"🔍 **{selected_place}** の傾向")
    col1, col2 = st.columns(2)
    with col1:
        most_common_phase = df_place['潮位フェーズ'].mode()[0] if not df_place.empty else "-"
        st.metric("ヒット率の高いフェーズ", most_common_phase)
    with col2:
        avg_size = df_place['全長_cm'].mean() if not df_place.empty else 0
        st.metric("平均サイズ", f"{avg_size:.1f} cm")