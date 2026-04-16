@echo off
TITLE Telegram Debt Bot - Auto Setup

echo [DEBUG] Script started...
pause

:: Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python at https://www.python.org/
    pause
    exit /b
)

:: Check and create venv
if not exist "venv" (
    echo [INFO] Creating virtual environment (venv)...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b
    )
    echo [INFO] Successfully created venv.
)

:: Activate venv and install dependencies
echo [INFO] Activating virtual environment...
call venv\Scripts\activate

echo [INFO] Checking and installing requirements...
python -m pip install --upgrade pip
pip install -r requirements.txt

:: Check config.json
if not exist "config.json" (
    if exist "config.json.example" (
        echo [WARNING] config.json not found. Creating from example...
        copy config.json.example config.json
        echo [IMPORTANT] Please open config.json and fill in your BOT_TOKEN!
        notepad config.json
    ) else (
        echo [ERROR] Missing config.json and config.json.example!
    )
)

:: Run bot
echo [INFO] Starting Bot...
python bot.py

echo.
echo Bot stopped.
pause
