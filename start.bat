@echo off
chcp 65001 >nul 2>nul
title AI TTRPG Simulator - Start

echo ============================================
echo   AI TTRPG Simulator - Starting
echo ============================================
echo.

:: ---- Check venv ----
if not exist "%~dp0backend\venv\Scripts\activate.bat" (
    echo [ERROR] Python venv not found. Run install.bat first.
    pause
    exit /b 1
)

:: ---- Check node_modules ----
if not exist "%~dp0frontend\node_modules" (
    echo [ERROR] Frontend deps not found. Run install.bat first.
    pause
    exit /b 1
)

echo [1/3] Starting backend (FastAPI, port 8000)...
start "TTRPG-Backend" cmd /k "cd /d "%~dp0backend" && call venv\Scripts\activate.bat && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

:: Wait for backend
timeout /t 3 /nobreak >nul

echo [2/3] Starting debug dashboard (port 8001)...
start "TTRPG-Debug" cmd /k "cd /d "%~dp0backend" && call venv\Scripts\activate.bat && python debug_server.py"

:: Wait for debug server
timeout /t 2 /nobreak >nul

echo [3/3] Starting frontend (Next.js, port 3000)...
start "TTRPG-Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

:: Wait for frontend
timeout /t 5 /nobreak >nul

echo.
echo ============================================
echo   All services started!
echo.
echo   Frontend:   http://localhost:3000
echo   Backend:    http://localhost:8000
echo   Debug:      http://localhost:8001
echo   API docs:   http://localhost:8000/docs
echo.
echo   First time? Visit http://localhost:3000/settings
echo   to set your API Key and model name.
echo.
echo   Closing this window won't stop the services.
echo   To stop: run stop.bat or close the
echo   TTRPG-Backend, TTRPG-Frontend and
echo   TTRPG-Debug windows.
echo ============================================

:: Auto-open browser
timeout /t 2 /nobreak >nul
start http://localhost:3000
start http://localhost:8001

pause
