@echo off
setlocal

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python not found in PATH.
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm not found in PATH.
  exit /b 1
)

echo Starting InvoiceMind backend on http://127.0.0.1:8000 ...
start "InvoiceMind Backend" cmd /k "cd /d ""%ROOT%"" && python scripts\migrate.py && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

echo Starting InvoiceMind frontend on http://127.0.0.1:3000 ...
start "InvoiceMind Frontend" cmd /k "cd /d ""%ROOT%\frontend"" && npm run dev -- --hostname 127.0.0.1 --port 3000"

echo.
echo InvoiceMind is starting in two windows:
echo - Backend:  http://127.0.0.1:8000
echo - Frontend: http://127.0.0.1:3000

endlocal
