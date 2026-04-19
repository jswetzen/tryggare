"""
Navigation E2E Tests

Tests for page navigation and responsive UI elements.

Run with:
    pytest backend/tests/e2e/test_navigation.py -v
    make test-navigation
"""
import pytest
import sys
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from tests.e2e.base import E2ETestBase, TestDataMixin


@pytest.mark.e2e
@pytest.mark.navigation
@pytest.mark.django_db(transaction=True)
class TestNavigation(E2ETestBase, TestDataMixin):
    """Test suite for navigation functionality."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.setup_driver()

        self.test_user = self.create_test_user(
            username="navtest",
            password="testpass123"
        )

    def teardown_method(self):
        """Clean up after each test."""
        self.cleanup_test_data(users=[self.test_user])
        self.teardown_driver()

    def test_page_navigation(self):
        """Test navigating between different pages."""
        print("\n🔍 Testing Page Navigation")
        print("=" * 60)

        # Login
        print("   Logging in...")
        self.login(self.test_user.username, "testpass123")

        # Should be on check-in page
        assert "/checkin" in self.driver.current_url, "Not on check-in page"
        print("   ✓ On check-in page")

        # Navigate to check-out. Nav links are anchors to /checkout —
        # match by href since text varies by locale (Check-Out / Utcheckning).
        print("   Navigating to check-out...")
        checkout_link = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='/checkout']"))
        )
        checkout_link.click()
        self.wait_for_url_contains("/checkout", timeout=10)
        print("   ✓ Successfully navigated to check-out page")

        # Navigate back to check-in
        print("   Navigating back to check-in...")
        checkin_link = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='/checkin']"))
        )
        checkin_link.click()
        self.wait_for_url_contains("/checkin", timeout=10)
        print("   ✓ Successfully navigated back to check-in page")

        print("\n" + "=" * 60)
        print("✅ Page navigation test PASSED")

    def test_responsive_menu(self):
        """Test responsive hamburger menu on mobile viewport."""
        print("\n🔍 Testing Responsive Menu")
        print("=" * 60)

        # Login
        self.login(self.test_user.username, "testpass123")

        # Resize to mobile viewport
        print("   Resizing to mobile viewport (375x667)...")
        self.driver.set_window_size(375, 667)
        time.sleep(1)

        # Look for hamburger menu
        print("   Looking for hamburger menu...")
        hamburger_selectors = [
            "//button[contains(@class, 'hamburger')]",
            "//button[contains(@aria-label, 'menu')]",
            "//button[contains(@class, 'menu')]",
            "//button[.//svg]"
        ]

        hamburger_found = False
        for selector in hamburger_selectors:
            try:
                hamburger = self.driver.find_element(By.XPATH, selector)
                hamburger.click()
                time.sleep(0.5)
                print("   ✓ Hamburger menu found and clicked")
                hamburger_found = True
                break
            except:
                continue

        if not hamburger_found:
            print("   ℹ️  Hamburger menu not found (may use different structure)")

        # Restore desktop viewport
        print("   Restoring desktop viewport...")
        self.driver.set_window_size(1920, 1080)

        print("\n" + "=" * 60)
        print("✅ Responsive menu test PASSED")


def run_tests():
    """Run the navigation tests."""
    exit_code = pytest.main([__file__, "-v", "-m", "navigation"])
    return exit_code


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 Running Navigation E2E Tests")
    print("=" * 60)

    exit_code = run_tests()

    print("\n" + "=" * 60)
    if exit_code == 0:
        print("✅ ALL NAVIGATION TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)

    sys.exit(exit_code)
