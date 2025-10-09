# Setup ngrok for mobile access to Boise Prosthodontics AI Scribe
param(
    [string]$NgrokUrl = ""
)

Write-Host "🌐 Setting up ngrok for mobile access..." -ForegroundColor Cyan
Write-Host ""

if (-not $NgrokUrl) {
    Write-Host "Please provide your ngrok URL as a parameter:" -ForegroundColor Yellow
    Write-Host "Example: .\setup_ngrok.ps1 -NgrokUrl 'https://abc123.ngrok.app'" -ForegroundColor Gray
    Write-Host ""
    Write-Host "To set up ngrok:" -ForegroundColor Yellow
    Write-Host "1. Install ngrok: https://ngrok.com/download" -ForegroundColor Gray
    Write-Host "2. Run: ngrok http 3051" -ForegroundColor Gray
    Write-Host "3. Copy the https URL and use it with this script" -ForegroundColor Gray
    Write-Host ""
    
    $NgrokUrl = Read-Host "Enter your ngrok URL (e.g., https://abc123.ngrok.app)"
}

# Validate URL
if (-not $NgrokUrl.StartsWith("https://") -and -not $NgrokUrl.StartsWith("http://")) {
    Write-Host "❌ Invalid URL. Please provide a full ngrok URL starting with https://" -ForegroundColor Red
    exit 1
}

# Remove trailing slash if present
$NgrokUrl = $NgrokUrl.TrimEnd('/')

Write-Host "📝 Updating .env file with ngrok URLs..." -ForegroundColor Yellow

# Read current .env file
$envContent = Get-Content .env -Raw

# Update API URL
$envContent = $envContent -replace "REACT_APP_API_URL=.*", "REACT_APP_API_URL=$NgrokUrl"

# Update WebSocket URL (convert http to ws, https to wss)
$wsUrl = $NgrokUrl -replace "^https://", "wss://" -replace "^http://", "ws://"
$envContent = $envContent -replace "REACT_APP_WS_URL=.*", "REACT_APP_WS_URL=${wsUrl}/ws/audio"

# Write updated .env file
Set-Content .env $envContent

Write-Host "✅ Updated .env file:" -ForegroundColor Green
Write-Host "   API URL: $NgrokUrl" -ForegroundColor Gray
Write-Host "   WebSocket URL: ${wsUrl}/ws/audio" -ForegroundColor Gray
Write-Host ""

Write-Host "🔄 Restarting frontend container to apply changes..." -ForegroundColor Yellow
docker-compose restart frontend

Write-Host ""
Write-Host "⏳ Waiting for frontend to restart..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✨ Mobile Access Ready!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📱 Access from your phone:" -ForegroundColor Yellow
Write-Host "   Frontend: http://localhost:3050 (or through ngrok if you expose port 3050)" -ForegroundColor Cyan
Write-Host "   API Backend: $NgrokUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "🔧 Important Notes:" -ForegroundColor Yellow
Write-Host "   - The frontend connects to: $NgrokUrl" -ForegroundColor Gray
Write-Host "   - WebSocket connects to: ${wsUrl}/ws/audio" -ForegroundColor Gray
Write-Host "   - Make sure ngrok is running on port 3051" -ForegroundColor Gray
Write-Host ""
Write-Host "🌐 To expose frontend via ngrok too:" -ForegroundColor Yellow
Write-Host "   Run in another terminal: ngrok http 3050" -ForegroundColor Gray
Write-Host ""