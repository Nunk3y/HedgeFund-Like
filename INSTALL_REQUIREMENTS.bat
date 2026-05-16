@echo off
title Install Tech Stock Screener
cd /d "%~dp0"
python -m venv .venv
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo Install complete.
pause
