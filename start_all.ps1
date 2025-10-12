# Start both backend and frontend for local development
param(
  [int]$BackendPort = 8000,
  [int]$FrontendPort = 3000,
  [string]$ApiUrl
)

if (-not $ApiUrl -or $ApiUrl -eq "") {
  $ApiUrl = "http://localhost:$BackendPort/api/v1"
}

# Do not set secrets here; rely on existing environment or .env loaded by backend

Write-Host "[start_all] Backend -> http://localhost:$BackendPort" -ForegroundColor Cyan
Write-Host "[start_all] Frontend -> http://localhost:$FrontendPort (proxying API $ApiUrl)" -ForegroundColor Cyan

# Start backend in a new PowerShell window (uses existing start_backend.ps1)
$backendScript = Join-Path $PSScriptRoot "start_backend.ps1"
if (-not (Test-Path $backendScript)) {
  Write-Host "[start_all] ERROR: start_backend.ps1 not found at $backendScript" -ForegroundColor Red
  exit 1
}

Start-Process -WindowStyle Minimized -FilePath "powershell" -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "`"$backendScript`"")

# Start frontend in this window
Push-Location (Join-Path $PSScriptRoot "frontend")
try {
  if (-not (Test-Path "node_modules")) {
    Write-Host "[start_all] Installing frontend dependencies..." -ForegroundColor Yellow
    npm install
  }
  $env:PORT = "$FrontendPort"
  $env:REACT_APP_API_URL = $ApiUrl
  Write-Host "[start_all] Starting React dev server on port $FrontendPort ..." -ForegroundColor Green
  npm start
} finally {
  Pop-Location
}
