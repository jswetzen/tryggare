# Testing Quick Start Guide

This is your quick reference for running tests in the Conference Check-In System.

## TL;DR - Most Common Commands

```bash
cd /workspace/check-ins/backend

# See all available commands
make help

# Run all E2E tests against dev
make test-e2e-dev

# Run specific test suite
make test-auth         # Authentication tests
make test-checkin      # Check-in flow tests
make test-checkout     # Check-out flow tests

# Rebuild and test production
make rebuild-prod
# Wait ~10 seconds for build
make test-e2e-prod
```

## Test Structure

```
tests/
├── e2e/                    # Selenium E2E tests
│   ├── test_auth.py       # Login/logout
│   ├── test_checkin_flow.py
│   ├── test_checkout_flow.py
│   ├── test_qr_page.py
│   ├── test_print_queue.py
│   ├── test_i18n.py
│   └── test_navigation.py
│
├── integration/           # API tests (future)
└── unit/                 # Unit tests (future)
```

## Quick Examples

### Run All E2E Tests

```bash
# Development environment (localhost:5173)
make test-e2e-dev

# Production environment (localhost:8080)
make test-e2e-prod
```

### Run Specific Test Suite

```bash
make test-auth         # Just authentication
make test-checkin      # Just check-in flow
make test-qr           # Just QR page
```

### Run One Test File

```bash
pytest tests/e2e/test_auth.py -v
```

### Run One Specific Test

```bash
pytest tests/e2e/test_auth.py::TestAuthentication::test_login_success -v
```

### Run Tests by Marker

```bash
pytest tests/e2e/ -m "auth" -v       # All auth-marked tests
pytest tests/e2e/ -m "checkin" -v    # All checkin-marked tests
```

## Rebuild Commands

```bash
# Trigger dev rebuild (hot reload should work)
make rebuild-dev

# Trigger production rebuild
make rebuild-prod

# Just restart (no rebuild)
make restart-dev
make restart-prod
```

## When Tests Fail

1. **Check screenshots:** `ls -lt /tmp/*.png | head -5`
2. **Check logs:**
   - Backend: `tail -f ../web.log`
   - Frontend: `tail -f ../frontend.log`
   - Build: `tail -f ../build.prod.log`
3. **Run with verbose output:** `pytest tests/e2e/test_auth.py -v -s`
4. **Check test coverage:** `cat tests/e2e/TEST_COVERAGE.md`

## Adding New Tests

1. **Pick the right file:**
   - Auth changes? → `test_auth.py`
   - Check-in workflow? → `test_checkin_flow.py`
   - QR page? → `test_qr_page.py`

2. **Use base classes:**
   ```python
   from tests.e2e.base import E2ETestBase, TestDataMixin

   class TestMyFeature(E2ETestBase, TestDataMixin):
       def setup_method(self):
           self.setup_driver()
           self.test_user = self.create_test_user()

       def test_something(self):
           self.login("user", "pass")
           # ... test code ...
   ```

3. **Update coverage:** Edit `tests/e2e/TEST_COVERAGE.md`

## Environment Variables

```bash
# Development (default)
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000

# Production
FRONTEND_URL=http://localhost:8080
BACKEND_URL=http://localhost:8080

# Remote Selenium (optional)
SELENIUM_HUB_URL=http://selenium:4444
```

## Common Issues

### ChromeDriver not found
```bash
pip install webdriver-manager
```

### Tests timeout
Increase timeout in test:
```python
self.wait_for_element(By.ID, "id", timeout=30)
```

### Database cleanup issues
```bash
uv run python manage.py flush --no-input
```

### Import errors
Make sure you're in the right directory:
```bash
cd /workspace/check-ins/backend
pytest tests/e2e/test_auth.py -v
```

## More Information

- **Full test docs:** `tests/README.md`
- **E2E specifics:** `tests/e2e/README.md`
- **Coverage matrix:** `tests/e2e/TEST_COVERAGE.md`
- **Reorganization details:** `../docs/E2E_TEST_REORGANIZATION.md`
- **Summary:** `../docs/TEST_REORGANIZATION_SUMMARY.md`

## Quick Reference Card

| Command | Description |
|---------|-------------|
| `make help` | Show all commands |
| `make test-e2e` | Run all E2E tests (dev) |
| `make test-e2e-prod` | Run all E2E tests (prod) |
| `make test-auth` | Run authentication tests |
| `make test-checkin` | Run check-in tests |
| `make test-checkout` | Run check-out tests |
| `make test-qr` | Run QR page tests |
| `make test-print` | Run print queue tests |
| `make test-i18n` | Run i18n tests |
| `make test-navigation` | Run navigation tests |
| `make rebuild-prod` | Rebuild production |
| `make clean` | Clean up artifacts |

---

**Keep this file handy!** It's your quickest path to running and understanding tests.

Last updated: 2025-12-12
