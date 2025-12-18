@echo off
title Build Spotify Ads Mute EXE
cd /d "%~dp0"

echo ============================================
echo   DANG DONG GOI SPOTIFY ADS MUTE THANH EXE
echo ============================================
echo.

REM Kiem tra virtual environment
if not exist "venv\Scripts\pyinstaller.exe" (
    echo Dang cai dat PyInstaller...
    venv\Scripts\pip.exe install pyinstaller
)

echo.
echo Dang tao file EXE...
echo.

venv\Scripts\pyinstaller.exe --onefile --windowed --name "SpotifyAdsMute" --icon=icon.ico spotify_ads_mute_tray.py

echo.
echo ============================================
echo   HOAN TAT!
echo ============================================
echo.
echo File EXE da duoc tao tai:
echo   dist\SpotifyAdsMute.exe
echo.
echo Ban co the copy file nay ra Desktop de su dung.
echo.
pause
