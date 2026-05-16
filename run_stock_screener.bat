@echo off
setlocal

REM Always launch from the folder where this .bat file lives.
REM This prevents old shortcuts or current-directory issues from opening the wrong app copy.
cd /d "%~dp0"

echo Starting Tech Stock Screener from:
echo %CD%
echo.

python main.py

if errorlevel 1 (
    echo.
    echo App exited with an error.
    pause
)
