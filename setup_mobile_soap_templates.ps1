# Mobile SOAP Templates Setup Script (PowerShell)

Write-Host "🚀 Starting Boise Prosthodontics AI Scribe for Mobile Access..." -ForegroundColor Green

# Start Docker services
Write-Host "📦 Starting Docker containers..." -ForegroundColor Yellow
docker-compose up -d

# Wait for services to be ready
Write-Host "⏳ Waiting for services to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check if services are running
Write-Host "🔍 Checking service status..." -ForegroundColor Yellow
docker-compose ps

# Test API endpoint
Write-Host "🧪 Testing API endpoints..." -ForegroundColor Yellow
Write-Host "Templates list:" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "http://localhost:3050/api/templates/list" -Method GET
    Write-Host "✅ API is responding! Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "Template count: $((ConvertFrom-Json $response.Content).Length)" -ForegroundColor Green
}
catch {
    Write-Host "⚠️ API test failed, but services may still be starting..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ Setup Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📱 MOBILE ACCESS INSTRUCTIONS:" -ForegroundColor Cyan
Write-Host "1. Install ngrok: https://ngrok.com/download" -ForegroundColor White
Write-Host "2. Run: ngrok http 3050" -ForegroundColor White
Write-Host "3. Use your ngrok URL for mobile access" -ForegroundColor White
Write-Host ""
Write-Host "🌐 Local Access: http://localhost:3050" -ForegroundColor Yellow
Write-Host "📋 API Base: http://localhost:3050/api/templates" -ForegroundColor Yellow
Write-Host ""
Write-Host "📚 Full API documentation: See MOBILE_SOAP_TEMPLATES_API.md" -ForegroundColor Magenta
Write-Host ""
Write-Host "🔧 Available API Endpoints:" -ForegroundColor Cyan
Write-Host "  GET    /api/templates/list     - List all templates" -ForegroundColor White
Write-Host "  GET    /api/templates/{id}     - Get specific template" -ForegroundColor White
Write-Host "  POST   /api/templates         - Create new template" -ForegroundColor White
Write-Host "  PUT    /api/templates/{id}     - Update template" -ForegroundColor White
Write-Host "  DELETE /api/templates/{id}     - Delete template" -ForegroundColor White
Write-Host ""

# Test quick API commands
Write-Host "💡 Quick Test Commands:" -ForegroundColor Yellow
Write-Host ""
Write-Host "List templates:" -ForegroundColor Cyan
Write-Host 'Invoke-WebRequest -Uri "http://localhost:3050/api/templates/list" -Method GET | Select-Object -ExpandProperty Content' -ForegroundColor Gray
Write-Host ""
Write-Host "Get specific template:" -ForegroundColor Cyan  
Write-Host 'Invoke-WebRequest -Uri "http://localhost:3050/api/templates/new_patient_consultation" -Method GET | Select-Object -ExpandProperty Content' -ForegroundColor Gray
Write-Host ""