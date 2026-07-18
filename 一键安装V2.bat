@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-v2.ps1"
if errorlevel 1 goto failed
python -m pip install -e "%~dp0"
if errorlevel 1 goto failed
echo.
echo Installation completed. Run the launcher next.
pause
exit /b 0

:failed
echo.
echo Installation failed. See the messages above.
pause
exit /b 1
