@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -m xhs_dl.cli %*
if errorlevel 1 pause
