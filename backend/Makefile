.PHONY: help test test-e2e test-unit test-integration rebuild-dev rebuild-prod clean coverage

# Default target
help:
	@echo "Conference Check-In System - Test & Build Commands"
	@echo ""
	@echo "Test Commands:"
	@echo "  make test              Run all tests (unit + integration + e2e)"
	@echo "  make test-unit         Run unit tests only"
	@echo "  make test-integration  Run API integration tests"
	@echo "  make test-e2e          Run E2E Selenium tests (defaults to dev)"
	@echo "  make test-e2e-dev      Run E2E against dev environment (port 5173)"
	@echo "  make test-e2e-prod     Run E2E against prod environment (port 8080)"
	@echo ""
	@echo "Specific E2E Test Suites:"
	@echo "  make test-auth         Run authentication tests only"
	@echo "  make test-checkin      Run check-in flow tests only"
	@echo "  make test-checkout     Run check-out flow tests only"
	@echo "  make test-qr           Run QR page tests only"
	@echo "  make test-print        Run print queue tests only"
	@echo "  make test-i18n         Run internationalization tests only"
	@echo "  make test-navigation   Run navigation tests only"
	@echo ""
	@echo "Build & Restart Commands:"
	@echo "  make rebuild-dev       Trigger dev environment rebuild"
	@echo "  make rebuild-prod      Trigger production environment rebuild"
	@echo "  make restart-dev       Restart dev containers (hot reload should work)"
	@echo "  make restart-prod      Restart production containers"
	@echo ""
	@echo "Utility Commands:"
	@echo "  make clean             Clean up test artifacts"
	@echo "  make coverage          Run tests with coverage report"
	@echo "  make verify            Run backend verification (quick sanity check)"
	@echo ""
	@echo "Examples:"
	@echo "  make rebuild-prod && sleep 10 && make test-e2e-prod"
	@echo "  make test-checkin      # Run just check-in tests"
	@echo "  make clean test        # Clean then run all tests"

# Test commands
test: test-unit test-e2e

test-unit:
	@echo "Running unit tests..."
	@uv run --group test python manage.py test accounts checkins events families printing

test-integration:
	@echo "Running integration tests..."
	@uv run --group test pytest tests/integration/ -v -m integration

test-e2e: test-e2e-dev

test-e2e-dev:
	@echo "Running E2E tests against development environment..."
	@echo "Frontend: http://localhost:5173"
	@echo "Backend:  http://localhost:8000"
	@FRONTEND_URL=http://localhost:5173 BACKEND_URL=http://localhost:8000 \
		uv run --group test pytest tests/e2e/ -v -m e2e

test-e2e-prod:
	@echo "Running E2E tests against production environment..."
	@echo "Frontend & Backend: http://localhost:8080"
	@FRONTEND_URL=http://localhost:8080 BACKEND_URL=http://localhost:8080 \
		uv run --group test pytest tests/e2e/ -v -m e2e

# Specific test suites
test-auth:
	@echo "Running authentication tests..."
	@uv run --group test pytest tests/e2e/test_auth.py -v

test-checkin:
	@echo "Running check-in flow tests..."
	@uv run --group test pytest tests/e2e/test_checkin_flow.py -v

test-checkout:
	@echo "Running check-out flow tests..."
	@uv run --group test pytest tests/e2e/test_checkout_flow.py -v

test-qr:
	@echo "Running QR page tests..."
	@uv run --group test pytest tests/e2e/test_qr_page.py -v

test-print:
	@echo "Running print queue tests..."
	@uv run --group test pytest tests/e2e/test_print_queue.py -v

test-i18n:
	@echo "Running i18n tests..."
	@uv run --group test pytest tests/e2e/test_i18n.py -v

test-navigation:
	@echo "Running navigation tests..."
	@uv run --group test pytest tests/e2e/test_navigation.py -v

# Utility commands
clean:
	@echo "Cleaning up test artifacts..."
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@rm -f /tmp/*test*.png 2>/dev/null || true
	@rm -f /tmp/*_state.png 2>/dev/null || true
	@rm -f /tmp/qr_*.png 2>/dev/null || true
	@echo "✓ Cleanup complete"

coverage:
	@echo "Running tests with coverage..."
	@uv run --group test pytest tests/ --cov=. --cov-report=html --cov-report=term-missing

verify:
	@echo "Running quick backend verification..."
	@uv run --group test python verify.py
