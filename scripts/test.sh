#!/bin/bash
# Run tests with coverage
set -e

echo "🧪 Running TestPilot AI tests..."

# Install test dependencies
pip install -q pytest pytest-asyncio pytest-cov

# Run tests
pytest tests/ -v --cov=api --cov-report=term-missing --cov-report=html

echo ""
echo "✅ Tests complete!"
echo "📊 Coverage report: htmlcov/index.html"
