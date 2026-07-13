@echo off
title XAUUSD AutoTrader
cd /d "%~dp0src"
call ..\venv\Scripts\activate.bat
python main.py
pause
