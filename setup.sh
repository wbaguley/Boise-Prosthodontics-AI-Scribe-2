#!/bin/bash

# Boise Prosthodontics AI Scribe - Quick Setup Script

set -e

echo "🦷 Boise Prosthodontics AI Scribe - Setup"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker detected${NC}"

# Create directories
echo "Creating directories..."
mkdir -p Backend/models Backend/logs

# Stop existing containers
echo "Stopping existing containers..."
docker-compose down 2>/dev/null || true

# Build and start
echo "Building containers (this will take 5-10 minutes)..."
docker-compose build --no-cache

echo "Starting Ollama first..."
docker-compose up -d ollama

echo "Waiting for Ollama to start..."
sleep 10

echo "Downloading Llama3 model (this will take 5-10 minutes)..."
docker exec boise_ollama ollama pull llama3:latest || echo "Will retry later"

echo "Starting all services..."
docker-compose up -d

echo "Waiting for services to initialize..."
sleep 30

# Check services
echo ""
echo "Checking services..."

if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Ollama running${NC}"
else
    echo -e "${YELLOW}⚠️  Ollama not ready yet${NC}"
fi

if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend running${NC}"
else
    echo -e "${YELLOW}⚠️  Backend not ready yet${NC}"
fi

if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend running${NC}"
else
    echo -e "${YELLOW}⚠️  Frontend not ready yet${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✨ Setup Complete!${NC}"
echo ""
echo "📱 Access the app at: http://localhost:3000"
echo ""
echo "🔧 Useful commands:"
echo "   View logs:    docker-compose logs -f backend"
echo "   Restart:      docker-compose restart"
echo "   Stop:         docker-compose down"
echo ""
echo "🧪 Test the system:"
echo "   1. Open http://localhost:3000"
echo "   2. Click 'Start Recording'"
echo "   3. Say: 'Patient needs crown on tooth 14'"
echo "   4. Click 'Stop Recording'"
echo "   5. Check the SOAP note"
echo ""
echo "=========================================="