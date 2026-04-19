"""
QR Scan Check-In E2E Tests

Tests for the QR-scan-based family lookup and check-in UI behaviour.
Bypasses the physical camera by:
  1. Calling /api/families/by-ticket/ directly from the browser via
     execute_async_script (same-origin fetch, uses session cookies).
  2. Using the search box to surface families and testing expand/collapse
     independently of QR scanning.

Run with:
    pytest backend/tests/e2e/test_qr_scan_checkin.py -v -s
    make test-qr-scan
"""
import pytest
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from tests.e2e.base import E2ETestBase, TestDataMixin
from events.models import EventTicket
from checkins.models import CheckInRecord


@pytest.mark.e2e
@pytest.mark.qrscan
@pytest.mark.django_db(transaction=True)
class TestQrScanCheckin(E2ETestBase, TestDataMixin):
    """E2E tests for QR scan check-in flow and family card expand/collapse."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.setup_driver()

        self.test_user = self.create_test_user(
            username="qrscantest",
            password="testpass123"
        )

        self.test_event, self.test_session = self.create_test_session(
            name="QR Test Session",
            is_active=True
        )

        self.test_family, self.test_parent = self.create_test_family(
            last_name="QRScanFamily"
        )

        self.test_child = self.create_test_child(
            self.test_family,
            first_name="QRKid"
        )

        EventTicket.objects.create(
            child=self.test_child,
            event=self.test_event,
            external_ticket_code="QRTEST_E2E"
        )

    def teardown_method(self):
        """Clean up after each test."""
        try:
            CheckInRecord.objects.filter(child=self.test_child).delete()
            EventTicket.objects.filter(external_ticket_code="QRTEST_E2E").delete()
        except Exception as e:
            print(f"   ⚠️  Cleanup warning: {e}")

        self.cleanup_test_data(
            users=[self.test_user],
            families=[self.test_family],
            children=[self.test_child],
            sessions=[self.test_session],
            events=[self.test_event]
        )
        self.teardown_driver()

    # ------------------------------------------------------------------ #
    # API-level tests (camera bypass using execute_async_script)          #
    # ------------------------------------------------------------------ #

    def test_by_ticket_api_returns_correct_family(self):
        """Bypasses camera: verifies /api/families/by-ticket/ returns the right family."""
        print("\n📷 Testing by-ticket API (camera bypass)")
        print("=" * 60)

        self.login(self.test_user.username, "testpass123")
        time.sleep(2)

        result = self.driver.execute_async_script("""
            var done = arguments[0];
            fetch(arguments[1] + '/api/families/by-ticket/?code=QRTEST_E2E', {credentials: 'include'})
              .then(function(r) {
                return r.json().then(function(data) {
                  done({status: r.status, data: data});
                });
              })
              .catch(function(err) { done({error: String(err)}); });
        """, self.config['backend_url'])

        print(f"   API response status: {result.get('status')}")
        assert "error" not in result, f"Fetch error: {result.get('error')}"
        assert result["status"] == 200, f"Expected 200, got {result['status']}: {result['data']}"
        assert result["data"]["last_name"] == "QRScanFamily", \
            f"Wrong family: {result['data'].get('last_name')}"
        assert len(result["data"]["children"]) == 1, \
            f"Expected 1 child, got {len(result['data']['children'])}"
        child = result["data"]["children"][0]
        assert child["first_name"] == "QRKid"

        print(f"   ✓ Family '{result['data']['last_name']}' returned correctly")
        print(f"   ✓ Child '{child['first_name']}' included in response")
        print("\n" + "=" * 60)
        print("✅ by-ticket API test PASSED")

    def test_by_ticket_api_unknown_code_returns_404(self):
        """Unknown ticket code returns 404 with correct error JSON."""
        print("\n📷 Testing by-ticket API — unknown code")
        print("=" * 60)

        self.login(self.test_user.username, "testpass123")
        time.sleep(2)

        result = self.driver.execute_async_script("""
            var done = arguments[0];
            fetch(arguments[1] + '/api/families/by-ticket/?code=DOESNOTEXIST_E2E', {credentials: 'include'})
              .then(function(r) {
                return r.json().then(function(data) {
                  done({status: r.status, data: data});
                });
              })
              .catch(function(err) { done({error: String(err)}); });
        """, self.config['backend_url'])

        assert "error" not in result, f"Fetch error: {result.get('error')}"
        assert result["status"] == 404, f"Expected 404, got {result['status']}"
        assert result["data"].get("error") == "not_found", \
            f"Wrong error payload: {result['data']}"

        print(f"   ✓ 404 returned with error='not_found'")
        print("\n" + "=" * 60)
        print("✅ Unknown code 404 test PASSED")

    def test_by_ticket_api_requires_auth(self):
        """Unauthenticated browser fetch returns 403."""
        print("\n📷 Testing by-ticket API — unauthenticated")
        print("=" * 60)

        # Navigate without logging in so there's no session cookie
        self.driver.get(f"{self.config['frontend_url']}/login")
        time.sleep(1)

        result = self.driver.execute_async_script("""
            var done = arguments[0];
            fetch(arguments[1] + '/api/families/by-ticket/?code=QRTEST_E2E', {credentials: 'include'})
              .then(function(r) {
                // 403 / 401 may come back as HTML or JSON depending on auth layer;
                // return text and let the caller decide.
                return r.text().then(function(body) {
                  var data = null;
                  try { data = JSON.parse(body); } catch (e) { data = body; }
                  done({status: r.status, data: data});
                });
              })
              .catch(function(err) { done({error: String(err)}); });
        """, self.config['backend_url'])

        assert "error" not in result, f"Fetch error: {result.get('error')}"
        assert result["status"] == 403, f"Expected 403, got {result['status']}"

        print(f"   ✓ 403 returned for unauthenticated request")
        print("\n" + "=" * 60)
        print("✅ Auth required test PASSED")

    # ------------------------------------------------------------------ #
    # UI tests: expand/collapse independent of QR                         #
    # ------------------------------------------------------------------ #

    def test_family_card_expands_on_click(self):
        """
        Clicking the family toggle button reveals child rows.
        This is the foundational expand/collapse behaviour triggered by QR scan.
        """
        print("\n📷 Testing family card expand/collapse")
        print("=" * 60)

        self.login(self.test_user.username, "testpass123")
        time.sleep(3)

        # Search for the family to surface it in the list
        search_input = self.wait_for_element(By.CSS_SELECTOR, "input[type='text']")
        search_input.clear()
        search_input.send_keys(self.test_family.last_name)

        search_button = self.wait_for_element(
            By.XPATH,
            "//button[contains(text(), 'Search') or contains(text(), 'Sök')]"
        )
        search_button.click()
        time.sleep(2)

        family_id = str(self.test_family.id)
        child_id = str(self.test_child.id)

        # Family card must be present
        family_card = self.wait_for_element(
            By.CSS_SELECTOR,
            f"[data-testid='family-card-{family_id}']",
            timeout=10
        )
        assert family_card is not None, "Family card not found"
        print(f"   ✓ Family card visible: family-card-{family_id}")

        # Before expanding: child row should not be visible
        child_rows = self.driver.find_elements(
            By.CSS_SELECTOR, f"[data-testid='child-row-{child_id}']"
        )
        visible_before = [r for r in child_rows if r.is_displayed()]
        assert len(visible_before) == 0, \
            f"Child row should be hidden before expand, but {len(visible_before)} visible"
        print(f"   ✓ Child row hidden before expand")

        # Click toggle button
        toggle = self.wait_for_element(
            By.CSS_SELECTOR,
            f"[data-testid='family-toggle-button-{family_id}']",
            timeout=10
        )
        toggle.click()
        time.sleep(1)

        # After expanding: child row must be visible
        child_rows = self.driver.find_elements(
            By.CSS_SELECTOR, f"[data-testid='child-row-{child_id}']"
        )
        visible_after = [r for r in child_rows if r.is_displayed()]
        assert len(visible_after) > 0, \
            "Child row should be visible after expand"
        print(f"   ✓ Child row visible after expand")

        # Click toggle again to collapse
        toggle.click()
        time.sleep(1)

        child_rows = self.driver.find_elements(
            By.CSS_SELECTOR, f"[data-testid='child-row-{child_id}']"
        )
        visible_collapsed = [r for r in child_rows if r.is_displayed()]
        assert len(visible_collapsed) == 0, \
            "Child row should be hidden after collapse"
        print(f"   ✓ Child row hidden after collapse")

        print("\n" + "=" * 60)
        print("✅ Family card expand/collapse test PASSED")

    def test_family_visible_in_initial_load(self):
        """
        Family with unchecked-in children should appear in the initial page load
        (before any search). This is the prerequisite for QR scan to find the card.
        """
        print("\n📷 Testing family visible on initial load")
        print("=" * 60)

        self.login(self.test_user.username, "testpass123")
        time.sleep(3)

        page_source = self.driver.page_source
        assert self.test_family.last_name in page_source, \
            f"Family '{self.test_family.last_name}' not visible on initial load"
        print(f"   ✓ Family '{self.test_family.last_name}' visible on initial load")

        print("\n" + "=" * 60)
        print("✅ Family visibility test PASSED")


def run_tests():
    """Run the QR scan check-in tests."""
    import sys
    exit_code = pytest.main([__file__, "-v", "-m", "qrscan"])
    return exit_code


if __name__ == "__main__":
    import sys
    print("\n" + "=" * 60)
    print("🚀 Running QR Scan Check-In E2E Tests")
    print("=" * 60)
    exit_code = run_tests()
    print("\n" + "=" * 60)
    if exit_code == 0:
        print("✅ ALL QR SCAN TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)
    sys.exit(exit_code)
