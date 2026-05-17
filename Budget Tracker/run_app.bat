@echo off
SETLOCAL EnableDelayedExpansion

echo ========================================
echo   Expense Tracker Setup ^& Launcher
echo ========================================

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b
)

:: Define Project Directory
SET "PROJECT_DIR=%~dp0"
cd /d "%PROJECT_DIR%"

:: Create Virtual Environment if it doesn't exist
if not exist "venv" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)

:: Activate Virtual Environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate

:: Install/Update Dependencies
echo [INFO] Checking dependencies...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

:: Launch Streamlit
echo [INFO] Launching Expense Tracker...
streamlit run main.py

echo [INFO] Application closed.
pause
