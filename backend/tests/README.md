# Conference Check-In System - Test Suite

Welcome to the reorganized test suite! This directory contains all tests for the check-in system, organized by type and purpose.

## Quick Start

```bash
# Run all tests
cd /workspace/check-ins/backend
make test

# Run just E2E tests against dev environment
make test-e2e-dev

# Run E2E tests against production
make test-e2e-prod

# Run specific test suite
make test-auth       # Authentication tests
make test-checkin    # Check-in flow tests
make test-checkout   # Check-out flow tests
make test-qr         # QR page tests
make test-print      # Print queue tests
make test-i18n       # Internationalization tests
make test-navigation # Navigation tests
```

## Directory Structure

```
tests/
├── README.md                    # This file
│
├── e2e/                         # End-to-end Selenium tests
│   ├── README.md               # E2E-specific documentation
│   ├── TEST_COVERAGE.md        # Test coverage matrix
│   ├── base.py                 # Base classes and helpers
│   │
│   ├── test_auth.py            # Authentication flows
│   ├── test_checkin_flow.py    # Check-in workflows
│   ├── test_checkout_flow.py   # Check-out workflows
│   ├── test_qr_page.py         # QR code page
│   ├── test_print_queue.py     # Print queue
│   ├── test_i18n.py            # Internationalization
│   └── test_navigation.py      # UI navigation
│
├── integration/                 # API integration tests (future)
│   └── README.md
│
└── unit/                        # Unit tests (future)
    └── README.md
```

## Test Types

### E2E Tests (`e2e/`)

End-to-end tests using Selenium WebDriver. These tests:
- Run in a real browser (headless Chrome)
- Test the complete user workflow
- Verify frontend + backend integration
- Take screenshots on failure (saved to `/tmp/`)

**When to use:** Testing complete user workflows, UI interactions, or cross-system functionality.

### Integration Tests (`integration/`)

API and component integration tests. These tests:
- Test API endpoints directly
- Test WebSocket connections
- Verify database operations
- Faster than E2E tests

**When to use:** Testing API endpoints, WebSocket functionality, or backend integration without UI.

### Unit Tests (`unit/`)

Fast, isolated tests for individual components. These tests:
- Test models, serializers, utilities
- No external dependencies
- Very fast execution
- High code coverage

**When to use:** Testing individual functions, classes, or utilities in isolation.

## Running Tests

### Using Makefile (Recommended)

```bash
# Show all available commands
make help

# Run all tests
make test

# Run specific suite
make test-e2e
make test-unit
make test-integration

# Run specific E2E test file
make test-auth

# Run against production
make test-e2e-prod
```

### Using pytest Directly

```bash
cd /workspace/check-ins/backend

# Run all tests in a directory
pytest tests/e2e/ -v

# Run specific file
pytest tests/e2e/test_auth.py -v

# Run specific test
pytest tests/e2e/test_auth.py::TestAuthentication::test_login_success -v

# Run tests with specific marker
pytest tests/e2e/ -v -m "auth"
pytest tests/e2e/ -v -m "checkin"

# Run with coverage
pytest tests/ --cov=backend --cov-report=html
```

### Using Django test runner

```bash
cd /workspace/check-ins/backend

# Run Django unit tests
uv run python manage.py test accounts checkins events families printing
```

## Environment Configuration

Tests automatically detect environment via environment variables:

```bash
# Development (default)
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000

# Production
FRONTEND_URL=http://localhost:8080
BACKEND_URL=http://localhost:8080

# Remote Selenium Grid (optional)
SELENIUM_HUB_URL=http://selenium:4444
```

## Writing New Tests

### 1. Choose the Right Test Type

- **User workflow?** → E2E test in `e2e/`
- **API endpoint?** → Integration test in `integration/`
- **Individual function?** → Unit test in `unit/`

### 2. Use Base Classes

E2E tests inherit from base classes for common functionality:

```python
from tests.e2e.base import E2ETestBase, TestDataMixin

class TestMyFeature(E2ETestBase, TestDataMixin):
    def setup_method(self):
        self.setup_driver()
        self.test_user = self.create_test_user()
        # ...

    def teardown_method(self):
        self.cleanup_test_data(users=[self.test_user])
        self.teardown_driver()

    def test_something(self):
        self.login("username", "password")
        # ... test code ...
```

### 3. Update Documentation

After adding tests, update:
1. `TEST_COVERAGE.md` - Check off what's now covered
2. This README if adding new patterns

### 4. Run Your Tests

```bash
# Run just your new test
pytest tests/e2e/test_my_feature.py -v

# Run full suite to ensure no regression
make test
```

## Debugging Failed Tests

### Screenshots

Failed E2E tests save screenshots to `/tmp/`:
```bash
ls -lt /tmp/*.png | head -5
```

### Logs

Check application logs:
```bash
# Backend
tail -f /workspace/check-ins/web.log

# Frontend
tail -f /workspace/check-ins/frontend.log

# Build logs
tail -f /workspace/check-ins/build.prod.log
```

### Verbose Output

Run tests with verbose output:
```bash
pytest tests/e2e/test_auth.py -v -s
```

### Run Non-Headless

Edit `base.py` temporarily to remove headless mode:
```python
# In base.py, comment out:
# chrome_options.add_argument("--headless=new")
```

## Test Coverage

View test coverage matrix:
```bash
cat tests/e2e/TEST_COVERAGE.md
```

Generate coverage report:
```bash
make coverage
# Open htmlcov/index.html in browser
```

## CI/CD Integration

Tests can be run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run E2E Tests
  run: |
    cd backend
    make test-e2e-prod
```

## Troubleshooting

### ChromeDriver not found

```bash
# Install ChromeDriver
pip install webdriver-manager
```

### Tests timing out

Increase timeout in base class or specific test:
```python
self.wait_for_element(By.ID, "element", timeout=30)
```

### Database cleanup issues

If tests leave orphaned data:
```bash
cd backend
uv run python manage.py flush --no-input
```

### Import errors

Ensure you're in the correct directory:
```bash
cd /workspace/check-ins/backend
pytest tests/e2e/test_auth.py -v
```

## Resources

- **Test Coverage Matrix:** `tests/e2e/TEST_COVERAGE.md`
- **Base Classes:** `tests/e2e/base.py`
- **Reorganization Plan:** `../docs/E2E_TEST_REORGANIZATION.md`
- **Makefile Help:** `make help`

## Contributing

When contributing tests:
1. Follow existing patterns in base classes
2. Keep tests focused and atomic
3. Clean up test data in teardown
4. Add docstrings explaining what's tested
5. Update coverage matrix

## Questions?

- Check `docs/E2E_TEST_REORGANIZATION.md` for detailed information
- Look at existing tests for examples
- Review base classes for available helpers

---

**Last Updated:** 2025-12-12
**Status:** Active ✅
