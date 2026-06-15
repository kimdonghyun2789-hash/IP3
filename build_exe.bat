@echo off
chcp 65001 >nul
title Build IP3 EXE
cd /d %~dp0

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller

pyinstaller ^
  --noconfirm ^
  --onefile ^
  --name IP3 ^
  --collect-all streamlit ^
  --collect-all altair ^
  app_launcher.py

echo.
echo [IP3] 빌드가 끝나면 dist\IP3.exe 가 생성됩니다.
echo [IP3] 실행 시 app.py, pages, components 등 소스 폴더가 함께 있어야 합니다.
pause
