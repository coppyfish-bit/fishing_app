import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import re

def show_analysis_page(df):
    st.subheader("📊 時合精密解析（スズキ・ヒラスズキ優先表示）")

    if df.empty:
        st.info("データがありません。")
        return

    # --- 1. フィルタリング設定 ---
    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        selected_place = st.selectbox("📍 場所を選択", sorted(df["場所"].unique()))
    
    with col_f2:
        # 魚種リストの取得
        all_species = sorted(df[df["場所"] == selected_place]["魚種"].unique())
        
        # 「スズキ」「ヒラスズキ」が存在すればデフォルトで選択状態にする
        initial_targets = ["スズキ", "ヒラスズキ"]
        default_selection = [s for s in initial_targets if s in all_species]
        
        selected_species = st.multiselect(
            "🐟 表示する魚種を選択", 
            all_species, 
            default=default_selection
        )

    # 何も選択されていない場合は案内を出す
    if not selected_species:
        st.info("👆 魚種を選択してください（スズキ・ヒラスズキは自動選択されます）")
        return

    # 以降、グラフ描画ロジックへ続く...
    # (以前お渡ししたコードと同じです)
