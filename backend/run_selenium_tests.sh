#!/bin/bash
set -e

echo "🧪 Running Selenium E2E Tests (Option 1: Separate Test Database)"
echo "=================================================================="
echo ""
echo "⚠️  IMPORTANT: This runs tests against live dev servers but with"
echo "   a SEPARATE test database. The test DB and dev DB are DIFFERENT!"
echo "   - Frontend: Uses backend API → Postgres (development DB)"
echo "   - Tests: Uses test_db.sqlite3 (isolated test DB)"
echo ""
echo "   Result: Login tests will FAIL because users in test DB aren't"
echo "   in the development Postgres DB that the API uses."
echo ""
echo "   For proper isolated testing, use Option 2:"
echo "   docker-compose -f docker-compose.test.yml up --abort-on-container-exit"
echo ""
echo "Press Ctrl+C to cancel, or Enter to continue anyway..."
read -t 5 || true
echo ""

# Ensure frontend is running
echo "Checking if frontend is running on port 5173..."
if ! curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo "❌ Frontend not running on port 5173"
    echo "   Start it with: cd frontend && npm run dev"
    exit 1
fi
echo "✓ Frontend is running"

# Ensure backend is running
echo "Checking if backend is running on port 8000..."
if ! curl -s http://localhost:8000/api/csrf/ > /dev/null 2>&1; then
    echo "❌ Backend not running on port 8000"
    echo "   Start it with: cd backend && uv run python manage.py runserver"
    exit 1
fi
echo "✓ Backend is running"
echo ""

# Check if test database exists from previous run
if [ -f "test_db.sqlite3" ]; then
    echo "⚠️  Found existing test database (test_db.sqlite3)"
    echo "   This will be cleaned up by Django's test runner"
    echo ""
fi

# Run tests with test settings
echo "Running tests with isolated test database..."
echo "Settings: config.settings.test"
echo ""

cd "$(dirname "$0")"
DJANGO_SETTINGS_MODULE=config.settings.test uv run python test_selenium_login.py

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All tests completed successfully!"
    echo ""
    echo "Test database: test_db.sqlite3"
    echo "Development database: UNTOUCHED ✓"
else
    echo "❌ Tests failed with exit code $EXIT_CODE"
    exit $EXIT_CODE
fi
