#!/bin/bash
#
# Run Selenium tests against production deployment
#
# This script tests the production environment at http://192.168.1.164:8080
# using the production database (db-prod on port 5433)
#
# Usage:
#   ./test_production.sh

set -e

echo "🧪 Running Selenium tests against production deployment"
echo "=================================================="
echo ""
echo "Configuration:"
echo "  Frontend URL: http://192.168.1.164:8080"
echo "  Backend URL:  http://192.168.1.164:8080"
echo "  Database:     postgresql://postgres@localhost:5433/checkins"
echo ""

# Set environment variables for production testing
export DATABASE_URL=postgresql://postgres:postgres@localhost:5433/checkins
export FRONTEND_URL=http://192.168.1.164:8080
export BACKEND_URL=http://192.168.1.164:8080

# Install test dependencies if needed
echo "📦 Installing test dependencies..."
uv sync --group test

echo ""
echo "🚀 Running tests..."
echo ""

# Run the tests
uv run python test_selenium_full_flows.py

echo ""
echo "✅ Production testing complete!"
