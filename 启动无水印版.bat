@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not "%~1"=="" goto run_args
echo.
echo 小红书无水印下载器 V2
set /p "XHS_SHARE=请粘贴分享文本或链接，然后按回车: "
if not defined XHS_SHARE goto end
python -m xhs_dl.cli "%XHS_SHARE%"
pause
goto end

:run_args
python -m xhs_dl.cli %*
if errorlevel 1 pause

:end
