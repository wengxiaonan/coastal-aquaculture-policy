@echo off
chcp 65001 >nul
cd /d "f:\deepseek harness"
echo Starting CARSI paper downloader...
echo.
py -3.13 carsi_download.py
echo.
echo ============================================
echo Script finished. Press any key to close...
pause >nul
