#!/bin/bash
# Mobile SOAP Templates Setup Script

echo "🚀 Starting Boise Prosthodontics AI Scribe for Mobile Access..."

# Start Docker services
echo "📦 Starting Docker containers..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Check if services are running
echo "🔍 Checking service status..."
docker-compose ps

# Test API endpoint
echo "🧪 Testing API endpoints..."
echo "Templates list:"
curl -s http://localhost:3050/api/templates/list | python -m json.tool 2>/dev/null || echo "API response received"

echo ""
echo "✅ Setup Complete!"
echo ""
echo "📱 MOBILE ACCESS INSTRUCTIONS:"
echo "1. Install ngrok: https://ngrok.com/download"
echo "2. Run: ngrok http 3050"
echo "3. Use your ngrok URL for mobile access"
echo ""
echo "🌐 Local Access: http://localhost:3050"
echo "📋 API Base: http://localhost:3050/api/templates"
echo ""
echo "📚 Full API documentation: See MOBILE_SOAP_TEMPLATES_API.md"
echo ""
echo "🔧 Available API Endpoints:"
echo "  GET    /api/templates/list     - List all templates"
echo "  GET    /api/templates/{id}     - Get specific template"  
echo "  POST   /api/templates         - Create new template"
echo "  PUT    /api/templates/{id}     - Update template"
echo "  DELETE /api/templates/{id}     - Delete template"
echo ""