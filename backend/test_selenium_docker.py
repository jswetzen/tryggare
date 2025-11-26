#!/usr/bin/env python
"""
Selenium E2E tests for Docker Compose test environment.

This version uses remote Selenium WebDriver to connect to a Selenium Grid
running in a Docker container. It's designed for CI/CD and automated testing.
"""

import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

import django

# Setup Django with test settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
django.setup()

from django.test import TestCase
from accounts.models import AdminUser


class LoginFlowSeleniumTest(TestCase):
    """
    End-to-end tests for the login flow using Selenium Grid.

    This test suite runs in Docker Compose with isolated services:
    - Backend: http://backend-test:8000
    - Frontend: http://frontend-test:5173
    - Selenium: http://selenium-chrome:4444
    """

    @classmethod
    def setUpClass(cls):
        """Set up the Remote Selenium WebDriver"""
        # Get URLs from environment (set by docker-compose.test.yml)
        cls.selenium_hub = os.getenv("SELENIUM_HUB_URL", "http://localhost:4444")
        cls.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        cls.backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

        print(f"\n🔧 Test Configuration:")
        print(f"   Selenium Hub: {cls.selenium_hub}")
        print(f"   Frontend: {cls.frontend_url}")
        print(f"   Backend: {cls.backend_url}")
        print()

        # Configure Chrome options for remote testing
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--lang=en-US")
        chrome_options.add_argument("--enable-javascript")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_experimental_option("prefs", {
            "intl.accept_languages": "en-US,en"
        })

        # Connect to remote Selenium Grid
        print("Connecting to Selenium Grid...")
        cls.driver = webdriver.Remote(
            command_executor=f"{cls.selenium_hub}/wd/hub",
            options=chrome_options
        )
        cls.driver.implicitly_wait(10)
        print("✓ Connected to Selenium Grid\n")

    @classmethod
    def tearDownClass(cls):
        """Clean up the WebDriver"""
        cls.driver.quit()

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
        """Test complete successful login flow"""
        print("\n🔍 Testing Successful Login Flow")
        print("=" * 60)

        # Navigate to the login page
        login_url = f"{self.frontend_url}/login"
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

        # Verify cookies are set
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

    def test_login_logout_login_again(self):
        """Test login, logout, then login again"""
        print("\n🔍 Testing Login -> Logout -> Login Again Flow")
        print("=" * 60)

        # First login
        print("\n1. First login...")
        login_url = f"{self.frontend_url}/login"
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

        print("\n" + "=" * 60)
        print("✅ Login-Logout-Login flow test passed!")


def run_tests():
    """Run the Selenium tests"""
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
    print("🚀 Running Selenium E2E Tests (Docker Compose)")
    print("=" * 60)

    try:
        exit_code = run_tests()
        print("\n" + "=" * 60)
        if exit_code == 0:
            print("✅ ALL TESTS PASSED!")
        else:
            print("❌ SOME TESTS FAILED")
        print("=" * 60)
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
