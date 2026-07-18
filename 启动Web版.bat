@echo off
chcp 65001 >nul
title xhs-dl 小红书笔记下载器 (Web)
cd /d "D:\AICode\xhs-dl"
echo.
echo   xhs-dl Web 服务启动中...
echo   浏览器将自动打开 http://127.0.0.1:5678
echo   关闭此窗口可停止服务
echo.
python -m xhs_dl.web.app
pause
