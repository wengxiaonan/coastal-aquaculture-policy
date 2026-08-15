@echo off
chcp 65001 >nul
cd /d "f:\deepseek harness"
echo 正在启动 CARSI 论文下载脚本...
echo.
py -3.13 carsi_download.py
echo.
echo ============================================
echo 脚本已结束。按任意键关闭此窗口...
pause >nul
