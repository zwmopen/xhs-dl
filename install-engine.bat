@echo off
chcp 65001 >nul
title xhs-dl Engine Setup
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup-v2.ps1"
pause
