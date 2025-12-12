# E2E Tests

End-to-end tests for the Conference Check-In System using Selenium WebDriver.

## Test Files

- **test_auth.py** - Authentication (login, logout, session)
- **test_checkin_flow.py** - Check-in workflows (search, individual, bulk)
- **test_checkout_flow.py** - Check-out workflows
- **test_qr_page.py** - QR code page functionality
- **test_print_queue.py** - Print queue management
- **test_i18n.py** - Internationalization and translations
- **test_navigation.py** - Page navigation and responsive UI

## Running Tests

```bash
# All E2E tests
make test-e2e

# Specific suite
make test-auth
make test-checkin
make test-checkout

# Against production
make test-e2e-prod
```

## What's Tested

See `TEST_COVERAGE.md` for complete test coverage matrix.

## Writing Tests

Inherit from base classes:

```python
from tests.e2e.base import E2ETestBase, TestDataMixin

@pytest.mark.e2e
@pytest.mark.auth
class TestMyFeature(E2ETestBase, TestDataMixin):
    def setup_method(self):
        self.setup_driver()
        # Create test data using mixins

    def test_something(self):
        # Use helper methods from base
        self.login("user", "pass")
        element = self.wait_for_element(By.ID, "myid")
```

## Base Classes

**E2ETestBase:**
- `setup_driver()` - Initialize WebDriver
- `teardown_driver()` - Cleanup WebDriver
- `login(username, password)` - Perform login
- `wait_for_element(by, value)` - Wait for element
- `wait_and_click(by, value)` - Wait and click
- `save_screenshot(name)` - Save screenshot

**TestDataMixin:**
- `create_test_user()` - Create admin user
- `create_test_family()` - Create family with parent
- `create_test_child()` - Create child
- `create_test_session()` - Create event and session
- `cleanup_test_data()` - Clean up in correct order

## Configuration

Tests use environment variables:
```bash
FRONTEND_URL=http://localhost:5173  # Dev
BACKEND_URL=http://localhost:8000   # Dev

# Or production:
FRONTEND_URL=http://localhost:8080
BACKEND_URL=http://localhost:8080

# Optional remote Selenium:
SELENIUM_HUB_URL=http://selenium:4444
```

## Debugging

**Screenshots:** Saved to `/tmp/` on failure
**Logs:** Check `web.log`, `frontend.log`, `build.prod.log`
**Verbose:** Run with `-v -s` flags

See parent `README.md` for more details.
