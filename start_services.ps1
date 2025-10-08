# Start Boise Prosthodontics AI Scribe Services
Write-Host "🏥 Starting Boise Prosthodontics AI Scribe Services..." -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker..." -ForegroundColor Yellow
try {
    docker ps > $null 2>&1
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

Write-Host ""

# Stop any existing containers
Write-Host "Stopping existing containers..." -ForegroundColor Yellow
docker-compose down

Write-Host ""

# Start Ollama first
Write-Host "Starting Ollama service..." -ForegroundColor Yellow
docker-compose up -d ollama

Write-Host "Waiting for Ollama to start (15 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Check if Ollama is responding
Write-Host "Checking Ollama status..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "✅ Ollama is running" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Ollama may still be starting up..." -ForegroundColor Yellow
}

Write-Host ""

# Pull llama3 model if needed
Write-Host "Checking for llama3 model..." -ForegroundColor Yellow
try {
    $models = docker exec boise_ollama ollama list 2>$null
    if ($models -match "llama3") {
        Write-Host "✅ llama3 model already available" -ForegroundColor Green
    } else {
        Write-Host "Pulling llama3 model (this will take 5-10 minutes)..." -ForegroundColor Yellow
        docker exec boise_ollama ollama pull llama3
        Write-Host "✅ llama3 model downloaded" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️ Could not check models, continuing..." -ForegroundColor Yellow
}

Write-Host ""

# Start all services
Write-Host "Starting all services..." -ForegroundColor Yellow
docker-compose up -d

Write-Host "Waiting for services to initialize (30 seconds)..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

Write-Host ""

# Check service status
Write-Host "Checking service status..." -ForegroundColor Yellow
Write-Host ""

# Check Ollama
try {
    $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "✅ Ollama: Running at http://localhost:11434" -ForegroundColor Green
} catch {
    Write-Host "❌ Ollama: Not responding" -ForegroundColor Red
}

# Check Backend
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3051/health" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "✅ Backend: Running at http://localhost:3051" -ForegroundColor Green
} catch {
    Write-Host "❌ Backend: Not responding" -ForegroundColor Red
}

# Check Frontend
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3050" -TimeoutSec 5 -ErrorAction Stop
    Write-Host "✅ Frontend: Running at http://localhost:3050" -ForegroundColor Green
} catch {
    Write-Host "❌ Frontend: Not responding" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✨ Services Started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📱 Access the app at: http://localhost:3050" -ForegroundColor Cyan
Write-Host ""
Write-Host "🔧 Useful commands:" -ForegroundColor Yellow
Write-Host "   View logs:    docker-compose logs -f backend" -ForegroundColor Gray
Write-Host "   Restart:      docker-compose restart" -ForegroundColor Gray
Write-Host "   Stop:         docker-compose down" -ForegroundColor Gray
Write-Host ""