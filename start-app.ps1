$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $projectRoot "backend"
$frontendDir = Join-Path $projectRoot "frontend"
$backendPython = Join-Path $backendDir "venv\Scripts\python.exe"

if (-not (Test-Path $backendPython)) {
    throw "Backend virtual environment not found at '$backendPython'."
}

if (-not (Test-Path (Join-Path $frontendDir "node_modules"))) {
    throw "Frontend dependencies are missing. Run 'yarn install' inside the frontend folder first."
}

$backendCommand = "Set-Location '$backendDir'; & '$backendPython' -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload"
$frontendCommand = "Set-Location '$frontendDir'; yarn start"

Write-Host "Starting backend on http://localhost:8001 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCommand | Out-Null

Write-Host "Starting frontend on http://localhost:3000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCommand | Out-Null

Write-Host ""
Write-Host "Both servers are launching in separate windows." -ForegroundColor Green
Write-Host "Frontend: http://localhost:3000" -ForegroundColor Green
Write-Host "Backend:  http://localhost:8001" -ForegroundColor Green
