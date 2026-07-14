@echo off
REM ============================================================
REM  XAUUSD AutoTrader — 24/7 Watchdog Launcher
REM  Restarts the bot if it ever crashes or exits
REM  Use THIS as your startup entry point for max reliability
REM ============================================================
title XAUUSD AutoTrader Watchdog

:LOOP
echo [%date% %time%] Watchdog: Starting AutoTrader...
echo [%date% %time%] Watchdog: Starting AutoTrader... >> "%~dp0src\logs\watchdog.log"

"%~dp0venv\Scripts\python.exe" "%~dp0src\main.py"

echo [%date% %time%] Watchdog: Bot exited — restarting in 10s...
echo [%date% %time%] Watchdog: Bot exited — restarting in 10s... >> "%~dp0src\logs\watchdog.log"

timeout /t 10 /nobreak >nul
goto LOOP
