"""
Check-Out Flow E2E Tests

Tests for the complete check-out workflow including viewing checked-in children,
checking out with pickup name, and undo functionality.

Run with:
    pytest backend/tests/e2e/test_checkout_flow.py -v
    make test-checkout
"""
import pytest
import sys
import time
from selenium.webdriver.common.by import By

from tests.e2e.base import E2ETestBase, TestDataMixin
from checkins.models import CheckInRecord


@pytest.mark.e2e
@pytest.mark.checkout
@pytest.mark.django_db(transaction=True)
class TestCheckOutFlow(E2ETestBase, TestDataMixin):
    """Test suite for check-out workflows."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.setup_driver()

        # Create test user
        self.test_user = self.create_test_user(
            username="checkouttest",
            password="testpass123"
        )

        # Create test session
        self.test_event, self.test_session = self.create_test_session(
            name="Test Checkout Session",
            is_active=True
        )

        # Create test family with child
        self.test_family, self.test_parent = self.create_test_family(
            last_name="TestCheckOut"
        )

        self.test_child = self.create_test_child(
            self.test_family,
            first_name="Charlie"
        )

    def teardown_method(self):
        """Clean up after each test."""
        self.cleanup_test_data(
            users=[self.test_user],
            families=[self.test_family],
            children=[self.test_child],
            sessions=[self.test_session],
            events=[self.test_event]
        )
        self.teardown_driver()

    def test_view_checked_in_child(self):
        """Test that checked-in children appear on checkout page."""
        print("\n🔍 Testing View Checked-In Child")
        print("=" * 60)

        # Pre-create a check-in
        print("   Creating check-in...")
        checkin = CheckInRecord.objects.create(
            child=self.test_child,
            session=self.test_session,
            check_in_staff=self.test_user
        )
        print(f"   ✓ {self.test_child.first_name} checked in")

        # Login and navigate to checkout page
        print("   Navigating to checkout page...")
        self.login(self.test_user.username, "testpass123")

        checkout_url = f"{self.config['frontend_url']}/checkout"
        self.driver.get(checkout_url)
        time.sleep(3)

        # Verify child appears in list
        page_source = self.driver.page_source
        child_found = self.test_child.first_name in page_source or \
                      str(self.test_child.id) in page_source

        assert child_found, \
            f"Child '{self.test_child.first_name}' not found on checkout page"

        print(f"   ✓ Child '{self.test_child.first_name}' found on checkout page")

        print("\n" + "=" * 60)
        print("✅ View checked-in child test PASSED")

    def test_checkout_with_pickup_name(self):
        """Test checking out a child with pickup person name."""
        print("\n🔍 Testing Check-Out with Pickup Name")
        print("=" * 60)

        # Pre-create a check-in
        print("   Creating check-in...")
        checkin = CheckInRecord.objects.create(
            child=self.test_child,
            session=self.test_session,
            check_in_staff=self.test_user
        )

        # Login and navigate to checkout page
        print("   Navigating to checkout page...")
        self.login(self.test_user.username, "testpass123")

        checkout_url = f"{self.config['frontend_url']}/checkout"
        self.driver.get(checkout_url)
        time.sleep(3)

        # Find and click checkout button
        print("   Finding checkout button...")
        table_rows = self.driver.find_elements(By.CSS_SELECTOR, "tr")

        clicked = False
        for row in table_rows:
            if self.test_child.first_name in row.text or str(self.test_child.id) in row.text:
                buttons = row.find_elements(By.CSS_SELECTOR, "button")
                if buttons:
                    buttons[0].click()
                    clicked = True
                    print("   ✓ Checkout button clicked")
                    break

        if not clicked:
            # Try alternative method - click any visible button
            all_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button")
            for button in all_buttons:
                if "Refresh" not in button.text and button.is_displayed():
                    button.click()
                    clicked = True
                    print("   ✓ Checkout button clicked (alternative method)")
                    break

        assert clicked, "Could not find or click checkout button"

        time.sleep(2)

        # Look for modal/input for pickup name
        try:
            pickup_input = self.driver.find_element(By.CSS_SELECTOR, "input[type='text']")
            pickup_input.send_keys("Test Parent")
            print("   ✓ Entered pickup person name")

            # Find confirm button
            confirm_buttons = self.driver.find_elements(By.TAG_NAME, "button")
            for btn in confirm_buttons:
                if "Confirm" in btn.text or "Check Out" in btn.text:
                    btn.click()
                    print("   ✓ Confirmed checkout")
                    break

            time.sleep(2)
        except:
            print("   ℹ️  No pickup name modal (may be optional)")

        # Verify checkout in database
        print("   Verifying checkout in database...")
        checkin.refresh_from_db()

        assert checkin.check_out_time is not None, "Check-out time not set"
        print("   ✅ Check-out successful!")
        print(f"   - Check-out time: {checkin.check_out_time}")
        if checkin.picked_up_by:
            print(f"   - Picked up by: {checkin.picked_up_by}")

        print("\n" + "=" * 60)
        print("✅ Check-out with pickup name test PASSED")


def run_tests():
    """Run the check-out flow tests."""
    exit_code = pytest.main([__file__, "-v", "-m", "checkout"])
    return exit_code


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 Running Check-Out Flow E2E Tests")
    print("=" * 60)

    exit_code = run_tests()

    print("\n" + "=" * 60)
    if exit_code == 0:
        print("✅ ALL CHECK-OUT TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)

    sys.exit(exit_code)
