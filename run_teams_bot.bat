@echo off
title Microsoft Teams AE Bot Simulator
cd /d "%~dp0"
echo Starting Teams AE Bot Simulator on http://localhost:8000 ...
python -m uvicorn teams_bot_app.main:app --host 127.0.0.1 --port 8000 --reload
pause
