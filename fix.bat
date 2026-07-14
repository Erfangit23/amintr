@echo off
REM ============================================================
REM  XAUUSD AutoTrader — Fix NumPy / MetaTrader5
REM  Run this ONCE on the VPS, then never again
REM ============================================================
title XAUUSD AutoTrader — Fix
cd /d "%~dp0"

echo Stopping any running bot...
taskkill /f /im python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo.
echo Step 1/3: Installing locked NumPy 1.x...
call venv\Scripts\activate.bat
pip install "numpy==1.26.4" --force-reinstall --no-cache-dir

echo.
echo Step 2/3: Reinstalling MetaTrader5 (now compiled against NumPy 1.x)...
pip install MetaTrader5==5.0.45 --force-reinstall --no-cache-dir

echo.
echo Step 3/3: Verifying...
python -c "import numpy; print('NumPy:', numpy.__version__); import MetaTrader5; print('MT5: OK')"

echo.
echo ============================================
echo   Fix complete! Now run: run.bat
echo ============================================
pause
