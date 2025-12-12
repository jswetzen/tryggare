# Archived E2E Tests

This directory contains the old E2E/Selenium test files that have been replaced by the new organized test structure in `tests/e2e/`.

## Why Archived?

These files were reorganized on 2025-12-12 to:
- Improve test organization
- Reduce duplication
- Make test coverage clear
- Simplify running specific test suites

## Migration Status

| Old File | New Location | Status |
|----------|-------------|--------|
| test_selenium_full_flows.py | tests/e2e/test_checkin_flow.py, test_checkout_flow.py, test_i18n.py | Migrated |
| test_selenium_comprehensive.py | tests/e2e/test_navigation.py, test_auth.py | Migrated |
| test_qr_page_e2e.py | tests/e2e/test_qr_page.py | Migrated |
| test_print_queue_e2e.py | tests/e2e/test_print_queue.py | Migrated |
| test_selenium_login.py | tests/e2e/test_auth.py | Migrated |
| test_selenium_simple.py | Obsolete | Deleted |
| test_selenium_debug.py | Obsolete | Deleted |
| test_selenium_nocache.py | Obsolete | Deleted |
| test_selenium_docker.py | Obsolete | Deleted |
| test_01_login.py | Obsolete | Deleted |
| test_simple_login.py | Obsolete | Deleted |
| test_auth.py (old) | Obsolete | Deleted |
| test_new_features.py | Obsolete | Deleted |
| test_recently_printed_fix.py | Obsolete | Deleted |
| test_timer_countdown.py | Obsolete | Deleted |
| test_prod_debug.py | Obsolete | Deleted |

## Using New Tests

See the main test documentation:
- **New test structure:** `backend/tests/e2e/`
- **Coverage matrix:** `backend/tests/e2e/TEST_COVERAGE.md`
- **Reorganization plan:** `docs/E2E_TEST_REORGANIZATION.md`
- **Run tests:** `cd backend && make test-e2e`

## Restoration (if needed)

If you need to restore old tests:
```bash
cd /workspace/check-ins/backend
cp OLD_TESTS/*.py .
```

## Cleanup

These files can be safely deleted after confirming new tests work:
```bash
rm -rf /workspace/check-ins/backend/OLD_TESTS
```

---

**Archived:** 2025-12-12
**Status:** Safe to delete after new tests verified
