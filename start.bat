@echo off
:: Sentinel – Start Script (Windows)
:: Usage: Double-click start.bat or run from Command Prompt

setlocal

set VENV_DIR=.venv
set REQUIREMENTS=requirements.txt

echo.
echo Sentinel Startup
echo ==================
echo.

:: VIRTUAL ENVIRONMENT
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [sentinel] No virtual environment found. Creating one...
    python -m venv %VENV_DIR%
    if errorlevel 1 (
        echo [sentinel] ERROR: Failed to create virtual environment.
        echo            Make sure Python is installed and on your PATH.
        pause
        exit /b 1
    )
    echo [sentinel] Virtual environment created at %VENV_DIR%

    echo [sentinel] Installing requirements...
    call "%VENV_DIR%\Scripts\pip.exe" install --upgrade pip -q
    call "%VENV_DIR%\Scripts\pip.exe" install -r %REQUIREMENTS% -q
    if errorlevel 1 (
        echo [sentinel] ERROR: Failed to install requirements.
        pause
        exit /b 1
    )
    echo [sentinel] Requirements installed.
) else (
    echo [sentinel] Virtual environment found at %VENV_DIR%
)

:: Activate the virtual environment
call "%VENV_DIR%\Scripts\activate.bat"
echo [sentinel] Virtual environment activated.
echo.

:: START SERVICES
echo [sentinel] Starting API (port 8000)...
start "Sentinel API" cmd /k "call %VENV_DIR%\Scripts\activate.bat && uvicorn sentinel_api:app --port 8000 --log-level warning"

timeout /t 2 /nobreak >nul

echo [sentinel] Starting detection pipeline...
start "Sentinel Detect" cmd /k "call %VENV_DIR%\Scripts\activate.bat && python sentinel_detect.py"

timeout /t 1 /nobreak >nul

echo [sentinel] Starting Streamlit dashboard...
start "Sentinel Dashboard" cmd /k "call %VENV_DIR%\Scripts\activate.bat && streamlit run sentinel.py"

echo.
echo +---------------------------------------------+
echo ^|  All services running in separate windows.  ^|
echo ^|  Close each window to stop that service.    ^|
echo ^|  Or close all three to stop everything.     ^|
echo +---------------------------------------------+
echo.

call "%VENV_DIR%\Scripts\deactivate.bat" 2>nul

pause