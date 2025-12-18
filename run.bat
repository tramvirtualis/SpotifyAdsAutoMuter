@echo off
title Spotify Ads Mute
cd /d "%~dp0"

REM Kiem tra virtual environment
if exist "venv\Scripts\python.exe" (
    echo Dang su dung virtual environment...
    venv\Scripts\python.exe spotify_ads_mute.py
) else (
    echo Dang su dung Python he thong...
    python spotify_ads_mute.py
)

pause
