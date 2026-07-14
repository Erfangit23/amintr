@echo off
REM ============================================================
REM  XAUUSD AutoTrader — CLEAN FIX (nukes venv, rebuilds from 0)
REM ============================================================
title AutoTrader — Clean Reset
cd /d "%~dp0"

echo ============================================
echo   STEP 1: Kill everything
echo ============================================
taskkill /f /im python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo ============================================
echo   STEP 2: Delete old venv completely
echo ============================================
if exist "venv\" (
    rmdir /s /q "venv"
    echo Old venv removed.
)

echo ============================================
echo   STEP 3: Create fresh venv
echo ============================================
python -m venv venv
call venv\Scripts\activate.bat
python -m pip install --upgrade pip --quiet

echo ============================================
echo   STEP 4: Install numpy 1.x FIRST
echo ============================================
pip install "numpy==1.26.4" --no-cache-dir
echo.
python -c "import numpy; print('NumPy version:', numpy.__version__)"
if %errorlevel% neq 0 (
    echo NUMPY FAILED!
    pause
    exit /b 1
)

echo ============================================
echo   STEP 5: Install MetaTrader5
echo ============================================
pip install MetaTrader5==5.0.45 --no-cache-dir
echo.
python -c "import MetaTrader5 as mt5; print('MT5 version:', mt5.__version__)"
if %errorlevel% neq 0 (
    echo MQL5 FAILED — trying alternative MetaTrader5 install...
    pip install MetaTrader5 --no-cache-dir
    python -c "import MetaTrader5 as mt5; print('MT5 OK')"
    if %errorlevel% neq 0 (
        echo MT5 STILL FAILS. Check if MetaTrader 5 terminal is installed.
        pause
        exit /b 1
    )
)

echo ============================================
echo   STEP 6: Install remaining deps
echo ============================================
pip install telethon==1.36.0 python-telegram-bot==21.6 aiofiles==24.1.0 pytz==2024.1 --no-cache-dir

echo ============================================
echo   STEP 7: Final verification
echo ============================================
python -c "import numpy; import MetaTrader5; print('ALL OK — NumPy', numpy.__version__)"
if %errorlevel% neq 0 (
    echo Something still wrong.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   FIX COMPLETE. Run: run.bat
echo ============================================
pause
