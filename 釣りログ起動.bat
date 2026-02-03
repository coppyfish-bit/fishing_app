@echo off
cd /d %~dp0
echo 🎣 釣果入力アプリを起動しています...
python -m streamlit run app.py
pause