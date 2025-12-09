#!/bin/bash
set -e

echo "🧪 Running E2E Tests with Docker Compose (Option 2)"
echo "===================================================="
echo ""
echo "This will:"
echo "  1. Start fresh PostgreSQL test database (in-memory)"
echo "  2. Start Redis/Valkey for channels"
echo "  3. Start Django backend with test settings"
echo "  4. Start SvelteKit frontend"
echo "  5. Start Selenium Chrome in container"
echo "  6. Run Selenium tests against isolated environment"
echo "  7. Tear down all test containers"
echo ""
echo "All test data is isolated and will be destroyed after tests."
echo ""

# Navigate to project root
cd "$(dirname "$0")"

# Build and run tests
echo "Starting test environment..."
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
    echo "✅ All tests passed!"
else
    echo "❌ Tests failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE
