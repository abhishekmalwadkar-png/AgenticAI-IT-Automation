#!/usr/bin/env bash
set -e

echo "======================================================================="
echo "  Microsoft Teams AE Bot Simulator - Production Runner (Linux/macOS)"
echo "======================================================================="

# Ensure working directory is the script root
cd "$(dirname "$0")"

# Verify Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found. Please install Python 3.10+."
    exit 1
fi

# Upgrade pip and install/verify dependencies
echo "[INFO] Verifying and updating runtime dependencies from requirements.txt..."
python3 -m pip install --upgrade pip --quiet
python3 -m pip install -r requirements.txt --quiet

# Check .env file
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "[INFO] Creating .env from .env.example..."
        cp .env.example .env
    fi
fi

# Run production Uvicorn server
echo "[INFO] Starting server on http://0.0.0.0:8000 (Workers: 2)..."
exec uvicorn teams_bot_app.main:app --host 0.0.0.0 --port 8000 --workers 2
