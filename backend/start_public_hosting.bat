@echo off
title Events Booking - Public Live Host
cls
echo ===========================================================================
echo   STARTING EVENTS BOOKING & CLOUDFLARE PUBLIC LIVE HOST
echo ===========================================================================
echo.

:: Detect Python interpreter (.venv preferred, fallback to system python)
if exist ".venv\Scripts\python.exe" (
    set "PY_EXEC=.venv\Scripts\python.exe"
    echo Using Virtual Environment Python: %PY_EXEC%
) else (
    set "PY_EXEC=python"
    echo Using System Python: %PY_EXEC%
)

:: Check and download cloudflared if missing
if not exist "cloudflared.exe" (
    echo.
    echo Cloudflare Tunnel binary not found. Downloading cloudflared.exe...
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; (New-Object Net.WebClient).DownloadFile('https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe', 'cloudflared.exe')"
    if exist "cloudflared.exe" (
        echo [OK] cloudflared.exe downloaded successfully.
    ) else (
        echo [ERROR] Failed to download cloudflared.exe. Please check your internet connection.
        pause
        exit /b 1
    )
)

echo.
echo [1/2] Launching Backend Server on http://127.0.0.1:5000...
start "EMS Server Backend" cmd /k "%PY_EXEC% app.py"

echo [2/2] Initializing Cloudflare Tunnel (Please wait 3-5 seconds)...
timeout /t 3 /nobreak >nul

echo.
echo ===========================================================================
echo   YOUR LIVE PUBLIC URL WILL APPEAR BELOW:
echo   (Look for the URL ending with .trycloudflare.com)
echo ===========================================================================
echo.
.\cloudflared.exe tunnel --url http://127.0.0.1:5000
pause
