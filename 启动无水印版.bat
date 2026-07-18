@echo off
chcp 65001 >nul
cd /d "%~dp0"
if "%~1"=="" goto interactive
python -m xhs_dl.cli %*
if errorlevel 1 pause
goto end

:interactive
python -m xhs_dl.cli
pause

:end
