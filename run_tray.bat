@echo off
title Spotify Ads Mute - System Tray
cd /d "%~dp0"

REM Kiem tra virtual environment
if exist "venv\Scripts\pythonw.exe" (
    echo Dang khoi dong Spotify Ads Mute trong System Tray...
    start "" venv\Scripts\pythonw.exe spotify_ads_mute_tray.py
    echo.
    echo Ung dung da khoi dong trong khay he thong!
    echo Tim icon mau xanh la cay o goc duoi ben phai man hinh.
    echo.
    timeout /t 3
) else (
    echo Loi: Khong tim thay virtual environment!
    echo Hay chay lenh: python -m venv venv
    echo Sau do: venv\Scripts\pip install -r requirements.txt pystray Pillow
    pause
)
