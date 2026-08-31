@echo off
setlocal
cd /d "%~dp0\.."
echo Working directory: %cd%
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: "python" was not found on PATH.
    echo Install Python 3.11 from python.org, checking "Add python.exe to PATH"
    echo during install, then re-run this script.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: failed to create the virtual environment. See message above.
        pause
        exit /b 1
    )
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: failed to activate the virtual environment.
    pause
    exit /b 1
)

echo Installing/updating dependencies — this can take a few minutes...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: pip install failed — see the message above.
    echo (MetaTrader5 requires 64-bit Python 3.8-3.11; if that line failed,
    echo  you likely have a 32-bit or too-new Python installed.)
    pause
    exit /b 1
)
echo Dependencies installed OK.
echo.

if not exist "backend\.env" (
    echo Creating backend\.env from the template...
    copy backend\.env.example backend\.env >nul
)

echo ============================================================
echo  About to open backend\.env in Notepad.
echo  If it doesn't appear on screen, check your taskbar — it may
echo  have opened BEHIND this window.
echo.
echo  Fill in: MT5_LOGIN, MT5_PASSWORD, MT5_SERVER (your demo
echo  account), and make up any two random strings for
echo  BACKEND_API_KEY and RISK_TOKEN_SECRET.
echo  SAVE THE FILE, then CLOSE Notepad to continue.
echo ============================================================
echo.
pause
start "" /wait notepad "backend\.env"

echo.
echo Notepad closed. Starting backend on http://localhost:8000 ...
echo Leave this window open. Press Ctrl+C to stop the server.
echo.
uvicorn backend.main:app --reload --port 8000

echo.
echo Backend stopped, or failed to start — check for an error above.
pause
