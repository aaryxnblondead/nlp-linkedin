@echo off
setlocal
REM One-click Windows deploy using docker compose (production)

if not exist ".env.production" (
  echo [deploy] ERROR: .env.production not found at %cd%.
  echo Copy .env.production.example to .env.production and fill in secrets, then rerun.
  exit /b 1
)

where docker >nul 2>nul
if errorlevel 1 (
  echo [deploy] ERROR: Docker not found in PATH. Install Docker Desktop and retry.
  exit /b 1
)

echo [deploy] Building images...
docker compose -f docker-compose.prod.yml --env-file .env.production build
if errorlevel 1 (
  echo [deploy] ERROR: Build failed.
  exit /b 1
)

echo [deploy] Starting services...
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
if errorlevel 1 (
  echo [deploy] ERROR: Services failed to start.
  exit /b 1
)

echo [deploy] Stack is up. Open http://localhost/ (or your IP) in a browser.
echo [deploy] Check logs: docker compose -f docker-compose.prod.yml logs -f backend
endlocal
