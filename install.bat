@echo off
chcp 65001 >nul 2>nul
title AI TTRPG Simulator - Install

echo ============================================
echo   AI TTRPG Simulator - Environment Setup
echo ============================================
echo.

:: ---- Check Python ----
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install Python 3.10+ and add to PATH.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b 1
)

:: ---- Check Node.js ----
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Install Node.js 18+ and add to PATH.
    echo Download: https://nodejs.org/
    pause
    exit /b 1
)

echo [1/5] Creating Python virtual environment...
cd /d "%~dp0backend"
if not exist "venv" (
    python -m venv venv
    echo       venv created.
) else (
    echo       venv already exists, skipping.
)

echo.
echo [2/5] Installing Python dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Python dependency installation failed.
    pause
    exit /b 1
)
echo       Python dependencies installed.

echo.
echo [3/5] Installing frontend dependencies...
cd /d "%~dp0frontend"
call npm install --silent
if %errorlevel% neq 0 (
    echo [ERROR] Frontend dependency installation failed.
    pause
    exit /b 1
)
echo       Frontend dependencies installed.

echo.
echo [4/5] Creating data directories...
cd /d "%~dp0backend"
if not exist "data" mkdir data
if not exist "data\uploads" mkdir data\uploads
if not exist "data\chroma" mkdir data\chroma
if not exist "data\skills" mkdir data\skills
if not exist "data\characters" mkdir data\characters
echo       Data directories ready.

echo.
echo [5/5] PF2e data import (optional)...
if defined FVTT_PF2E_PACKS (
    echo       Indexing PF2e character builder data...
    cd /d "%~dp0backend"
    call venv\Scripts\activate.bat
    python -m app.systems.pf2e.ingest.ingest_charbuilder "%FVTT_PF2E_PACKS%"
    if %errorlevel% neq 0 (
        echo [WARN] Character builder indexing failed.
    ) else (
        echo       Character builder data indexed.
    )
) else (
    echo       [SKIP] Set FVTT_PF2E_PACKS to auto-import PF2e data.
)

if defined FVTT_PF2E_TRANSLATIONS (
    echo       Merging Chinese translations...
    python -m app.systems.pf2e.ingest.translations "%FVTT_PF2E_TRANSLATIONS%"
    if %errorlevel% neq 0 (
        echo [WARN] Translation merge failed.
    ) else (
        echo       Chinese translations merged.
    )
) else (
    echo       [SKIP] Set FVTT_PF2E_TRANSLATIONS to auto-merge CN translations.
)

echo.
echo ============================================
echo   Installation complete!
echo.
echo   Next steps:
echo     1. (Optional) Run ingest_rules.bat to import PF2e rules
echo     2. Run start.bat to start services
echo     3. Open http://localhost:3000 to configure API Key
echo.
echo   Daggerheart and SWADE data is built-in.
echo   PF2e requires external FVTT data — run ingest_rules.bat when ready.
echo ============================================
pause
