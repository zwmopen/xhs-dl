@echo off
chcp 65001 >nul
title xhs-dl V2 Web
cd /d "%~dp0"
echo.
echo   Starting xhs-dl V2 Web...
echo   Browser URL: http://127.0.0.1:5678
echo   Close this window to stop the service.
echo.
python -m xhs_dl.web.app
pause
