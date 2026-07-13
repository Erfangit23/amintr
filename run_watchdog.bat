@echo off
REM ============================================================
REM  XAUUSD AutoTrader — 24/7 Watchdog Launcher
REM  Restarts the bot if it ever crashes or exits
REM  Use THIS as your startup entry point for max reliability
REM ============================================================
title XAUUSD AutoTrader Watchdog
cd /d "%~dp0"

:LOOP
echo [%date% %time%] Watchdog: Starting AutoTrader...
echo [%date% %time%] Watchdog: Starting AutoTrader... >> src\logs\watchdog.log

REM Activate venv and run
call venv\Scripts\activate.bat
python src\main.py

echo [%date% %time%] Watchdog: Bot exited with code %errorlevel% — restarting in 10s...
echo [%date% %time%] Watchdog: Bot exited with code %errorlevel% — restarting in 10s... >> src\logs\watchdog.log

REM Wait 10 seconds before restart
timeout /t 10 /nobreak >nul

goto LOOP
