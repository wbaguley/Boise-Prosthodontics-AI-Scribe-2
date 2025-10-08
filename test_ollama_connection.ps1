#!/usr/bin/env pwsh

Write-Host "Testing Ollama Connection..." -ForegroundColor Yellow
Write-Host ""

# Test from host machine
Write-Host "1. Testing from host machine (localhost:11434):" -ForegroundColor Blue
try {
    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -Method Get -TimeoutSec 5
    Write-Host "✅ Successfully connected to localhost:11434" -ForegroundColor Green
    Write-Host "Available models:" -ForegroundColor Green
    $response.models | ForEach-Object { Write-Host "  - $($_.name)" -ForegroundColor Green }
} catch {
    Write-Host "❌ Cannot connect to localhost:11434" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "2. Checking Ollama container status:" -ForegroundColor Blue
try {
    $containers = docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | Select-String "ollama"
    if ($containers) {
        Write-Host $containers -ForegroundColor Green
    } else {
        Write-Host "❌ No Ollama container found running" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ Docker command failed" -ForegroundColor Red
}

Write-Host ""
Write-Host "3. Testing backend health endpoint:" -ForegroundColor Blue
try {
    $healthResponse = Invoke-RestMethod -Uri "http://localhost:3051/health" -Method Get -TimeoutSec 5
    Write-Host "✅ Backend health check successful" -ForegroundColor Green
    Write-Host "Ollama status: $($healthResponse.ollama)" -ForegroundColor $(if ($healthResponse.ollama -eq "healthy") { "Green" } else { "Red" })
    Write-Host "Whisper status: $($healthResponse.whisper)" -ForegroundColor Green
} catch {
    Write-Host "❌ Cannot connect to backend at localhost:3051" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "4. Docker compose services status:" -ForegroundColor Blue
try {
    docker-compose ps
} catch {
    Write-Host "❌ Docker compose command failed" -ForegroundColor Red
}

Write-Host ""
Write-Host "Done!" -ForegroundColor Yellow