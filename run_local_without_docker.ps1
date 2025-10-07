# Run Boise Prosthodontics AI Scribe WITHOUT Docker
# Save this as run_local_without_docker.ps1
Write-Host "🏥 Starting Boise Prosthodontics AI Scribe (No Docker)" -ForegroundColor Cyan
Write-Host ""

# Set UTF-8 encoding for Python
$env:PYTHONIOENCODING = "utf-8"

# Navigate to project root
$ProjectRoot = "C:\Users\GTM_PLANETARY_RIG 1\Desktop\Boise Prosthodontics AI Scribe\Boise-Prosthodontics-AI-Scribe"
Set-Location $ProjectRoot

Write-Host "Step 1: Starting Ollama locally..." -ForegroundColor Yellow

# Check if Ollama is installed
try {
    ollama --version
    Write-Host "✅ Ollama is installed" -ForegroundColor Green
    
    # Start Ollama serve in background
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 5

    # Test Ollama
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "✅ Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Ollama not installed or not running" -ForegroundColor Red
    Write-Host "Download from: https://ollama.ai/download" -ForegroundColor Yellow
    Write-Host ""
    $continue = Read-Host "Continue without Ollama? (y/n)"
    if ($continue -ne "y") {
        exit 1
    }
}

Write-Host ""
Write-Host "Step 2: Starting Backend..." -ForegroundColor Yellow

# Set environment variables for backend
$env:OLLAMA_HOST = "http://localhost:11434"
$env:WHISPER_MODEL = "tiny"

# Start backend in new window
$backendPath = Join-Path $ProjectRoot "backend"
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$backendPath'; `$env:PYTHONIOENCODING='utf-8'; `$env:OLLAMA_HOST='http://localhost:11434'; & 'C:/Users/GTM_PLANETARY_RIG 1/AppData/Local/Programs/Python/Python313/python.exe' main.py"
) -WindowStyle Normal

Write-Host "✅ Backend starting in new window..." -ForegroundColor Green
Start-Sleep -Seconds 5

Write-Host ""
Write-Host "Step 3: Starting Frontend..." -ForegroundColor Yellow

# Start frontend in new window
$frontendPath = Join-Path $ProjectRoot "frontend"
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$frontendPath'; npm start"
) -WindowStyle Normal

Write-Host "✅ Frontend starting in new window..." -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✨ Services Starting!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Wait 30 seconds, then open:" -ForegroundColor Yellow
Write-Host "📱 http://localhost:3000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to close this window..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")