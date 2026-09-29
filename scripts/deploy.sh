#!/bin/bash
# TestPilot AI - Docker Deployment Script

set -e

echo "🚀 TestPilot AI - Docker Deployment"
echo "================================"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install docker-compose."
    exit 1
fi

# Build and start
echo "📦 Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

echo "✅ Services started!"
echo ""
echo "API: http://localhost:8000"
echo "Docs: http://localhost:8000/docs"
echo "Postgres: localhost:5432"
echo ""
echo "To stop: docker-compose down"
echo "To view logs: docker-compose logs -f"
