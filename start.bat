@echo off
:: Sentinel – Start Script (Windows)
:: Runs sentinel_detect.py and sentinel.py concurrently.
:: Usage: Double-click start.bat or run from Command Prompt

echo.
echo Sentinel Startup
echo.

echo [sentinel] Starting detection pipeline...
start "Sentinel Detect" cmd /k "python sentinel_detect.py"

:: Small delay so detect can connect to DB before Streamlit opens
timeout /t 2 /nobreak >nul

echo [sentinel] Starting Streamlit dashboard...
start "Sentinel Dashboard" cmd /k "streamlit run sentinel.py"

echo.
echo [sentinel] Both services running in separate windows.
echo [sentinel] Close those windows to stop each service.
echo.
pause