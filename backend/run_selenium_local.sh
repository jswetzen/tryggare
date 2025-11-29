#!/bin/bash
# Run Selenium tests against local development servers
# Backend: http://localhost:8000
# Frontend: http://localhost:5173

set -e

echo "🧪 Running Selenium Tests Against Local Dev Servers"
echo "===================================================="
echo ""
echo "Prerequisites:"
echo "  ✓ Backend running on http://localhost:8000"
echo "  ✓ Frontend running on http://localhost:5173"
echo "  ✓ ChromeDriver installed"
echo ""

cd "$(dirname "$0")"

# Check if servers are running
echo "Checking if servers are accessible..."
if ! curl -s http://localhost:8000/api/csrf/ > /dev/null; then
    echo "❌ Backend not accessible at http://localhost:8000"
    echo "   Please start the backend server first"
    exit 1
fi

if ! curl -s http://localhost:5173 > /dev/null; then
    echo "❌ Frontend not accessible at http://localhost:5173"
    echo "   Please start the frontend server first"
    exit 1
fi

echo "✓ Both servers are accessible"
echo ""

# Run the full flow tests
echo "Running Full Workflow Tests..."
echo "=============================="
uv run python test_selenium_full_flows.py

echo ""
echo "✅ Tests completed!"
echo ""
echo "Screenshots saved to: backend/test-results/"
