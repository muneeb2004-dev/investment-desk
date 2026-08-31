@echo off
setlocal
cd /d "%~dp0\.."
echo Working directory: %cd%
echo.

REM Run this in a SECOND terminal, after start_backend.bat is already
REM running — the agents call the backend on http://localhost:8000, so
REM the backend has to be up first.

if not exist ".venv" (
    echo ERROR: no .venv found. Run scripts\start_backend.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: failed to activate the virtual environment.
    pause
    exit /b 1
)

if not exist "backend\.env" (
    echo ERROR: backend\.env not found. Run scripts\start_backend.bat first.
    pause
    exit /b 1
)

findstr /b /c:"GOOGLE_API_KEY=" backend\.env >nul
if errorlevel 1 (
    echo ERROR: GOOGLE_API_KEY is not set in backend\.env.
    echo Get a free Gemini API key at https://aistudio.google.com/apikey
    echo — no billing account required — and add it as:
    echo     GOOGLE_API_KEY=your-key-here
    pause
    exit /b 1
)

echo ============================================================
echo  Starting the agent fleet UI on http://localhost:8080
echo.
echo  Open that URL, pick "adk_agents" in the left panel, and
echo  talk to the desk. Leave this window open; Ctrl+C stops it.
echo.
echo  Reminder: enable "Algo Trading" in the MT5 terminal, or
echo  every order comes back retcode 10027.
echo ============================================================
echo.

adk web --port 8080

echo.
echo Agent UI stopped, or failed to start — check for an error above.
pause
