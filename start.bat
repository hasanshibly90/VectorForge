@echo off
title VectorForge - Starting...

echo ============================================
echo   VectorForge - Raster to Vector SaaS
echo ============================================
echo.

:: Kill any existing processes on ports 8000 and 5173
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do taskkill /F /PID %%a >nul 2>&1

:: Start backend
echo [1/2] Starting Backend (FastAPI on :8000)...
start "VectorForge Backend" cmd /k "cd /d "%~dp0backend" && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

:: Wait for backend to be ready
timeout /t 4 /nobreak >nul

:: Start frontend
echo [2/2] Starting Frontend (Vite on :5173)...
start "VectorForge Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

timeout /t 3 /nobreak >nul

echo.
echo ============================================
echo   VectorForge is running!
echo.
echo   Frontend:  http://localhost:5173
echo   API Docs:  http://localhost:8000/docs
echo   Health:    http://localhost:8000/health
echo ============================================
echo.
echo   Close the two terminal windows to stop.
echo.
pause
