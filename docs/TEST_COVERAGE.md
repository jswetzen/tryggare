# Test Coverage Summary

This document describes all automated tests in the Check-Ins system.

## E2E Tests (Selenium)

### 1. test_selenium_full_flows.py

**Location**: `backend/test_selenium_full_flows.py`

**Run with**: `./verification.sh --test` or `uv run python test_selenium_full_flows.py`

**Tests**:

#### test_complete_checkin_flow()
- Login as staff user
- Navigate to check-in page
- Session auto-selection when only one active session
- Search for family
- Select child for check-in
- Click main check-in button
- Verify check-in record in database
- Verify QR token generated

#### test_complete_checkout_flow()
- Login as staff user
- Pre-create checked-in child
- Navigate to check-out page
- Find child in checked-in list
- Perform check-out
- Verify check-out record in database

#### test_i18n_language_switching()
- Login as staff user
- Verify default language (English)
- Switch to Swedish
- Verify UI text translated
- Switch back to English
- Verify language persists across navigation
- Verify language persists after page reload
- Test "No children checked in" message in Swedish

**Key features tested**:
- Authentication and login
- Check-in workflow
- Check-out workflow
- Session auto-selection
- Family search
- Real-time database verification
- Internationalization (English + Swedish)
- Language persistence

### 2. test_qr_page_e2e.py

**Location**: `backend/test_qr_page_e2e.py`

**Run with**: `./verification.sh --test` or `uv run python test_qr_page_e2e.py`

**Tests**:

#### test_qr_page_public_access()
- QR page loads WITHOUT authentication (public access)
- No redirect to login page
- Child information displays (name, allergies, notes)
- Parent information displays
- Check-in status displays (not checked in)
- After check-in: status updates to "Checked In"
- Session name displays
- Action buttons present:
  - Check-out button
  - Edit child button
  - Reprint label button
- Check-out functionality:
  - Opens modal
  - Accepts "picked up by" input
  - Saves to database
- Undo checkout functionality:
  - Undo button appears within 5-minute window
  - Click undo restores check-in status
  - Database updated correctly

**Key features tested**:
- Public access (no authentication required)
- QR token lookup
- Child information display
- Real-time check-in status
- Check-out with modal
- Undo checkout (5-minute window)
- Action buttons

## Unit/Integration Tests

### 3. test_new_features.py

**Location**: `backend/test_new_features.py`

**Run with**: `uv run python test_new_features.py`

**Tests**:

#### TEST 1: Nested Family Creation
- Create family with 2 parents and 2 children via API
- Verify all nested objects created
- Verify parent details (name, phone, email, relationship)
- Verify child details (name, birthdate, allergies, notes)

#### TEST 2: Family Creation Validation
- Reject family with no parents (400 error)
- Reject family with no children (400 error)

#### TEST 3: Undo Checkout Endpoint
- Check in child
- Check out child
- Undo checkout within time window (success)
- Verify check-in record restored
- Try undo when already checked in (400 error)
- Try undo after 10 minutes (400 error - time window expired)
- Verify 5-minute time window enforcement

#### TEST 4: QR Token Generation
- Create child without QR token
- Check in child
- Verify QR token auto-generated
- Verify token is valid UUID format

**Key features tested**:
- Nested family creation API
- API validation
- Undo checkout endpoint
- Time window enforcement
- QR token generation

## Running Tests

### Run all tests (recommended):
```bash
./verification.sh --test
```

### Run specific test file:
```bash
./verification.sh --test test_selenium_full_flows.py
./verification.sh --test test_qr_page_e2e.py
uv run python test_new_features.py
```

### Run tests without restarting services:
```bash
./verification.sh --no-restart --test
```

## Test Configuration

Tests automatically detect deployment mode:

- **Production** (port 8080): Uses `config.settings.prod` and PostgreSQL on port 5433
- **Development** (port 5173): Uses `config.settings.local` and PostgreSQL on port 5432

Environment variables:
- `FRONTEND_URL`: Frontend URL (default: http://localhost:8080 for prod)
- `BACKEND_URL`: Backend URL (default: http://localhost:8080 for prod)
- `DATABASE_URL`: Database connection string

## Test Data Cleanup

All tests implement proper cleanup:
- Deactivate existing active sessions before test
- Clean up leftover test data from previous runs
- Delete test data after test completes (in finally block)
- Clean up in proper order to avoid foreign key constraints

## Screenshots

Tests save screenshots on failure:
- `/tmp/checkin_test_failure.png`
- `/tmp/checkout_test_failure.png`
- `/tmp/qr_page_test_failure.png`
- `/tmp/final_state.png`

## Test Coverage Summary

| Feature | Unit Tests | E2E Tests | Status |
|---------|-----------|-----------|--------|
| Check-in flow | ✅ | ✅ | Complete |
| Check-out flow | ✅ | ✅ | Complete |
| Undo checkout | ✅ | ✅ | Complete |
| QR page (public) | ✅ | ✅ | Complete |
| QR token generation | ✅ | ✅ | Complete |
| Nested family creation | ✅ | ❌ | Partial |
| Family validation | ✅ | ❌ | Partial |
| Session auto-selection | ❌ | ✅ | Complete |
| Search families | ❌ | ✅ | Complete |
| i18n (EN/SV) | ❌ | ✅ | Complete |
| Language persistence | ❌ | ✅ | Complete |

## Known Gaps

Features that need additional test coverage:
- Add Family modal UI (backend tested, frontend not tested)
- Edit child functionality
- Reprint label functionality
- Admin dashboard
- Ticket validation
- Event management
- WebSocket real-time updates
- Error handling and edge cases
