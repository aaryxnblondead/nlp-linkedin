@echo off
setlocal
REM Start both backend and frontend for local development
REM Usage: start_all.cmd [BACKEND_PORT] [FRONTEND_PORT]

set BACKEND_PORT=%1
if "%BACKEND_PORT%"=="" set BACKEND_PORT=8000
set FRONTEND_PORT=%2
if "%FRONTEND_PORT%"=="" set FRONTEND_PORT=3000

set API_URL=http://localhost:%BACKEND_PORT%/api/v1

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_all.ps1" -BackendPort %BACKEND_PORT% -FrontendPort %FRONTEND_PORT% -ApiUrl %API_URL%

endlocal
