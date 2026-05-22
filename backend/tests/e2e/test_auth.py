"""
Authentication E2E Tests

Tests for login, logout, and session management functionality.

Run with:
    pytest backend/tests/e2e/test_auth.py -v
    make test-auth
"""

import pytest
import sys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Import base classes
try:
    from tests.e2e.base import E2ETestBase, TestDataMixin
except ImportError:
    # Fallback for standalone execution
    from .base import E2ETestBase, TestDataMixin


@pytest.mark.e2e
@pytest.mark.auth
@pytest.mark.django_db(transaction=True)
class TestAuthentication(E2ETestBase, TestDataMixin):
    """Test suite for authentication flows."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.setup_driver()
        self.test_user = self.create_test_user(
            username="authtest", password="testpass123", name="Auth Test User"
        )

    def teardown_method(self):
        """Clean up after each test."""
        self.cleanup_test_data(users=[self.test_user])
        self.teardown_driver()

    def test_login_success(self):
        """Test successful login with valid credentials."""
        print("\n🔍 Testing Login Success")
        print("=" * 60)

        # Navigate to login page
        login_url = f"{self.config['frontend_url']}/login"
        self.driver.get(login_url)

        # Wait for login form
        username_field = self.wait_for_element(By.ID, "username")
        password_field = self.wait_for_element(By.ID, "password")

        print(f"   Logging in as {self.test_user.username}...")

        # Fill in credentials
        username_field.send_keys(self.test_user.username)
        password_field.send_keys("testpass123")

        # Submit
        submit_button = self.wait_for_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()

        # Wait for redirect to check-in page
        self.wait_for_url_contains("/checkin", timeout=10)

        # Verify we're on the check-in page
        assert "/checkin" in self.driver.current_url, (
            f"Expected redirect to /checkin, got {self.driver.current_url}"
        )

        print("   ✓ Login successful")
        print("   ✓ Redirected to check-in page")
        print("\n" + "=" * 60)
        print("✅ Login success test PASSED")

    def test_login_invalid_credentials(self):
        """Test login failure with invalid credentials."""
        print("\n🔍 Testing Login with Invalid Credentials")
        print("=" * 60)

        # Navigate to login page
        login_url = f"{self.config['frontend_url']}/login"
        self.driver.get(login_url)

        # Wait for login form
        username_field = self.wait_for_element(By.ID, "username")
        password_field = self.wait_for_element(By.ID, "password")

        print("   Attempting login with wrong password...")

        # Fill in with wrong password
        username_field.send_keys(self.test_user.username)
        password_field.send_keys("wrongpassword")

        # Submit
        submit_button = self.wait_for_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()

        # Wait a moment for any redirect or error message
        import time

        time.sleep(2)

        # Should still be on login page
        current_url = self.driver.current_url
        assert "/login" in current_url, f"Expected to stay on /login, got {current_url}"

        print("   ✓ Stayed on login page (no redirect)")

        # Check for error message in page
        page_source = self.driver.page_source
        # Look for common error messages
        has_error = any(
            msg in page_source.lower()
            for msg in ["invalid", "incorrect", "wrong", "failed", "error"]
        )

        if has_error:
            print("   ✓ Error message displayed")
        else:
            print("   ⚠️  No clear error message found (may still be correct behavior)")

        print("\n" + "=" * 60)
        print("✅ Invalid credentials test PASSED")

    def test_logout(self):
        """Test logout functionality."""
        print("\n🔍 Testing Logout")
        print("=" * 60)

        # First, login
        print("   Logging in...")
        success = self.login(self.test_user.username, "testpass123")
        assert success, "Login failed"

        # Find and click logout button
        print("   Finding logout button...")
        try:
            logout_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//button[contains(text(), 'Logout') or contains(text(), 'Log out') "
                        "or contains(text(), 'Logga ut')]",
                    )
                )
            )
            print("   ✓ Logout button found")

            print("   Clicking logout...")
            logout_button.click()

            # Wait for redirect to login page
            self.wait_for_url_contains("/login", timeout=10)

            assert "/login" in self.driver.current_url, (
                f"Expected redirect to /login after logout, got {self.driver.current_url}"
            )

            print("   ✓ Redirected to login page")
            print("   ✓ Logout successful")

        except Exception as e:
            print(f"   ⚠️  Could not complete logout test: {e}")
            self.save_screenshot("logout_test_failure")
            raise

        print("\n" + "=" * 60)
        print("✅ Logout test PASSED")

    def test_session_persistence(self):
        """Test that login session persists across page navigation."""
        print("\n🔍 Testing Session Persistence")
        print("=" * 60)

        # Login
        print("   Logging in...")
        success = self.login(self.test_user.username, "testpass123")
        assert success, "Login failed"

        # Navigate to different pages
        print("   Navigating to checkout page...")
        checkout_url = f"{self.config['frontend_url']}/checkout"
        self.driver.get(checkout_url)

        import time

        time.sleep(2)

        # Should not redirect to login
        current_url = self.driver.current_url
        assert "/login" not in current_url, "Session lost - redirected to login page"

        print("   ✓ Session persisted to checkout page")

        # Navigate back to check-in
        print("   Navigating back to check-in page...")
        checkin_url = f"{self.config['frontend_url']}/checkin"
        self.driver.get(checkin_url)

        time.sleep(2)

        # Should still be logged in
        current_url = self.driver.current_url
        assert "/login" not in current_url, "Session lost - redirected to login page"

        print("   ✓ Session persisted to check-in page")

        print("\n" + "=" * 60)
        print("✅ Session persistence test PASSED")


def run_tests():
    """Run the authentication tests."""
    exit_code = pytest.main([__file__, "-v", "-m", "auth"])
    return exit_code


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 Running Authentication E2E Tests")
    print("=" * 60)

    exit_code = run_tests()

    print("\n" + "=" * 60)
    if exit_code == 0:
        print("✅ ALL AUTHENTICATION TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)

    sys.exit(exit_code)
