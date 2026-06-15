@echo off
chcp 65001 >nul
title IP3
cd /d %~dp0

REM 최초 실행 시 필요한 패키지를 설치합니다.
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo [IP3] 필요한 패키지를 설치합니다...
    python -m pip install -r requirements.txt
)

echo [IP3] 앱을 실행합니다. 브라우저가 자동으로 열립니다.
python -m streamlit run app.py
pause
