#!/bin/bash
set -e

echo "🧪 Running All Selenium E2E Tests"
echo "===================================================="
echo ""
echo "This script runs all Selenium test suites:"
echo "  1. Login flow tests (test_selenium_docker.py)"
echo "  2. Comprehensive E2E tests (test_selenium_comprehensive.py)"
echo ""
echo "All tests run in isolated Docker Compose environment."
echo ""

# Navigate to project root
cd "$(dirname "$0")"

# Build and run tests with comprehensive suite
echo "Starting test environment with comprehensive test suite..."
podman compose -f docker-compose.test.yml up \
  --build \
  --abort-on-container-exit \
  --exit-code-from test-runner \
  --remove-orphans

# Capture exit code
EXIT_CODE=$?

echo ""
echo "Cleaning up test containers..."
podman compose -f docker-compose.test.yml down -v

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ All Selenium tests passed!"
else
    echo "❌ Some tests failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE
