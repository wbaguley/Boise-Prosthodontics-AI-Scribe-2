# Diagnose Connection Issues
Write-Host "🔍 Diagnosing Connection Issues..." -ForegroundColor Cyan
Write-Host ""

# Test 1: Is Ollama running?
Write-Host "1. Testing Ollama at localhost:11434..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 3
    Write-Host "✅ Ollama IS running" -ForegroundColor Green
    Write-Host $response.Content
} catch {
    Write-Host "❌ Ollama is NOT running" -ForegroundColor Red
    Write-Host "Start it with: ollama serve" -ForegroundColor Yellow
}

Write-Host ""

# Test 2: Is Backend running?
Write-Host "2. Testing Backend at localhost:3051..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3051/health" -TimeoutSec 3
    Write-Host "✅ Backend IS running" -ForegroundColor Green
    Write-Host $response.Content
} catch {
    Write-Host "✅ Backend is responding at 127.0.0.1:3051" -ForegroundColor Green
} catch {
    Write-Host "❌ Backend is NOT responding at 127.0.0.1:3051" -ForegroundColor Red
}

Write-Host ""

# Test 3: Try alternative backend address
Write-Host "3. Testing Backend at 127.0.0.1:3051..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:3051/health" -TimeoutSec 3
    Write-Host "✅ Backend responds to 127.0.0.1" -ForegroundColor Green
} catch {
    Write-Host "❌ Backend is NOT responding at 127.0.0.1:3051" -ForegroundColor Red
}

Write-Host ""

# Test 4: Is Frontend running?
Write-Host "4. Testing Frontend at localhost:3000..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 3
    Write-Host "✅ Frontend IS running" -ForegroundColor Green
} catch {
    Write-Host "❌ Frontend is NOT running" -ForegroundColor Red
}

Write-Host ""

# Test 5: Check what's listening on port 3051
Write-Host "5. Checking what is listening on port 3051..." -ForegroundColor Yellow
netstat -ano | Select-String ":3051"

Write-Host ""
Write-Host "====================================" -ForegroundColor Cyan
Write-Host "Diagnosis Complete!" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan