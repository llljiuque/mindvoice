# Electron Application Development Startup Script
# Ensure running in the correct directory

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$separator = "========================================"

Write-Host $separator -ForegroundColor Cyan
Write-Host "Starting MindVoice Electron Application" -ForegroundColor Cyan
Write-Host $separator -ForegroundColor Cyan
Write-Host ""
Write-Host "Current directory: $(Get-Location)" -ForegroundColor Yellow
Write-Host ""

# Check dist-electron directory
$mainJsPath = Join-Path $scriptDir "dist-electron\main.js"
if (-not (Test-Path $mainJsPath)) {
    Write-Host "Building Electron main process..." -ForegroundColor Yellow
    npm run build:electron
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Build failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host "Build completed" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "Electron main process already built: $mainJsPath" -ForegroundColor Green
    Write-Host ""
}

# Check node_modules
if (-not (Test-Path "node_modules")) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    npm install
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installation failed!" -ForegroundColor Red
        exit 1
    }
    Write-Host "Installation completed" -ForegroundColor Green
    Write-Host ""
}

# Verify main field in package.json
$packageJson = Get-Content "package.json" | ConvertFrom-Json
Write-Host "package.json main field: $($packageJson.main)" -ForegroundColor Gray
Write-Host ""

# Start development server
Write-Host "Starting development server..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Gray
Write-Host $separator -ForegroundColor Cyan
Write-Host ""

npm run dev
