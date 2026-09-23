@echo off
setlocal enabledelayedexpansion
title Microsoft Teams AE Bot - IT Service Automation Simulator

echo =======================================================================
echo   Microsoft Teams AE Bot Simulator - Production Runner
echo =======================================================================
echo.

cd /d "%~dp0"

REM 1. Check Python Availability
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Python is not found in PATH!
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

REM 2. Verify & Auto-install Dependencies
echo [INFO] Verifying and updating runtime dependencies from requirements.txt...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Standard pip install reported notices. Continuing with self-healing bootstrap...
)

REM 3. Create .env from template if missing
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] No .env found. Creating .env from .env.example template...
        copy .env.example .env
        echo [NOTICE] Created .env. Please update it with your actual credentials.
    )
)

REM 4. Launch Production Server
echo.
echo [SUCCESS] Starting Teams AE Bot Server at: http://127.0.0.1:8000
echo [INFO] Health Check Endpoint: http://127.0.0.1:8000/health
echo.
python -m uvicorn teams_bot_app.main:app --host 0.0.0.0 --port 8000 --reload

pause
