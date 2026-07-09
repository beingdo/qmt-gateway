# QMT Gateway Startup Script for Windows
# Usage: .\start_gateway.ps1

Write-Host "Starting QMT Gateway..."
Write-Host "Ensure XtMiniQmt.exe is already running and logged in!"
Write-Host ""

$PythonPath = "C:\国金证券QMT交易端\bin.x64\python.exe"
$GatewayScript = Join-Path $PSScriptRoot "gateway.py"

if (-not (Test-Path $PythonPath)) {
    Write-Host "ERROR: Python not found at $PythonPath" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $GatewayScript)) {
    Write-Host "ERROR: gateway.py not found at $GatewayScript" -ForegroundColor Red
    exit 1
}

Write-Host "Python: $PythonPath" -ForegroundColor Green
Write-Host "Gateway: $GatewayScript" -ForegroundColor Green
Write-Host "Starting service on http://0.0.0.0:8888" -ForegroundColor Cyan
Write-Host ""

& $PythonPath $GatewayScript
