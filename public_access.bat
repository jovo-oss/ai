@echo off
setlocal enabledelayedexpansion

title AI Chat System - Public Access

echo ========================================
echo   AI Chat System - Public Access
echo ========================================
echo.

:: Check Node.js
echo [*] Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found
    echo Please install Node.js from https://nodejs.org/
    echo.
    pause
    exit /b 1
)
echo [OK] Node.js found

echo.
echo [*] Checking localtunnel...
where lt >nul 2>&1
if errorlevel 1 (
    echo [*] localtunnel not found, installing...
    call npm install -g localtunnel
    if errorlevel 1 (
        echo [ERROR] Failed to install localtunnel
        echo Please run: npm install -g localtunnel
        echo.
        pause
        exit /b 1
    )
    echo [OK] localtunnel installed
) else (
    echo [OK] localtunnel found
)

echo.
echo [*] Starting backend service (includes frontend)...

:: Get the script directory
set PROJECT_DIR=%~dp0

:: Start backend (port 8000, includes frontend)
echo [*] Starting backend on port 8000...
start /MIN cmd /c "cd /d "%PROJECT_DIR%backend" && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
python -c "import time; time.sleep(3)"
echo [OK] Backend started

echo.
echo [OK] Service started on port 8000
echo.
echo [*] Creating public tunnel...
echo.
echo [*] Please wait for the URL to appear...
echo.
echo ========================================
echo   The public URL will be shown below
echo   Keep this window open
echo ========================================
echo.

:: Create tunnel for backend (port 8000, includes frontend)
lt --port 8000

echo.
echo ========================================
echo   If tunnel stopped, restart this script
echo ========================================
pause
