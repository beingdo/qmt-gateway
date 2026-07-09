# QMT Gateway Startup Script for Windows
# Usage: .\start_gateway.ps1

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "Starting QMT Gateway..." -ForegroundColor Cyan
Write-Host "Ensure XtMiniQmt.exe is already running and logged in!" -ForegroundColor Yellow
Write-Host ""

# Try multiple paths
$PossiblePaths = @(
    "C:\国金证券QMT交易端\bin.x64\python.exe",
    "C:\Program Files\Sinolink Securities\QMT\bin.x64\python.exe"
)

$PythonPath = $null
foreach ($path in $PossiblePaths) {
    if (Test-Path $path) {
        $PythonPath = $path
        break
    }
}

if (-not $PythonPath) {
    Write-Host "ERROR: Python not found in any expected location:" -ForegroundColor Red
    foreach ($path in $PossiblePaths) {
        Write-Host "  - $path" -ForegroundColor Red
    }
    Write-Host ""
    Write-Host "Please check QMT installation path." -ForegroundColor Yellow
    exit 1
}

$GatewayScript = Join-Path $PSScriptRoot "gateway.py"

if (-not (Test-Path $GatewayScript)) {
    Write-Host "ERROR: gateway.py not found at $GatewayScript" -ForegroundColor Red
    exit 1
}

Write-Host "Python found: $PythonPath" -ForegroundColor Green
Write-Host "Gateway: $GatewayScript" -ForegroundColor Green
Write-Host "Starting service on http://0.0.0.0:8888" -ForegroundColor Cyan
Write-Host ""

& $PythonPath $GatewayScript
