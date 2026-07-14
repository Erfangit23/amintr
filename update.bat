@echo off
title XAUUSD AutoTrader — Update
echo ============================================
echo   XAUUSD AutoTrader — Pull & Update
echo ============================================
cd /d "%~dp0"

echo Stopping any running bot...
taskkill /f /im python.exe >nul 2>&1
timeout /t 3 /nobreak >nul

echo.
echo Pulling latest from GitHub...
git pull

echo.
echo Updating Python dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt -q

echo.
echo ============================================
echo   Done! Restart the bot with run_watchdog.bat
echo ============================================
pause
