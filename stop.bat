@echo off
chcp 65001 >nul 2>nul
title AI TTRPG Simulator - Stop

echo ============================================
echo   AI TTRPG Simulator - Stopping services
echo ============================================
echo.

echo Stopping backend (uvicorn)...
taskkill /f /fi "WINDOWTITLE eq TTRPG-Backend*" >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)

echo Stopping debug dashboard...
taskkill /f /fi "WINDOWTITLE eq TTRPG-Debug*" >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8001" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)

echo Stopping frontend (next dev)...
taskkill /f /fi "WINDOWTITLE eq TTRPG-Frontend*" >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000" ^| findstr "LISTENING"') do (
    taskkill /f /pid %%a >nul 2>&1
)

echo.
echo All services stopped.
timeout /t 2 /nobreak >nul
