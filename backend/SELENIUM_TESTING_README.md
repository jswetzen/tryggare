# Selenium Testing for Frontend Login Flow

## Overview

This directory contains Selenium-based end-to-end tests for the frontend login flow, following the Django Channels testing guide from https://channels.readthedocs.io/en/latest/tutorial/part_4.html.

## Test Files

- `test_selenium_login.py` - Main test suite with comprehensive login flow tests
- `test_selenium_debug.py` - Debug script to troubleshoot issues
- `test_selenium_simple.py` - Simple test for basic connectivity

## Setup

### Dependencies

The required dependencies are installed via uv:

```bash
cd /workspace/check-ins/backend
uv sync --group test
```

This installs:
- `selenium>=4.15,<5.0` - WebDriver for browser automation
- `webdriver-manager>=4.0,<5.0` - Automatic ChromeDriver management

### Database Configuration

The database settings in `config/settings/base.py` have been configured for Selenium testing:

```python
"TEST": {
    "NAME": BASE_DIR / "db.sqlite3",
}
```

This ensures that `ChannelsLiveServerTestCase` can access the same database as the test server.

## ✅ Resolved: i18n Hydration Issue

### Problem (Resolved)

The frontend login page was failing to hydrate in headless Chrome due to an `svelte-i18n` initialization issue.

### Solution Implemented

Updated `frontend/src/lib/i18n/i18n.ts` to explicitly set the locale:

```typescript
import { register, init, locale } from 'svelte-i18n';

register('en', () => import('./locales/en.json'));
register('sv', () => import('./locales/sv.json'));

init({
  fallbackLocale: 'en',
  initialLocale: 'en',
});

// Explicitly set locale to ensure it's initialized
// This fixes issues with headless browsers and SSR
locale.set('en');
```

This ensures the locale is immediately available, preventing the hydration failure in headless Chrome and other testing environments.

## Test Structure

### LoginFlowSeleniumTest

Extends `ChannelsLiveServerTestCase` to support WebSocket URLs and provides:

1. **test_successful_login_flow**: Tests complete login flow from form submission to redirect
2. **test_invalid_credentials_error**: Verifies error messages for invalid credentials
3. **test_empty_fields_validation**: Checks HTML5 form validation
4. **test_logout_flow**: Tests logout and session clearing
5. **test_login_logout_login_again**: ✨ Tests login → logout → login again (verifies session cleanup)
6. **test_protected_route_redirect_with_return_url**: ✨ Tests accessing protected route while logged out, then logging in

### Helper Methods

- `wait_for_element_and_interact()`: Handles stale element references with retry logic

## Running Tests

```bash
# Ensure servers are running
# Backend: http://localhost:8000
# Frontend: http://localhost:5173

# Run the test suite
cd /workspace/check-ins/backend
uv run python test_selenium_login.py
```

### Test Results

All 6 tests pass successfully:

```
test_empty_fields_validation (__main__.LoginFlowSeleniumTest.test_empty_fields_validation) ... ok
test_invalid_credentials_error (__main__.LoginFlowSeleniumTest.test_invalid_credentials_error) ... ok
test_login_logout_login_again (__main__.LoginFlowSeleniumTest.test_login_logout_login_again) ... ok
test_logout_flow (__main__.LoginFlowSeleniumTest.test_logout_flow) ... ok
test_protected_route_redirect_with_return_url (__main__.LoginFlowSeleniumTest.test_protected_route_redirect_with_return_url) ... ok
test_successful_login_flow (__main__.LoginFlowSeleniumTest.test_successful_login_flow) ... ok

Ran 6 tests in ~25s
```

## Chrome Options

The tests use the following Chrome configuration for headless testing:

```python
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--lang=en-US")
chrome_options.add_argument("--enable-javascript")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)
chrome_options.add_experimental_option("prefs", {
    "intl.accept_languages": "en-US,en"
})
```

## References

- [Django Channels Testing Guide](https://channels.readthedocs.io/en/latest/tutorial/part_4.html)
- [Selenium Python Documentation](https://selenium-python.readthedocs.io/)
- [SvelteKit i18n](https://github.com/kaisermann/svelte-i18n)

## Achievements

- ✅ Fixed i18n hydration issue in headless Chrome
- ✅ Implemented comprehensive login/logout test suite
- ✅ Added test for login-logout-login flow (addresses ongoing session cleanup issues)
- ✅ Added test for protected route redirection
- ✅ All 6 tests passing successfully
- ✅ Configured Chrome options for optimal headless testing
- ✅ Database configured for ChannelsLiveServerTestCase compatibility

## Next Steps

1. Add tests for WebSocket functionality (check-in/check-out real-time updates)
2. Add tests for language switcher functionality
3. Integrate tests into CI/CD pipeline
4. Add visual regression testing
