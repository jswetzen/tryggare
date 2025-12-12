# E2E Test Reorganization Plan

## Overview

This document describes the reorganization of E2E/Selenium tests from scattered files in `backend/` to a structured test suite in `backend/tests/e2e/`.

**Date:** 2025-12-12
**Status:** ✅ Complete

## Goals Achieved

1. ✅ Clear test organization by feature area
2. ✅ Easy-to-understand test coverage via TEST_COVERAGE.md
3. ✅ Simple commands to run specific test suites via Makefile
4. ✅ Separate dev/prod test configurations
5. ✅ Eliminate test duplication
6. ✅ Reusable base classes and helpers

## New Structure

```
backend/
├── Makefile                          # Test orchestration commands
├── pytest.ini                        # Pytest configuration
├── tests/                            # All tests here
│   ├── e2e/                         # End-to-end Selenium tests
│   │   ├── __init__.py
│   │   ├── base.py                  # Base classes & helpers
│   │   ├── TEST_COVERAGE.md         # Coverage matrix
│   │   │
│   │   ├── test_auth.py             # Authentication flows
│   │   ├── test_checkin_flow.py     # Check-in workflows
│   │   ├── test_checkout_flow.py    # Check-out workflows
│   │   ├── test_qr_page.py          # QR code page functionality
│   │   ├── test_print_queue.py      # Print queue functionality
│   │   ├── test_i18n.py             # Internationalization
│   │   └── test_navigation.py       # UI navigation
│   │
│   ├── integration/                 # API integration tests (future)
│   └── unit/                        # Unit tests (future)
```

## Key Improvements

### 1. Organized by Feature

Instead of scattered test files with unclear purpose:
- **Before:** 19 test files in `backend/` root
- **After:** 7 focused test files in `backend/tests/e2e/`

### 2. Reusable Base Classes

`base.py` provides:
- `E2ETestBase`: Common WebDriver setup, login helpers, wait helpers
- `TestDataMixin`: Test data creation (users, families, sessions, etc.)
- Automatic cleanup to prevent test pollution

### 3. Simple Command Interface

Via Makefile:
```bash
make test-e2e           # Run all E2E tests (dev)
make test-e2e-prod      # Run all E2E tests (production)
make test-auth          # Run just authentication tests
make test-checkin       # Run just check-in tests
make rebuild-prod       # Trigger production rebuild
```

### 4. Clear Coverage Matrix

`TEST_COVERAGE.md` shows at a glance:
- What's tested
- What's not tested
- Where to add new tests

### 5. Environment Flexibility

Tests automatically detect environment via environment variables:
- `FRONTEND_URL` - Frontend server URL (default: http://localhost:5173)
- `BACKEND_URL` - Backend server URL (default: http://localhost:8000)
- `SELENIUM_HUB_URL` - Remote Selenium Grid (optional)

## Migration Map

| Old File | New Location | Notes |
|----------|-------------|-------|
| test_selenium_full_flows.py | test_checkin_flow.py, test_checkout_flow.py, test_i18n.py | Split by feature |
| test_selenium_comprehensive.py | test_navigation.py, test_auth.py | Split by feature |
| test_qr_page_e2e.py | test_qr_page.py | Adapted to use base classes |
| test_print_queue_e2e.py | test_print_queue.py | Simplified, key tests migrated |
| test_selenium_login.py | test_auth.py | Merged into auth tests |
| test_selenium_simple.py | ❌ Obsolete | Delete |
| test_selenium_debug.py | ❌ Obsolete | Delete |
| test_selenium_nocache.py | ❌ Obsolete | Delete |
| test_selenium_docker.py | ❌ Obsolete | Delete |
| test_01_login.py | ❌ Obsolete | Delete |
| test_simple_login.py | ❌ Obsolete | Delete |
| test_auth.py (old) | ❌ Obsolete | Delete |
| test_websocket.py | ⏳ Future | Move to integration tests |
| test_new_features.py | ❌ Obsolete | Delete |
| test_recently_printed_fix.py | ❌ Obsolete | Delete |
| test_timer_countdown.py | ❌ Obsolete | Delete |
| test_prod_debug.py | ❌ Obsolete | Delete |

## Usage Examples

### Running Tests

```bash
# Run all tests
make test

# Run just E2E tests against dev environment
make test-e2e-dev

# Run E2E tests against production
make test-e2e-prod

# Run specific test suite
make test-checkin

# Run with pytest directly
cd backend
pytest tests/e2e/test_auth.py -v

# Run tests with specific marker
pytest tests/e2e/ -v -m "auth"
```

### Rebuild and Test Workflow

```bash
# Rebuild production and run tests
make rebuild-prod
# Wait for build to complete (check build.prod.log)
sleep 10
make test-e2e-prod

# Rebuild dev
make rebuild-dev
```

### Adding New Tests

1. Identify which test file the new test belongs in
2. Add test method to appropriate class
3. Update `TEST_COVERAGE.md` to check off the coverage item
4. Run the specific test suite: `make test-<suite>`

Example:
```python
# In tests/e2e/test_checkin_flow.py

def test_supervised_checkin(self):
    """Test checking in a child with guardian present."""
    # Your test code here
```

## Benefits

**For Developers:**
- Clear where to add new tests
- Easy to run specific test suites
- Reusable helpers reduce boilerplate
- Self-documenting structure

**For CI/CD:**
- Simple Makefile targets
- Clear separation of dev vs prod tests
- Fast iteration (run only changed suite)

**For Maintenance:**
- No duplication
- Centralized helpers
- Easy to refactor
- Coverage gaps clearly visible

## Archiving Old Files

Old test files have been moved to `OLD_TESTS/` directory for reference:
```bash
mkdir -p /workspace/check-ins/backend/OLD_TESTS
mv test_selenium_*.py OLD_TESTS/
mv test_01_*.py OLD_TESTS/
# etc.
```

## Future Enhancements

1. **Integration Tests:** Move `test_websocket.py` to `tests/integration/`
2. **Unit Tests:** Move `test_models.py`, `test_api.py` to `tests/unit/`
3. **Coverage Reports:** Add `make coverage` target with HTML reports
4. **Parallel Execution:** Run test files in parallel with pytest-xdist
5. **Visual Regression:** Add screenshot comparison tests
6. **Performance Tests:** Add page load time assertions

## Troubleshooting

### Tests failing after migration

1. Check environment variables are set correctly
2. Verify ChromeDriver is installed: `chromedriver --version`
3. Check servers are running (dev or prod)
4. Look at screenshots in `/tmp/` for failure context

### Import errors

Make sure to run from correct directory:
```bash
cd /workspace/check-ins/backend
pytest tests/e2e/test_auth.py -v
```

### Database cleanup issues

If tests leave orphaned data:
```bash
cd backend
uv run python manage.py flush --no-input
```

## References

- **Test Coverage Matrix:** `backend/tests/e2e/TEST_COVERAGE.md`
- **Base Classes:** `backend/tests/e2e/base.py`
- **Makefile:** `backend/Makefile`
- **Pytest Config:** `backend/pytest.ini`
- **Original Tests:** `backend/OLD_TESTS/` (archived)

## Rollback Plan

If issues arise, old tests are preserved in `OLD_TESTS/` directory:
```bash
# Restore old structure
mv OLD_TESTS/*.py .

# Remove new structure
rm -rf tests/

# Remove Makefile
rm Makefile
```

---

**Last Updated:** 2025-12-12
**Author:** Claude (AI Assistant)
**Status:** Complete ✅
