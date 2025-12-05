# Comprehensive Verification Methodology

This guide provides a foolproof process for testing and verifying changes to the Conference Child Management System. It consolidates learnings from production deployment testing and Selenium test implementation.

---

## Table of Contents

1. [Testing Strategy](#testing-strategy)
2. [Component Tests (Frontend)](#component-tests-frontend)
3. [Understanding the Environment](#understanding-the-environment)
4. [The Restart Mechanism](#the-restart-mechanism)
5. [Quick Testing Workflows](#quick-testing-workflows)
6. [Selenium E2E Testing](#selenium-e2e-testing)
7. [Production-Style Testing](#production-style-testing)
8. [Troubleshooting Common Issues](#troubleshooting-common-issues)

---

## Testing Strategy

This project uses a **two-tier testing approach**:

### 1. Component Tests (Fast, Unit-level)
- **Purpose**: Fast feedback during frontend development
- **Location**: `frontend/src/` (alongside components)
- **Tool**: Vitest + Testing Library
- **Speed**: 2-3 seconds for 38 tests
- **Run**: `cd frontend && pnpm test`
- **When**: During development for instant feedback

### 2. E2E Tests (Slow, Integration-level)
- **Purpose**: Production confidence with full integration
- **Location**: `backend/test_selenium_full_flows.py`
- **Tool**: Selenium + Django test framework
- **Speed**: 15-20 seconds per test
- **Run**: `./verification.sh --test`
- **When**: Before deployment to verify full system

**Both are valuable and complementary!**
- Component tests catch bugs early
- E2E tests verify everything works together

See [frontend/TESTING.md](frontend/TESTING.md) for detailed component testing guide.

---

## Component Tests (Frontend)

### Quick Start

```bash
cd frontend

# Run tests in watch mode (recommended for development)
pnpm test

# Run tests once
pnpm test run

# Run tests with interactive UI
pnpm test:ui

# Run tests with coverage
pnpm test:coverage
```

### What's Tested

**38 Component Tests**:
- LanguageSwitcher (5 tests) - Language switching, i18n
- SearchBox (8 tests) - Input handling, callbacks
- LoginPage (9 tests) - Authentication, validation
- FamilyTable (15 tests) - Check-in/checkout functionality

### When to Use

✅ **Use component tests for**:
- Testing individual component behavior
- Fast iteration during development
- Catching UI bugs before integration testing
- Testing user interactions (clicks, typing)
- Testing conditional rendering
- Testing form validation

❌ **Don't use component tests for**:
- Database verification
- Full user workflows
- Real API integration
- Cross-page navigation
- Production environment validation

**For these, use E2E tests instead!**

### Documentation
- **[frontend/TESTING.md](frontend/TESTING.md)** - Complete testing guide
- **[frontend/UI_TESTING.md](frontend/UI_TESTING.md)** - Testing strategy and architecture

---

## Understanding the Environment

### Development vs Production-Style

**Development Environment** (`docker-compose.yml`):
- Frontend: SvelteKit dev server on port 5173 (with HMR)
- Backend: Django on port 8000
- Database: PostgreSQL on port 5432
- Access: `http://localhost:5173` (frontend) or `http://localhost:8000` (API)

**Production-Style Environment** (`docker-compose.prod.yml`):
- Frontend: Static build served by Django
- Backend: Django on port 8080 (host-exposed)
- Database: PostgreSQL on port 5433 (separate from dev)
- Access: `http://192.168.1.164:8080` or `http://localhost:8080`
- **Important**: This is NOT a remote production server - it's running locally in Podman containers

### Key Technical Details

**SvelteKit Configuration**:
- Uses `adapter-static` for production (client-side only rendering)
- `ssr: false` in `svelte.config.js` (no server-side rendering)
- Test IDs (`data-testid`) only appear after client-side JavaScript renders
- Static HTML does not contain test IDs - they're added by the SvelteKit framework after hydration

**Authentication**:
- Client-side authentication via `/api/auth/check/`
- User data loaded in `frontend/src/routes/+layout.ts`
- Session cookies must match environment (secure=true for HTTPS, secure=false for HTTP)

**Restart Mechanism**:
- File watching pattern using `restart.txt`
- Touching the file triggers Podman container restart
- `restart.sh` script automates this process

---

## The Restart Mechanism

### How It Works

1. **Host machine** runs Podman containers with volume mounts
2. **Containers** watch for changes to `restart.txt` file
3. **When `restart.txt` is modified** (touched), containers detect the change and restart
4. **Container logs** stream to `web.log` and `frontend.log`

### Using verification.sh (Recommended)

The `verification.sh` script replaces `restart.sh` with a comprehensive verification workflow:

```bash
# Just restart and verify (replaces restart.sh)
./verification.sh

# Restart and run all Selenium tests
./verification.sh --test

# Restart and run specific test
./verification.sh --test test_selenium_full_flows.py

# Run tests without restarting
./verification.sh --no-restart --test

# Custom timeout (default: 60s)
./verification.sh --timeout 90
```

**What verification.sh does:**
1. ✅ Touches restart.txt to trigger container restart
2. ✅ Monitors web.log for restart completion (with timeout)
3. ✅ Verifies server health (checks for errors in logs)
4. ✅ Shows recent log summary
5. ✅ Optionally runs Selenium tests
6. ✅ Provides clear visual feedback with colors and progress

### Manual Restart (Legacy)

If you prefer to restart manually without verification.sh:

```bash
# From project root
./restart.sh

# What it does:
# 1. Touches restart.txt to trigger container restart
# 2. Containers detect the change and rebuild/restart
# 3. Wait 30-60 seconds for restart to complete
```

### Verifying Restart Completed (Manual Method)

**Method 1: Check logs for rebuild indicators**
```bash
# Watch web.log for Django startup
tail -f web.log | grep -i "starting\|spawned\|listening"

# Look for lines like:
# "Performing system checks..."
# "Django version X.X.X, using settings 'config.settings.base'"
# "Starting ASGI/Daphne version X.X.X"
# "Listening at: http://0.0.0.0:8000"
```

**Method 2: Check timestamp on restart.txt**
```bash
ls -l restart.txt

# Compare timestamp to current time
# If restart.txt was modified seconds ago, restart should be in progress
```

**Method 3: Monitor container status**
```bash
podman ps | grep -E "web|frontend"

# Check "STATUS" column - should show "Up X seconds" after restart
```

**Recommendation**: Use `verification.sh` instead of manual verification for a more reliable and automated workflow.

### Production-Style Restart

For production-style testing, you need to **manually rebuild**:

```bash
# Production restart requires rebuild
podman compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate --build

# Why restart.sh doesn't work for production:
# - restart.sh only touches restart.txt
# - Production containers don't have hot-reload configured
# - Must rebuild the entire static bundle and image
```

---

## Quick Testing Workflows

### After Backend Changes

```bash
cd /workspace/check-ins/backend

# 1. If models changed, create and apply migrations
uv run python manage.py makemigrations
uv run python manage.py migrate

# 2. Run quick verification
uv run python verify.py

# 3. Restart and verify development server
cd /workspace/check-ins
./verification.sh

# Alternative: Restart and run tests
./verification.sh --test
```

### After Frontend Changes

```bash
cd /workspace/check-ins

# 1. Restart and verify development server
./verification.sh

# 2. Manually test UI changes in browser
# - Navigate to http://localhost:5173 (dev) or http://localhost:8000 (if backend serves static)
# - Test the changed flows
# - Verify i18n works (toggle English/Swedish)

# Alternative: Restart and run all tests
./verification.sh --test
```

### After Adding data-testid Attributes

This is critical for Selenium tests. Follow the UPDATE_GUIDE.md workflow:

```bash
# 1. Add data-testid to components
# Example: frontend/src/routes/checkin/+page.svelte
# <button data-testid="main-checkin-button" onclick={performCheckIn}>

# 2. Restart and run tests to verify
./verification.sh --test

# 3. (Optional) Verify test IDs are in the rendered JavaScript bundle
# (They won't be in static HTML due to ssr=false)
curl -s http://localhost:8000 | grep -o "data-testid" | wc -l
# Should return 0 (test IDs not in static HTML)

curl -s http://localhost:8000/_app/immutable/chunks/*.js | grep "data-testid"
# Should return matches (test IDs in JS bundles)
```

---

## Selenium E2E Testing

### Test File Location

`backend/test_selenium_full_flows.py`

### Running Tests

**Development environment:**
```bash
cd /workspace/check-ins/backend

# Run all tests
uv run python test_selenium_full_flows.py

# Run specific test (if using pytest markers in future)
# uv run pytest test_selenium_full_flows.py::test_checkin_flow -v
```

**Production-style environment:**
```bash
cd /workspace/check-ins/backend

# Use helper script
./test_production.sh

# Or set environment variables manually
export DATABASE_URL=postgresql://postgres:postgres@localhost:5433/checkins
export FRONTEND_URL=http://192.168.1.164:8080
export BACKEND_URL=http://192.168.1.164:8080
uv run python test_selenium_full_flows.py
```

### Test Structure

The test file contains:
1. `SeleniumTestHelper` class - reusable methods for login, navigation, waits
2. Individual test functions:
   - `test_checkin_flow()` - Complete check-in process
   - `test_checkout_flow()` - Complete check-out process
   - `test_i18n_language_switching()` - Language switching and i18n verification
3. Test data setup/cleanup - creates Sessions, Families, Parents, Children, Users

### Understanding Test Failures

**Screenshots on failure:**
- Automatically saved to `/tmp/<test_name>_failure.png`
- View to see what the browser was showing when test failed
- Examples: `/tmp/checkin_test_failure.png`, `/tmp/i18n_test_failure.png`

**Common failure patterns:**

1. **Element not found:**
   ```
   selenium.common.exceptions.TimeoutException: Message:
   Element not found: [data-testid='main-checkin-button']
   ```
   - Check if `data-testid` attribute exists in component
   - Verify restart.sh was run after adding attribute
   - Check screenshot to see actual page state

2. **Button disabled:**
   ```
   Button clicked but no action occurred
   Button disabled state: true
   ```
   - Check browser console logs (printed in test output)
   - Verify all required data is loaded (e.g., selectedSession)
   - Check if multiple sessions exist (prevents auto-select)

3. **Database errors:**
   ```
   IntegrityError: duplicate key value violates unique constraint
   ```
   - Previous test run didn't clean up data
   - Run cleanup manually or restart test database

4. **API authentication errors:**
   ```
   Authentication credentials were not provided
   ```
   - Session cookies not set correctly
   - Check CSRF_COOKIE_SECURE and SESSION_COOKIE_SECURE settings
   - For HTTP testing, both should be `false`

### Test Data Model Compatibility

**Critical field names** (use these in test setup):

**Session:**
```python
session = Session.objects.create(
    name="Morning Session",
    is_active=True,  # NOT status="active"
    start_time="2025-11-29T09:00:00Z",  # Full datetime, NOT "09:00"
    end_time="2025-11-29T12:00:00Z"
)
```

**Family/Parent/Child:**
```python
family = Family.objects.create()  # No family_name field
parent = Parent.objects.create(
    family=family,
    first_name="John",
    last_name="Smith"
    # NOT primary_contact_name
)
child = Child.objects.create(
    family=family,
    first_name="Emma",
    last_name="Smith",
    birthdate="2020-05-15",  # NOT date_of_birth
    ticket_type="event_pass"
)
```

### Browser Console Logging

Tests automatically check browser console for errors:

```python
# Check browser console for errors
logs = helper.driver.get_log('browser')
if logs:
    print("   📋 Browser console logs:")
    for log in logs:
        if log['level'] in ['SEVERE', 'WARNING']:
            print(f"      [{log['level']}] {log['message']}")
```

This helps identify JavaScript errors, API failures, and other client-side issues.

---

## Production-Style Testing

### What "Production-Style" Means

- Running locally on your development machine
- Using production configuration (static build, production settings)
- Separate database from development (port 5433 vs 5432)
- Mimics production deployment without being on a remote server

### Starting Production-Style Environment

```bash
cd /workspace/check-ins

# 1. Ensure .env.prod exists and is configured
cat .env.prod
# Should contain:
# - SECRET_KEY=<random-key>
# - ALLOWED_HOSTS=192.168.1.164,localhost
# - CORS_ALLOWED_ORIGINS=http://192.168.1.164:8080,http://localhost:8080
# - CSRF_TRUSTED_ORIGINS=http://192.168.1.164:8080,http://localhost:8080
# - SESSION_COOKIE_SECURE=false (for HTTP testing)
# - CSRF_COOKIE_SECURE=false (for HTTP testing)

# 2. Build and start production containers
podman compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# 3. Wait for build to complete (can take 1-2 minutes)
# Watch for "Successfully tagged" and containers starting

# 4. Create superuser (first time only)
podman compose -f docker-compose.prod.yml exec web-prod uv run python manage.py createsuperuser

# 5. Access application
# Navigate to: http://192.168.1.164:8080 or http://localhost:8080
```

### Verifying Production Build

**Check if static files were built:**
```bash
podman compose -f docker-compose.prod.yml exec web-prod ls -la /app/staticfiles

# Should show index.html and _app/ directory with JS bundles
```

**Check environment variables:**
```bash
podman compose -f docker-compose.prod.yml exec web-prod env | grep -E "ALLOWED_HOSTS|CORS|CSRF"

# Verify values match .env.prod
```

**Check logs:**
```bash
# Backend logs
podman compose -f docker-compose.prod.yml logs web-prod --tail=50

# Database logs
podman compose -f docker-compose.prod.yml logs db-prod --tail=20
```

### Making Changes to Production-Style

**Important**: restart.sh does NOT work for production-style environment.

```bash
# After making changes to code:

# 1. Rebuild the production containers
podman compose -f docker-compose.prod.yml --env-file .env.prod up -d --force-recreate --build

# 2. Wait for rebuild (1-2 minutes)

# 3. Verify changes are applied
# - Check logs
# - Test in browser
# - Run Selenium tests
```

### Running Selenium Tests Against Production-Style

```bash
cd /workspace/check-ins/backend

# Method 1: Use helper script
./test_production.sh

# Method 2: Set environment variables
export DATABASE_URL=postgresql://postgres:postgres@localhost:5433/checkins
export FRONTEND_URL=http://192.168.1.164:8080
export BACKEND_URL=http://192.168.1.164:8080
uv run python test_selenium_full_flows.py

# Method 3: Modify test_selenium_full_flows.py temporarily
# Change FRONTEND_URL and DATABASE_URL at top of file
# (Not recommended - easy to accidentally commit)
```

---

## Troubleshooting Common Issues

### Issue: Test IDs Not Found

**Symptom:**
```
selenium.common.exceptions.TimeoutException:
Element not found: [data-testid='family-search']
```

**Diagnosis:**
```bash
# 1. Check if test ID exists in component source
grep -n "data-testid=\"family-search\"" frontend/src/lib/components/SearchBox.svelte

# 2. Check if test ID is in rendered JavaScript bundle
curl -s http://localhost:8000/_app/immutable/chunks/*.js | grep "family-search"

# 3. Verify restart completed
tail -n 20 frontend.log | grep -i "built\|ready"
```

**Solutions:**
1. Add the data-testid attribute to the component
2. Restart the server with `./restart.sh`
3. Wait 30 seconds for rebuild
4. Re-run tests

### Issue: Button Disabled / Not Clickable

**Symptom:**
```
Button clicked but no API call made
Button disabled state: true
```

**Diagnosis:**
```bash
# 1. Check browser console in test output
# Look for JavaScript errors or missing data

# 2. Inspect database for duplicate sessions
psql -U postgres -h localhost -p 5432 -d checkins
SELECT id, name, is_active FROM checkins_session WHERE is_active = true;
# Should return only ONE active session
```

**Solutions:**
1. Clean up duplicate sessions in database
2. Verify selectedSession is set correctly
3. Check that child selection logic works
4. Review button's disabled condition in component

### Issue: Authentication Failing in Production-Style

**Symptom:**
```
Error: Authentication credentials were not provided
Status: 403
```

**Diagnosis:**
```bash
# 1. Check cookie security settings
grep -E "SESSION_COOKIE_SECURE|CSRF_COOKIE_SECURE" .env.prod

# 2. Check ALLOWED_HOSTS
grep "ALLOWED_HOSTS" .env.prod

# 3. Check actual cookies in browser (via test)
# Test should print cookies after login
```

**Solutions:**
1. For HTTP testing (no SSL), set both to false:
   ```env
   SESSION_COOKIE_SECURE=false
   CSRF_COOKIE_SECURE=false
   ```

2. Verify ALLOWED_HOSTS includes your IP:
   ```env
   ALLOWED_HOSTS=192.168.1.164,localhost
   ```

3. Ensure CORS_ALLOWED_ORIGINS includes port:
   ```env
   CORS_ALLOWED_ORIGINS=http://192.168.1.164:8080,http://localhost:8080
   ```

4. Rebuild production containers after changing .env.prod

### Issue: Database Connection Failed

**Symptom:**
```
psycopg2.OperationalError: could not connect to server
```

**Diagnosis:**
```bash
# 1. Check if database container is running
podman ps | grep postgres

# 2. Check database logs
podman logs <container-id>

# 3. Verify DATABASE_URL
echo $DATABASE_URL
# Development: postgresql://postgres:postgres@localhost:5432/checkins
# Production: postgresql://postgres:postgres@localhost:5433/checkins
```

**Solutions:**
1. Ensure correct port (5432 for dev, 5433 for prod)
2. Start database container if not running
3. Check credentials match environment file

### Issue: WebSocket Connection Failed

**Symptom:**
```
WebSocket connection failed: wss://localhost:8000/ws/...
```

**Diagnosis:**
```bash
# 1. Check WebSocket URL configuration
grep "VITE_PUBLIC_WS_BASE_URL" docker-compose.prod.yml

# 2. Check if using wss:// on http:// site
# Browser console should show: "Mixed Content" warning
```

**Solutions:**
1. For HTTP sites, use ws:// not wss://
2. Dynamic URL detection in websocket.ts handles this automatically
3. For production with SSL, ensure reverse proxy handles WebSocket upgrades

### Issue: i18n Test Failing (Expected)

**Symptom:**
```
❌ i18n test FAILED: Text should change to Swedish, but got: 'Search Families' (expected: 'Sök Familjer')
```

**This is CORRECT behavior** - the test is identifying that the UI has hardcoded English text instead of using translation keys.

**Diagnosis:**
The test correctly identifies missing i18n implementation:
- Hardcoded: `<label>Search Families</label>`
- Should be: `<label>{$t('checkin.search_families')}</label>`

**Solution:**
1. Replace hardcoded text with translation keys
2. Add Swedish translations to `frontend/src/lib/i18n/locales/sv.json`
3. Re-run test to verify i18n works

---

## Complete Testing Workflow Example

### Scenario: Adding a New Feature to Check-In Page

```bash
# 1. Create a branch
git checkout -b feature-session-selector

# 2. Add data-testid attributes to existing elements (if needed)
vim frontend/src/routes/checkin/+page.svelte
# Add: data-testid="session-select"

# 3. Implement the new feature
vim frontend/src/routes/checkin/+page.svelte
# Add session selector dropdown

# 4. Add i18n support
vim frontend/src/lib/i18n/locales/en.json
vim frontend/src/lib/i18n/locales/sv.json

# 5. Update Selenium test
vim backend/test_selenium_full_flows.py
# Add test case for session selector

# 6. Restart and run tests (one command!)
./verification.sh --test

# 7. Fix any test failures
# View screenshots in /tmp/
# Adjust test or fix bugs
# Re-run: ./verification.sh --test

# 8. Manual testing in browser
# Navigate to http://localhost:5173
# Test the new session selector
# Toggle language to verify i18n

# 9. Test in production-style environment
cd /workspace/check-ins
podman compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# Wait for build
sleep 120

# 10. Run Selenium tests against production
cd backend
./test_production.sh

# 11. Commit changes
git add .
git commit -m "Add session selector to check-in page with i18n support"

# 12. Push and create PR (if applicable)
git push origin feature-session-selector
```

---

## Best Practices Summary

### DO:
- ✅ Always add `data-testid` attributes when creating new UI elements
- ✅ Use restart.sh and verify completion before testing
- ✅ Check both web.log and frontend.log after restart
- ✅ Run Selenium tests after UI changes
- ✅ Test in both dev and production-style environments
- ✅ Clean up test data between runs
- ✅ Use correct field names for database models
- ✅ Check browser console logs in test output
- ✅ Implement i18n from the start (don't hardcode text)

### DON'T:
- ❌ Don't assume restart.sh works for production-style (it doesn't)
- ❌ Don't look for test IDs in static HTML (ssr=false means they're in JS)
- ❌ Don't use wrong field names (status vs is_active, date_of_birth vs birthdate)
- ❌ Don't commit with failing tests
- ❌ Don't skip cleaning up test data
- ❌ Don't forget to wait after restart (minimum 30 seconds)
- ❌ Don't ignore browser console errors in test output
- ❌ Don't use SESSION_COOKIE_SECURE=true with HTTP

---

## Quick Reference Commands

```bash
# Restart development server (NEW - recommended)
./verification.sh

# Restart and run all tests (NEW - recommended)
./verification.sh --test

# Restart and run specific test (NEW)
./verification.sh --test test_selenium_full_flows.py

# Run tests without restarting (NEW)
./verification.sh --no-restart --test

# Legacy restart (manual verification needed)
./restart.sh && sleep 30

# Check restart completed (manual)
tail -n 20 web.log | grep "Listening"

# Run Selenium tests (dev)
cd backend && uv run python test_selenium_full_flows.py

# Rebuild production
podman compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# Run Selenium tests (production)
cd backend && ./test_production.sh

# Check logs
tail -f web.log
tail -f frontend.log

# View test failure screenshots
ls -lh /tmp/*_failure.png
```

---

## Related Documentation

- **UPDATE_GUIDE.md**: Detailed guide for maintaining Selenium tests during UI redesign
- **PRODUCTION_DEPLOYMENT.md**: Production deployment architecture and setup
- **CLAUDE.md**: Development environment overview and task completion checklist
- **PROJECT_SPECIFICATION.md**: Complete system specification
- **TECHNICAL_DESIGN.md**: Technical architecture and design decisions
