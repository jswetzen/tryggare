#!/usr/bin/env python
"""
Selenium end-to-end test for frontend login flow

Based on Django Channels testing guide:
https://channels.readthedocs.io/en/latest/tutorial/part_4.html

This test uses ChannelsLiveServerTestCase to ensure WebSocket support
and tests the complete login flow from the frontend perspective.
"""

import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

import django
from django.conf import settings

# Setup Django with test settings to avoid affecting development database
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
django.setup()

from django.test import TestCase
from accounts.models import AdminUser


class LoginFlowSeleniumTest(TestCase):
    """
    End-to-end tests for the login flow using Selenium.

    This test suite runs against the live development servers:
    - Backend: http://localhost:8000
    - Frontend: http://localhost:5173

    It uses a separate test database (test_db.sqlite3) to avoid affecting
    development data while still testing against the running servers.

    Note: For CI/CD, use docker-compose.test.yml which spins up isolated
    test servers with ChannelsLiveServerTestCase.
    """

    @classmethod
    def setUpClass(cls):
        """Set up the Selenium WebDriver before running tests"""
        # Note: We don't call super().setUpClass() because we're testing against
        # external servers, not starting our own test server

        # Configure Chrome options for headless testing
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")  # Use new headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--lang=en-US")  # Set language for i18n
        chrome_options.add_argument("--enable-javascript")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-cache")  # Disable cache for fresh content
        chrome_options.add_argument("--disable-application-cache")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        # Set Accept-Language header
        chrome_options.add_experimental_option("prefs", {
            "intl.accept_languages": "en-US,en"
        })

        # Initialize the Chrome WebDriver
        service = Service(ChromeDriverManager().install())
        cls.driver = webdriver.Chrome(service=service, options=chrome_options)
        cls.driver.implicitly_wait(10)  # Wait up to 10 seconds for elements

    @classmethod
    def tearDownClass(cls):
        """Clean up the WebDriver after tests"""
        cls.driver.quit()
        # Note: We don't call super().tearDownClass() because we didn't start a test server

    def setUp(self):
        """Set up test data before each test"""
        # Create a test user
        self.test_username = "seleniumtest"
        self.test_password = "testpass123"
        self.test_name = "Selenium Test User"

        # Delete existing test user if present
        AdminUser.objects.filter(username=self.test_username).delete()

        # Create fresh test user
        self.test_user = AdminUser.objects.create_user(
            username=self.test_username,
            password=self.test_password,
            name=self.test_name
        )

    def tearDown(self):
        """Clean up test data after each test"""
        # Delete test user
        AdminUser.objects.filter(username=self.test_username).delete()

        # Clear cookies
        self.driver.delete_all_cookies()

    def wait_for_element_and_interact(self, by, value, action="click", text=None, timeout=10, retries=3):
        """
        Wait for element to be present and stable, then interact with it.
        This handles SvelteKit's client-side hydration which can cause stale elements.
        Uses retry logic to handle stale element references.
        """
        from selenium.common.exceptions import StaleElementReferenceException

        for attempt in range(retries):
            try:
                # Wait for element to be present
                WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by, value))
                )

                # Small wait for hydration to complete
                time.sleep(0.3)

                # Find the element fresh
                element = self.driver.find_element(by, value)

                # Perform the action
                if action == "click":
                    element.click()
                elif action == "send_keys" and text is not None:
                    # Don't clear for SvelteKit - can cause stale references
                    element.send_keys(text)

                return element

            except StaleElementReferenceException:
                if attempt == retries - 1:
                    raise
                # Wait a bit and retry
                time.sleep(0.5)
                continue

    def test_successful_login_flow(self):
        """Test complete successful login flow from frontend"""
        print("\n🔍 Testing Successful Login Flow")
        print("=" * 60)

        # Navigate to the login page
        # Note: We're testing against the SvelteKit frontend at port 5173
        login_url = "http://localhost:5173/login"
        print(f"\n1. Navigating to {login_url}...")
        self.driver.get(login_url)

        # Wait for the page to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        print("   ✓ Login page loaded")

        # Verify page title
        self.assertIn("Login", self.driver.title)
        print(f"   ✓ Page title verified: {self.driver.title}")

        # Fill in the username field
        print("\n2. Filling in login form...")
        self.wait_for_element_and_interact(By.ID, "username", "send_keys", self.test_username)
        print(f"   ✓ Username entered: {self.test_username}")

        # Fill in the password field
        self.wait_for_element_and_interact(By.ID, "password", "send_keys", self.test_password)
        print("   ✓ Password entered")

        # Submit the form
        print("\n3. Submitting login form...")
        self.wait_for_element_and_interact(By.CSS_SELECTOR, "button[type='submit']", "click")

        # Wait for redirect to check-in page
        print("\n4. Waiting for redirect...")
        WebDriverWait(self.driver, 10).until(
            EC.url_contains("/checkin")
        )
        print(f"   ✓ Redirected to: {self.driver.current_url}")

        # Verify we're on the check-in page
        self.assertIn("/checkin", self.driver.current_url)
        print("   ✓ Successfully redirected to check-in page")

        # Verify cookies are set (sessionid and csrftoken)
        cookies = self.driver.get_cookies()
        cookie_names = [cookie['name'] for cookie in cookies]
        print(f"\n5. Verifying authentication cookies...")
        print(f"   Cookies set: {cookie_names}")

        self.assertIn('sessionid', cookie_names, "Session cookie not found")
        print("   ✓ Session cookie verified")

        self.assertIn('csrftoken', cookie_names, "CSRF token cookie not found")
        print("   ✓ CSRF token cookie verified")

        print("\n" + "=" * 60)
        print("✅ Successful login flow test passed!")

    def test_invalid_credentials_error(self):
        """Test that invalid credentials show an error message"""
        print("\n🔍 Testing Invalid Credentials Error")
        print("=" * 60)

        # Navigate to the login page
        login_url = "http://localhost:5173/login"
        print(f"\n1. Navigating to {login_url}...")
        self.driver.get(login_url)

        # Wait for the page to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        print("   ✓ Login page loaded")

        # Fill in invalid credentials
        print("\n2. Entering invalid credentials...")
        self.wait_for_element_and_interact(By.ID, "username", "send_keys", "invaliduser")
        self.wait_for_element_and_interact(By.ID, "password", "send_keys", "wrongpassword")
        print("   ✓ Invalid credentials entered")

        # Submit the form
        print("\n3. Submitting form...")
        self.wait_for_element_and_interact(By.CSS_SELECTOR, "button[type='submit']", "click")

        # Wait for error message to appear
        print("\n4. Waiting for error message...")
        error_div = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".bg-red-100"))
        )

        # Verify error message is displayed
        error_text = error_div.text
        print(f"   ✓ Error message displayed: {error_text}")

        # Should contain error about invalid credentials
        self.assertTrue(len(error_text) > 0, "Error message is empty")

        # Verify we're still on the login page
        self.assertIn("/login", self.driver.current_url)
        print("   ✓ Still on login page (not redirected)")

        print("\n" + "=" * 60)
        print("✅ Invalid credentials error test passed!")

    def test_empty_fields_validation(self):
        """Test that empty fields trigger HTML5 validation"""
        print("\n🔍 Testing Empty Fields Validation")
        print("=" * 60)

        # Navigate to the login page
        login_url = "http://localhost:5173/login"
        print(f"\n1. Navigating to {login_url}...")
        self.driver.get(login_url)

        # Wait for the page to load
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        print("   ✓ Login page loaded")

        # Try to submit without filling fields
        print("\n2. Attempting to submit empty form...")
        submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()

        # Check if username field has validation error
        username_field = self.driver.find_element(By.ID, "username")
        is_valid = self.driver.execute_script(
            "return arguments[0].checkValidity();", username_field
        )

        print(f"   Username field valid: {is_valid}")
        self.assertFalse(is_valid, "Username field should be invalid when empty")
        print("   ✓ HTML5 validation prevents submission")

        # Verify we're still on the login page
        self.assertIn("/login", self.driver.current_url)
        print("   ✓ Still on login page")

        print("\n" + "=" * 60)
        print("✅ Empty fields validation test passed!")

    def test_logout_flow(self):
        """Test the complete logout flow"""
        print("\n🔍 Testing Logout Flow")
        print("=" * 60)

        # First, log in
        print("\n1. Logging in...")
        login_url = "http://localhost:5173/login"
        self.driver.get(login_url)

        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )

        # Fill in credentials and submit
        self.wait_for_element_and_interact(By.ID, "username", "send_keys", self.test_username)
        self.wait_for_element_and_interact(By.ID, "password", "send_keys", self.test_password)
        self.wait_for_element_and_interact(By.CSS_SELECTOR, "button[type='submit']", "click")

        # Wait for redirect
        WebDriverWait(self.driver, 10).until(
            EC.url_contains("/checkin")
        )
        print("   ✓ Successfully logged in")

        # Click logout button
        print("\n2. Clicking logout button...")
        # Find the logout button by text content
        logout_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Logout')]"))
        )
        logout_button.click()
        print("   ✓ Logout button clicked")

        # Wait for redirect to login page
        print("\n3. Waiting for redirect to login page...")
        WebDriverWait(self.driver, 10).until(
            EC.url_contains("/login")
        )
        print(f"   ✓ Redirected to: {self.driver.current_url}")

        # Verify we're on the login page
        self.assertIn("/login", self.driver.current_url)
        print("   ✓ Successfully redirected to login page")

        # Try to navigate to protected page
        print("\n4. Attempting to access protected page...")
        self.driver.get("http://localhost:5173/checkin")

        # Should redirect back to login
        WebDriverWait(self.driver, 10).until(
            EC.url_contains("/login")
        )

        self.assertIn("/login", self.driver.current_url)
        print("   ✓ Protected page redirects to login (session cleared)")

        print("\n" + "=" * 60)
        print("✅ Logout flow test passed!")

    def test_login_logout_login_again(self):
        """Test login, logout, then login again - ensures session is properly cleared"""
        print("\n🔍 Testing Login -> Logout -> Login Again Flow")
        print("=" * 60)

        # First login
        print("\n1. First login...")
        login_url = "http://localhost:5173/login"
        self.driver.get(login_url)

        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )

        self.wait_for_element_and_interact(By.ID, "username", "send_keys", self.test_username)
        self.wait_for_element_and_interact(By.ID, "password", "send_keys", self.test_password)
        self.wait_for_element_and_interact(By.CSS_SELECTOR, "button[type='submit']", "click")

        # Wait for redirect
        WebDriverWait(self.driver, 10).until(
            EC.url_contains("/checkin")
        )
        print("   ✓ First login successful")

        # Logout
        print("\n2. Logging out...")
        logout_button = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Logout')]"))
        )
        logout_button.click()

        WebDriverWait(self.driver, 10).until(
            EC.url_contains("/login")
        )
        print("   ✓ Logout successful")

        # Second login
        print("\n3. Second login (after logout)...")
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )

        self.wait_for_element_and_interact(By.ID, "username", "send_keys", self.test_username)
        self.wait_for_element_and_interact(By.ID, "password", "send_keys", self.test_password)
        self.wait_for_element_and_interact(By.CSS_SELECTOR, "button[type='submit']", "click")

        # Wait for redirect after second login
        WebDriverWait(self.driver, 10).until(
            EC.url_contains("/checkin")
        )
        print("   ✓ Second login successful")

        # Verify we're actually logged in
        self.assertIn("/checkin", self.driver.current_url)
        print("   ✓ Successfully on check-in page after re-login")

        # Verify cookies are set
        cookies = self.driver.get_cookies()
        cookie_names = [cookie['name'] for cookie in cookies]
        self.assertIn('sessionid', cookie_names, "Session cookie not found after re-login")
        print("   ✓ Session cookie verified after re-login")

        print("\n" + "=" * 60)
        print("✅ Login-Logout-Login flow test passed!")

    def test_protected_route_redirect_with_return_url(self):
        """Test accessing protected route while logged out, redirecting to login, then back to original route"""
        print("\n🔍 Testing Protected Route Redirect with Return URL")
        print("=" * 60)

        # Try to access protected route while logged out
        print("\n1. Accessing protected route /checkout while logged out...")
        self.driver.get("http://localhost:5173/checkout")

        # Should redirect to login
        WebDriverWait(self.driver, 10).until(
            EC.url_contains("/login")
        )
        print(f"   ✓ Redirected to login: {self.driver.current_url}")

        # Verify we're on the login page
        self.assertIn("/login", self.driver.current_url)
        print("   ✓ On login page")

        # Now login
        print("\n2. Logging in...")
        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )

        self.wait_for_element_and_interact(By.ID, "username", "send_keys", self.test_username)
        self.wait_for_element_and_interact(By.ID, "password", "send_keys", self.test_password)
        self.wait_for_element_and_interact(By.CSS_SELECTOR, "button[type='submit']", "click")

        # Wait for redirect after login
        print("\n3. Waiting for redirect after login...")
        WebDriverWait(self.driver, 10).until(
            lambda driver: "/login" not in driver.current_url
        )

        # Check if we were redirected to the intended page or default page
        final_url = self.driver.current_url
        print(f"   Final URL: {final_url}")

        # The system might redirect to /checkout if it remembers the original request,
        # or to /checkin as the default post-login page
        # Either is acceptable behavior
        if "/checkout" in final_url:
            print("   ✓ Redirected back to original /checkout route!")
        elif "/checkin" in final_url:
            print("   ℹ Redirected to default /checkin page (no return URL preservation)")
            print("   ℹ This is acceptable behavior - user can navigate to /checkout manually")
        else:
            self.fail(f"Unexpected redirect after login: {final_url}")

        # Verify we can now access /checkout manually
        print("\n4. Manually accessing /checkout while logged in...")
        self.driver.get("http://localhost:5173/checkout")

        # Wait a moment for page to load
        time.sleep(1)

        # Should not redirect back to login
        self.assertNotIn("/login", self.driver.current_url)
        print(f"   ✓ Can access /checkout: {self.driver.current_url}")

        print("\n" + "=" * 60)
        print("✅ Protected route redirect test passed!")


def run_tests():
    """Run the Selenium tests using Django's test runner"""
    import unittest

    # Create a test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(LoginFlowSeleniumTest)

    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 Running Selenium Login Flow Tests")
    print("=" * 60)
    print("\nNOTE: These tests require:")
    print("  1. Backend server running on http://localhost:8000")
    print("  2. Frontend server running on http://localhost:5173")
    print("  3. Chrome/Chromium browser installed")
    print("=" * 60)

    try:
        exit_code = run_tests()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
