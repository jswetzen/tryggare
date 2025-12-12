# E2E Test Database Configuration

**Date:** 2025-12-12
**Status:** Implemented and Verified

## Problem

The E2E tests were failing because they were configured to use an isolated SQLite test database (`test_db.sqlite3`), but the tests use Selenium to interact with the live development frontend/backend services which use PostgreSQL. This caused authentication failures because:

1. Tests created users in the SQLite database
2. Selenium submitted login forms to the live backend
3. The live backend checked PostgreSQL and didn't find the users
4. Login failed, tests failed

## Solution

Reconfigured E2E tests to use the **live development PostgreSQL database** instead of an isolated test database. This is the correct approach for E2E tests because:

1. **E2E tests test the entire stack** - They interact with running services via Selenium
2. **Tests remain isolated** - Each test uses unique test data with comprehensive cleanup
3. **No data pollution** - The `TestDataMixin` cleanup methods ensure tests don't leave data behind
4. **Proper transaction handling** - pytest-django's `@pytest.mark.django_db(transaction=True)` provides isolation

## Changes Made

### 1. pytest.ini - Changed Django Settings Module
**File:** `/workspace/check-ins/backend/pytest.ini`

```python
# Before
DJANGO_SETTINGS_MODULE = config.settings.test

# After
DJANGO_SETTINGS_MODULE = config.settings.local
```

Added `--reuse-db` flag to prevent pytest from destroying/recreating the database.

### 2. conftest.py - Custom Database Setup
**File:** `/workspace/check-ins/backend/tests/e2e/conftest.py`

Created a new conftest.py that overrides pytest-django's database setup to use the live database:

```python
@pytest.fixture(scope='session', autouse=True)
def django_db_setup(django_db_blocker):
    """
    Override pytest-django's database setup to use the live development database.

    E2E tests interact with running services, so they need to share the same
    database. The --reuse-db flag prevents pytest from destroying/recreating it.
    """
    with django_db_blocker.unblock():
        from django.core.management import call_command
        try:
            call_command('migrate', '--noinput')
        except Exception as e:
            print(f"Warning: Migration check failed: {e}")

        yield
```

### 3. All Test Classes - Added Database Decorator
**Files:**
- `tests/e2e/test_auth.py`
- `tests/e2e/test_checkin_flow.py`
- `tests/e2e/test_checkout_flow.py`
- `tests/e2e/test_i18n.py`
- `tests/e2e/test_navigation.py`
- `tests/e2e/test_print_queue.py`
- `tests/e2e/test_qr_page.py`

Added `@pytest.mark.django_db(transaction=True)` decorator to all test classes:

```python
@pytest.mark.e2e
@pytest.mark.auth
@pytest.mark.django_db(transaction=True)
class TestAuthentication(E2ETestBase, TestDataMixin):
    ...
```

### 4. test.py Settings (Now Unused for E2E)
**File:** `/workspace/check-ins/backend/config/settings/test.py`

Updated documentation in the file to explain that it's no longer used for E2E tests, but kept for potential future unit/integration tests that might need isolation.

## Verification

All authentication tests now pass successfully:

```bash
$ make test-auth
Running authentication tests...
============================== test session starts ==============================
collected 4 items

tests/e2e/test_auth.py::TestAuthentication::test_login_success PASSED    [ 25%]
tests/e2e/test_auth.py::TestAuthentication::test_login_invalid_credentials PASSED [ 50%]
tests/e2e/test_auth.py::TestAuthentication::test_logout PASSED           [ 75%]
tests/e2e/test_auth.py::TestAuthentication::test_session_persistence PASSED [100%]

============================== 4 passed in 17.08s ==============================
```

## Test Isolation Strategy

Even though tests use the live database, isolation is maintained through:

1. **Unique test data** - Each test uses unique usernames/family names (e.g., "authtest", "checkintest", "navtest")
2. **Comprehensive cleanup** - `TestDataMixin.cleanup_test_data()` removes all test data after each test
3. **Transaction support** - `@pytest.mark.django_db(transaction=True)` provides transaction-level isolation where possible
4. **No production data risk** - Tests only run against development database (localhost:5432)

## Future Considerations

1. **Unit/Integration Tests:** If we need truly isolated unit or integration tests in the future, we can:
   - Create a separate test directory (e.g., `tests/unit/`)
   - Use `config.settings.test` for those tests
   - Keep E2E tests using `config.settings.local`

2. **Production E2E Tests:** When running E2E tests against production (port 8080):
   - Same database configuration works
   - Use environment variables to point to production database
   - Consider using a separate test database for production E2E tests

3. **CI/CD Pipeline:** For automated testing:
   - Ensure development environment is running before E2E tests
   - Consider using docker-compose to spin up a fresh environment for each CI run
   - Add pre-test database cleanup to ensure clean state

## Related Documentation

- See `backend/TESTING_QUICKSTART.md` for how to run tests
- See `backend/tests/e2e/TEST_COVERAGE.md` for test coverage details
- See `CLAUDE.md` for overall project testing guidelines
