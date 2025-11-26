# Selenium Testing Strategy & Database Management Plan

## Problem Statement

The current Selenium tests use `ChannelsLiveServerTestCase` which was configured to use the same SQLite database for tests as production. This causes two issues:

1. **Development workflow issue**: Running tests against the live development database can delete/modify production data (like the admin user)
2. **Test isolation issue**: Tests should run in isolation with a clean database state

## Current Situation

- **Development Environment**: Uses PostgreSQL database (`DATABASE_URL` pointing to postgres container)
- **Test Configuration**: Tests currently configured to use `db.sqlite3` (which doesn't exist)
- **ChannelsLiveServerTestCase**: Requires special database configuration per Django Channels guide

## Options & Recommendations

### Option 1: Separate Test Database (RECOMMENDED for Development)

**Use a dedicated test database that's automatically cleaned up after tests.**

#### Implementation:

```python
# backend/config/settings/test.py
from .base import *

# Use a separate test database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test_db.sqlite3",
        # Don't override TEST.NAME - let Django create a temporary test DB
    }
}

# Use in-memory channel layer for testing
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    }
}
```

#### Usage:

```bash
# Run tests with test settings
cd /workspace/check-ins/backend
DJANGO_SETTINGS_MODULE=config.settings.test uv run python test_selenium_login.py
```

**Pros:**
- ✅ Completely isolated from development database
- ✅ Clean state for every test run
- ✅ Won't delete admin user or any development data
- ✅ Simple to implement

**Cons:**
- ❌ Need to set environment variable or update test file
- ❌ Test database is ephemeral (but that's usually desired)

---

### Option 2: External Test Runner with Docker Compose (RECOMMENDED for CI/CD)

**Create a separate docker-compose setup for automated testing.**

#### Implementation:

```yaml
# docker-compose.test.yml
services:
  db-test:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: checkins_test
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
    tmpfs:
      - /var/lib/postgresql/data  # Use tmpfs for speed

  backend-test:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://test:test@db-test:5432/checkins_test
      DJANGO_SETTINGS_MODULE: config.settings.test
    depends_on:
      - db-test
    command: pytest tests/selenium/

  frontend-test:
    build: ./frontend
    environment:
      BACKEND_URL: http://backend-test:8000
    depends_on:
      - backend-test
```

#### Usage:

```bash
# Run entire test suite in isolated environment
docker-compose -f docker-compose.test.yml up --abort-on-container-exit

# Or with CI/CD
make test-e2e
```

**Pros:**
- ✅ Complete isolation - fresh environment every time
- ✅ Matches CI/CD environment exactly
- ✅ Can run in parallel with development
- ✅ Reproducible across all machines
- ✅ No risk to development data

**Cons:**
- ❌ Slower to start up (container overhead)
- ❌ More complex setup
- ❌ Requires Docker

---

### Option 3: Mock External Server (Current Approach - NOT RECOMMENDED)

**Test against the running development server.**

This is what we're currently doing and it has significant drawbacks:

**Pros:**
- ✅ Simple - no additional setup
- ✅ Tests against "real" environment

**Cons:**
- ❌ Modifies development database
- ❌ Can delete production data (admin user got deleted)
- ❌ Tests are not isolated
- ❌ Can interfere with manual testing
- ❌ Not suitable for CI/CD

---

### Option 4: Hybrid Approach (RECOMMENDED - Best of Both Worlds)

**Use Option 1 for local development, Option 2 for CI/CD.**

#### Project Structure:

```
backend/
├── config/
│   └── settings/
│       ├── base.py          # Base settings
│       ├── local.py         # Development (uses postgres)
│       ├── test.py          # Testing (uses sqlite)
│       └── production.py    # Production
├── test_selenium_login.py   # Local testing script
└── tests/
    └── e2e/
        └── test_selenium_login.py  # CI/CD test suite

docker-compose.yml           # Development environment
docker-compose.test.yml      # Test environment
```

#### Implementation:

**1. Create test settings:**

```python
# backend/config/settings/test.py
from .base import *

# Separate test database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "test_db.sqlite3",
    }
}

# Don't send real emails
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Faster password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# In-memory cache
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemBackend',
    }
}
```

**2. Update test script to use test settings:**

```python
# backend/test_selenium_login.py (line 27)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
```

**3. Add .gitignore entry:**

```
# .gitignore
backend/test_db.sqlite3
backend/test_db.sqlite3-*
```

**4. Create helper script:**

```bash
# backend/run_selenium_tests.sh
#!/bin/bash
set -e

echo "🧪 Running Selenium E2E Tests"
echo "================================"

# Ensure frontend is running
if ! curl -s http://localhost:5173 > /dev/null; then
    echo "❌ Frontend not running on port 5173"
    echo "   Start it with: cd frontend && npm run dev"
    exit 1
fi

# Ensure backend is running
if ! curl -s http://localhost:8000/api/csrf/ > /dev/null; then
    echo "❌ Backend not running on port 8000"
    echo "   Start it with: cd backend && uv run python manage.py runserver"
    exit 1
fi

echo "✓ Frontend and backend are running"
echo ""

# Run tests with test settings
cd backend
DJANGO_SETTINGS_MODULE=config.settings.test uv run python test_selenium_login.py

echo ""
echo "✅ All tests completed!"
```

**Pros:**
- ✅ Clean separation of concerns
- ✅ Local development is fast and isolated
- ✅ CI/CD has complete control
- ✅ No risk to development data
- ✅ Easy to understand and maintain

**Cons:**
- ❌ Slightly more setup initially
- ❌ Need to maintain multiple settings files

---

## Immediate Fix (Quick Solution)

To immediately prevent the admin user from being deleted:

### Revert the TEST database override:

```python
# backend/config/settings/base.py
def _database_config():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
            # REMOVE THIS:
            # "TEST": {
            #     "NAME": BASE_DIR / "db.sqlite3",
            # },
        }
```

This will make tests use a temporary test database like `test_db.sqlite3` instead of the main database.

### Update test script:

```python
# backend/test_selenium_login.py
# Change line 27 to:
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
```

---

## Recommendation Summary

**For Immediate Use:**
1. Implement **Option 1** (Separate Test Database) - takes 10 minutes
2. Create `config/settings/test.py`
3. Update test script to use test settings
4. Run tests safely without affecting development data

**For Long-term/CI-CD:**
1. Implement **Option 4** (Hybrid Approach)
2. Keep Option 1 for quick local testing
3. Add Option 2 (Docker Compose) for automated regression testing
4. Document in CI/CD pipeline

## Migration Path

1. **Today**: Implement Option 1 (Separate Test Database)
2. **This Week**: Create `run_selenium_tests.sh` helper script
3. **Next Sprint**: Implement docker-compose.test.yml for CI/CD
4. **Future**: Add more E2E tests using the established pattern

---

## Testing Best Practices

### Do's:
- ✅ Use separate test databases
- ✅ Clean up test data after each test
- ✅ Use fixtures for common test data
- ✅ Mock external services
- ✅ Run tests in CI/CD on every commit

### Don'ts:
- ❌ Test against production database
- ❌ Test against development database (current issue)
- ❌ Share database between tests
- ❌ Commit test database files to git
- ❌ Hard-code production credentials in tests
