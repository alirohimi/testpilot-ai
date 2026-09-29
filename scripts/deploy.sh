#!/bin/bash
# TestPilot AI - Production Deployment Script
# Usage: ./deploy.sh [fly|render|local]

set -e

ENVIRONMENT=${1:-local}
PROJECT_NAME="testpilot-ai"

echo "🚀 Deploying TestPilot AI to $ENVIRONMENT..."

case $ENVIRONMENT in
    fly)
        echo "📦 Building for Fly.io..."
        
        # Check if fly CLI is installed
        if ! command -v fly &> /dev/null; then
            echo "❌ Fly CLI not found. Install it: https://fly.io/docs/hands-on/"
            exit 1
        fi
        
        # Login to Fly
        fly auth login
        
        # Create app if not exists
        fly apps create $PROJECT_NAME 2>/dev/null || echo "✅ App already exists"
        
        # Deploy
        echo "🚀 Deploying to Fly.io..."
        fly deploy
        
        # Post-deploy
        echo "✅ Deployment complete!"
        echo "📍 View logs: fly logs -a $PROJECT_NAME"
        echo "📍 Open app: fly open -a $PROJECT_NAME"
        ;;
        
    render)
        echo "📦 Deploying to Render..."
        
        # Render CLI or GitHub integration
        if [ -n "$RENDER_API_KEY" ]; then
            echo "🔑 Using Render CLI..."
            # Render CLI deployment
            render deploy
        else
            echo "⚠️  Set RENDER_API_KEY environment variable"
            echo "📍 Alternatively, push to GitHub and enable auto-deploy in Render dashboard"
            echo "🔗 https://dashboard.render.com"
        fi
        ;;
        
    local)
        echo "🧪 Running local deployment..."
        
        # Check prerequisites
        echo "📋 Checking prerequisites..."
        
        # Check Python
        if ! command -v python3 &> /dev/null; then
            echo "❌ Python 3 not found"
            exit 1
        fi
        
        # Check Docker
        if ! command -v docker &> /dev/null; then
            echo "⚠️  Docker not found - skipping container deployment"
        fi
        
        # Install dependencies
        echo "📦 Installing dependencies..."
        pip install -r requirements.txt
        
        # Setup environment
        if [ ! -f .env ]; then
            echo "📝 Creating .env file from template..."
            cp .env.example .env
            echo "⚠️  Please edit .env with your configuration"
        fi
        
        # Initialize database
        echo "🗄️  Initializing database..."
        alembic upgrade head
        
        # Start services
        echo "🐳 Starting services..."
        docker-compose up -d
        
        # Wait for services
        echo "⏳ Waiting for services to be ready..."
        sleep 5
        
        # Run migrations
        echo "🔄 Running database migrations..."
        alembic upgrade head
        
        # Start API server
        echo "🚀 Starting API server..."
        uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload &
        
        echo ""
        echo "✅ Deployment complete!"
        echo ""
        echo "📍 API docs: http://localhost:8000/docs"
        echo "📍 Health check: http://localhost:8000/health"
        echo "📍 API root: http://localhost:8000/"
        echo ""
        echo "🧪 Run tests: pytest tests/ -v"
        ;;
        
    *)
        echo "❌ Unknown environment: $ENVIRONMENT"
        echo "Usage: ./deploy.sh [fly|render|local]"
        exit 1
        ;;
esac

echo ""
echo "🎉 Done!"
