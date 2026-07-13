@echo off
title XAUUSD AutoTrader — Setup
echo ============================================
echo   XAUUSD AutoTrader — First-Time Setup
echo ============================================
echo.
cd /d "%~dp0"

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install Python 3.11+ from python.org
    pause
    exit /b 1
)
echo [OK] Python found

:: Create venv
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat

:: Upgrade pip
python -m pip install --upgrade pip -q

:: Install deps
echo Installing dependencies...
pip install -r requirements.txt

echo.
echo ============================================
echo   Setup complete!
echo.
echo   1. Edit src\config.json with your settings
echo   2. Run: run.bat
echo ============================================
pause
