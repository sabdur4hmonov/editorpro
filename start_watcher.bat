@echo off
rem Montaj watcher: Claude chatdan yuborgan topshiriqlarni shu kompyuterda bajaradi.
rem Oyna ochiq turguncha ishlaydi. To'xtatish uchun oynani yoping.
cd /d "%~dp0"
title Montaj watcher
if not exist ".venv\Scripts\python.exe" (
  echo .venv topilmadi. Avval setup.ps1 ni ishga tushiring.
  pause
  exit /b 1
)
:loop
".venv\Scripts\python.exe" scripts\watcher.py
if %errorlevel%==75 (
  echo Watcher yangilandi, qayta ishga tushmoqda...
  goto loop
)
echo.
echo Watcher to'xtadi.
pause
