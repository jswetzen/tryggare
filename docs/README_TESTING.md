# Selenium Testing Guide

This project has two options for running Selenium E2E tests:

## Option 1: Quick Local Testing (Limited)

**Use Case**: Quick verification against running development servers
**Limitation**: Test database is separate from dev database, so login tests will fail

```bash
cd backend
./run_selenium_tests.sh
```

This runs tests against:
- Frontend: http://localhost:5173 (your dev server)
- Backend: http://localhost:8000 (your dev server)
- Database: test_db.sqlite3 (isolated test database)

⚠️ **Important**: The test database and development database are DIFFERENT, so users created in tests won't be in the dev database that your API uses. Only non-auth tests will pass.

## Option 2: Full Isolated Testing (Recommended) ✅

**Use Case**: Complete E2E testing with fresh, isolated environment
**Benefits**: All tests pass, no risk to development data, matches CI/CD

```bash
./run-tests.sh
```

This spins up a complete test environment in Docker:
- Fresh PostgreSQL test database (in tmpfs for speed)
- Fresh Redis/Valkey for channels
- Backend server with test settings
- Frontend server
- Selenium Chrome in container
- Runs all tests
- Tears down everything after

### Manual Docker Compose Usage

```bash
# Build and run tests
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

# Clean up
docker-compose -f docker-compose.test.yml down -v
```

### View Live Testing (VNC)

The Selenium container exposes a VNC server on port 7900:

```bash
# In a browser, navigate to:
http://localhost:7900

# Password: secret
```

You can watch the tests run in real-time!

## Test Files

- `backend/test_selenium_login.py` - Original tests (for local dev servers)
- `backend/test_selenium_docker.py` - Docker-specific tests (uses remote WebDriver)
- `backend/config/settings/test.py` - Test-specific Django settings

## CI/CD Integration

Add to your CI pipeline:

```yaml
# .github/workflows/test.yml
- name: Run E2E Tests
  run: |
    ./run-tests.sh
```

## Troubleshooting

### Tests fail to connect to Selenium

```bash
# Check if Selenium is healthy
docker-compose -f docker-compose.test.yml ps
```

### Want to keep containers running for debugging

```bash
# Run without --abort-on-container-exit
docker-compose -f docker-compose.test.yml up --build

# In another terminal, run tests manually
docker-compose -f docker-compose.test.yml exec test-runner \
  uv run python test_selenium_docker.py
```

### View logs from a specific service

```bash
docker-compose -f docker-compose.test.yml logs backend-test
docker-compose -f docker-compose.test.yml logs frontend-test
docker-compose -f docker-compose.test.yml logs selenium-chrome
```

## Summary

- **Local dev**: Tests are limited because dev DB ≠ test DB
- **Docker Compose**: Full isolation, all tests pass ✅
- **CI/CD**: Use Docker Compose option
