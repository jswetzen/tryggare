# E2E Test Coverage Matrix

This document provides an overview of what functionality is covered by our E2E tests.
Use this to quickly understand test coverage and identify gaps.

## Authentication (test_auth.py)
- [x] Login with valid credentials
- [x] Login with invalid credentials
- [x] Logout functionality
- [x] Session persistence across navigation
- [ ] Password reset flow (not implemented)
- [ ] Session timeout (not implemented)

## Check-In Flow (test_checkin_flow.py)
- [x] Search family by name
- [x] Individual child check-in
- [x] Prevent duplicate check-in to same session
- [x] Session auto-selection
- [ ] Bulk family check-in (partial - see old tests)
- [ ] Supervised check-in with guardian (planned feature)
- [ ] Ticket validation (if implemented)
- [ ] Allergy warnings display (visual only)

## Check-Out Flow (test_checkout_flow.py)
- [x] View checked-in children on checkout page
- [x] Check-out with pickup person name
- [ ] Undo checkout within 5-minute window (in old tests)
- [ ] Undo disabled after 5 minutes (in old tests)
- [ ] Bulk checkout (not implemented)

## QR Page (test_qr_page.py)
- [x] Public access without authentication
- [x] Child information display (name, allergies, parent)
- [x] Check-in status display (not checked in / checked in)
- [x] Action buttons present (checkout, edit, print)
- [ ] Checkout from QR page workflow (partial)
- [ ] Undo from QR page (in old tests)
- [ ] Edit child info from QR page
- [ ] Reprint label from QR page
- [ ] QR code generation/display

## Print Queue (test_print_queue.py)
- [x] Display unprintable check-ins
- [x] Empty queue state
- [ ] Individual print action (in old tests)
- [ ] Recently printed section (in old tests)
- [ ] Session filtering (in old tests)
- [ ] Supervised child filtering (planned feature)
- [ ] Bulk print (removed feature)

## Internationalization (test_i18n.py)
- [x] Switch language (English ↔ Norwegian)
- [x] Language persistence across navigation
- [ ] Language persistence after page reload (in old tests)
- [ ] All UI elements translated correctly
- [ ] Date/time format localization

## Navigation (test_navigation.py)
- [x] Navigate between pages (checkin, checkout)
- [x] Responsive hamburger menu on mobile
- [ ] Breadcrumb navigation (if implemented)
- [ ] Print queue navigation link
- [ ] Back button behavior

## WebSocket / Real-time Updates (not yet migrated)
- [ ] Check-in broadcasts to other clients
- [ ] Multi-station synchronization
- [ ] Checkout broadcasts
- [ ] Connection recovery
- [ ] Graceful degradation when WebSocket unavailable

## Coverage Summary

**Total Test Methods:** ~25
**Passing:** ~20 (estimated)
**Not Yet Implemented:** ~15 (identified gaps)

## Adding New Tests

When adding a new feature, add tests to the appropriate file:

1. **Authentication changes?** → `test_auth.py`
2. **Check-in workflow?** → `test_checkin_flow.py`
3. **Check-out workflow?** → `test_checkout_flow.py`
4. **QR page changes?** → `test_qr_page.py`
5. **Print queue changes?** → `test_print_queue.py`
6. **Translation/i18n?** → `test_i18n.py`
7. **Navigation/UI?** → `test_navigation.py`

Update this document when adding tests!

## Running Specific Test Suites

```bash
# Run all E2E tests
make test-e2e

# Run specific suite
make test-auth
make test-checkin
make test-checkout
make test-qr
make test-print
make test-i18n
make test-navigation

# Run against production
make test-e2e-prod
```

## Known Gaps

Priority items to add test coverage for:
1. **Undo checkout within 5-minute window** - Important workflow
2. **Bulk family check-in** - Common use case
3. **WebSocket real-time updates** - Critical for multi-station
4. **Supervised check-in** - Planned feature
5. **Session filtering in print queue** - Already implemented
6. **Complete QR page workflow** - Partial coverage only

## Migration Status

| Old Test File | Migrated To | Status |
|--------------|-------------|--------|
| test_selenium_full_flows.py | test_checkin_flow.py, test_checkout_flow.py, test_i18n.py | ✅ Partial |
| test_selenium_comprehensive.py | test_navigation.py, test_auth.py | ✅ Complete |
| test_qr_page_e2e.py | test_qr_page.py | ✅ Complete |
| test_print_queue_e2e.py | test_print_queue.py | ✅ Partial |
| test_websocket.py | (not yet migrated) | ⏳ Pending |
| test_selenium_simple.py | (obsolete) | ❌ Delete |
| test_selenium_debug.py | (obsolete) | ❌ Delete |
| test_selenium_nocache.py | (obsolete) | ❌ Delete |
| test_selenium_login.py | test_auth.py | ✅ Complete |
| test_selenium_docker.py | (obsolete) | ❌ Delete |

Last updated: 2025-12-12
