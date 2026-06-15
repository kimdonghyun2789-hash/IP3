@echo off
chcp 65001 >nul
title Build IP3 EXE
cd /d "%~dp0"

set "PYEXE=python"
where py >nul 2>nul && set "PYEXE=py"

%PYEXE% -m pip install --upgrade pip
%PYEXE% -m pip install -r requirements.txt
%PYEXE% -m pip install pyinstaller

%PYEXE% -m PyInstaller ^
  --noconfirm ^
  --onefile ^
  --name IP3 ^
  --collect-all streamlit ^
  --collect-all altair ^
  app_launcher.py

echo.
echo [IP3] Build done. The executable is at dist\IP3.exe
echo [IP3] Keep IP3.exe next to the source folders (app.py, pages, components, ...).
pause
