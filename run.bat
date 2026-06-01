@echo off
title Process Sync Simulator

echo.
echo  ================================================
echo   Process Sync Simulator
echo  ================================================
echo.

:: Check venv exists, rebuild if missing
if not exist "%~dp0venv\Scripts\python.exe" (
    echo [SETUP] Virtual environment not found. Creating...
    python -m venv "%~dp0venv"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        echo         Make sure Python 3.x is installed and on your PATH.
        pause
        exit /b 1
    )
    echo [SETUP] Installing dependencies...
    "%~dp0venv\Scripts\pip" install -r "%~dp0requirements.txt" --quiet
    if errorlevel 1 (
        echo [ERROR] pip install failed. Check requirements.txt and your internet connection.
        pause
        exit /b 1
    )
    echo [SETUP] Done.
    echo.
)

:: Start Flask in background
echo [START] Starting Flask server on http://127.0.0.1:5000 ...
start "" /B "%~dp0venv\Scripts\python.exe" "%~dp0app.py"

:: Wait 2 seconds then open browser
echo [WAIT]  Opening browser in 2 seconds...
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:5000"

echo [READY] Server is running. Close this window to stop.
echo.
echo  Press Ctrl+C or close this window to shut down the server.
echo.

:: Keep window open so Flask stays alive
"%~dp0venv\Scripts\python.exe" "%~dp0app.py"
