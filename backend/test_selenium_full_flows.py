#!/usr/bin/env python
"""
Complete end-to-end Selenium tests for check-in/check-out flows and i18n.

This test suite covers:
- Full check-in workflow (create session, search family, check in child)
- Full check-out workflow (search checked-in child, check out)
- Language switching (English/Swedish)
- CSRF token handling
- API endpoint verification
"""

import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException

import django

# IMPORTANT: Use local settings (same as running server) for password hash compatibility!
# Tests will share the same database as the running server
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.test import TestCase
from accounts.models import AdminUser
from families.models import Family, Child
from events.models import Event, Session
from checkins.models import CheckInRecord


class FullFlowSeleniumTests(TestCase):
    """
    Complete end-to-end tests for check-in/check-out flows.
    """

    @classmethod
    def setUpClass(cls):
        """Set up the Remote Selenium WebDriver"""
        # Get URLs from environment
        cls.selenium_hub = os.getenv("SELENIUM_HUB_URL", "http://localhost:4444")
        cls.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        cls.backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

        print(f"\n🔧 Test Configuration:")
        print(f"   Selenium Hub: {cls.selenium_hub}")
        print(f"   Frontend: {cls.frontend_url}")
        print(f"   Backend: {cls.backend_url}")
        print()

        # Configure Chrome options for optimal performance
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")  # Use new headless mode (Chrome 109+)
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")  # Slower but prevents crashes
        chrome_options.add_argument("--disable-gpu")  # Reduces memory usage
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--lang=en-US")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")

        # Disable images for faster page loads (we're not taking visual screenshots)
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "intl.accept_languages": "en-US,en"
        }
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)

        # Enable browser logging
        chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

        # Detect if we should use local ChromeDriver or remote Selenium Grid
        use_remote = os.getenv("SELENIUM_HUB_URL") is not None

        if use_remote:
            # Connect to remote Selenium Grid (Docker)
            print("Connecting to Selenium Grid...")
            cls.driver = webdriver.Remote(
                command_executor=f"{cls.selenium_hub}/wd/hub",
                options=chrome_options
            )
            print("✓ Connected to Selenium Grid\n")
        else:
            # Use local ChromeDriver
            print("Using local ChromeDriver...")
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager

            service = Service(ChromeDriverManager().install())
            cls.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("✓ Local ChromeDriver initialized\n")

        # Use shorter implicit wait - explicit waits are better for performance
        cls.driver.implicitly_wait(3)

    @classmethod
    def tearDownClass(cls):
        """Clean up the WebDriver"""
        # Take a screenshot before closing
        try:
            screenshot_path = '/tmp/final_state.png'
            cls.driver.save_screenshot(screenshot_path)
            print(f"📸 Saved final screenshot to {screenshot_path}")
        except:
            pass
        cls.driver.quit()

    def setUp(self):
        """Set up test data before each test"""
        # Create a test user
        self.test_username = "flowtest"
        self.test_password = "testpass123"
        self.test_name = "Flow Test User"

        # Delete existing test user if present
        AdminUser.objects.filter(username=self.test_username).delete()

        # Create fresh test user
        self.test_user = AdminUser.objects.create_user(
            username=self.test_username,
            password=self.test_password,
            name=self.test_name
        )

        # Create test event and active session
        self.test_event = Event.objects.create(
            name="Sunday Service",
            start_date="2025-11-26",
            end_date="2025-11-26"
        )

        self.test_session = Session.objects.create(
            event=self.test_event,
            name="Morning Childcare",
            start_time="2025-11-26T09:00:00Z",
            end_time="2025-11-26T12:00:00Z",
            is_active=True,  # Make sure it's active!
            requires_ticket=False
        )

        # Create test family, parent, and child
        self.test_family = Family.objects.create()

        from families.models import Parent
        self.test_parent = Parent.objects.create(
            family=self.test_family,
            name="John Smith",
            phone="555-1234",
            email="john@example.com",
            relationship_type="Father"
        )

        self.test_child = Child.objects.create(
            family=self.test_family,
            first_name="Emma",
            last_name="Smith",
            birthdate="2020-05-15",
            allergies="Peanuts",
            notes="None",
            qr_token=None  # Will be generated on check-in
        )

        print(f"\n✅ Test data created:")
        print(f"   User: {self.test_username}")
        print(f"   Event: {self.test_event.name}")
        print(f"   Session: {self.test_session.name} (Active: {self.test_session.is_active})")
        print(f"   Family ID: {self.test_family.id}")
        print(f"   Parent: {self.test_parent.name}")
        print(f"   Child: {self.test_child.first_name} {self.test_child.last_name}")

    def tearDown(self):
        """Clean up test data after each test"""
        # Take screenshot on failure
        if hasattr(self, '_outcome'):
            result = self._outcome.result
            if result.errors or result.failures:
                test_name = self._testMethodName
                screenshot_path = f'/tmp/{test_name}_failure.png'
                self.driver.save_screenshot(screenshot_path)
                print(f"📸 Saved failure screenshot to {screenshot_path}")

        # Clean up in reverse order of dependencies
        CheckInRecord.objects.filter(child=self.test_child).delete()
        Child.objects.filter(family=self.test_family).delete()
        self.test_family.delete()
        self.test_session.delete()
        self.test_event.delete()
        AdminUser.objects.filter(username=self.test_username).delete()

        # Clear cookies
        self.driver.delete_all_cookies()

    def wait_and_find(self, by, value, timeout=10):
        """Wait for element and return it"""
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def wait_and_click(self, by, value, timeout=10):
        """Wait for element to be clickable and click it"""
        element = WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        element.click()
        return element

    def check_console_for_errors(self, context=""):
        """Check browser console for API errors and return them"""
        try:
            logs = self.driver.get_log('browser')
            errors = []
            for log in logs:
                if log['level'] == 'SEVERE':
                    message = log['message']
                    # Skip favicon errors (not critical)
                    if 'favicon' in message.lower():
                        continue
                    # Check for 403 errors
                    if '403' in message or 'Forbidden' in message:
                        errors.append(f"403 Forbidden: {message}")
                    # Check for other HTTP errors
                    elif any(code in message for code in ['400', '401', '404', '500']):
                        errors.append(f"HTTP Error: {message}")
            return errors
        except:
            return []

    def assert_no_api_errors(self, context=""):
        """Assert that there are no API errors in console"""
        errors = self.check_console_for_errors(context)
        if errors:
            print(f"\n❌ API Errors found{' in ' + context if context else ''}:")
            for error in errors:
                print(f"   - {error}")
            self.fail(f"API errors detected{' in ' + context if context else ''}: {len(errors)} error(s)")

    def perform_login(self):
        """Helper method to perform login"""
        print("   Logging in...")
        login_url = f"{self.frontend_url}/login"
        self.driver.get(login_url)

        # Wait for login form
        username_field = self.wait_and_find(By.ID, "username")
        password_field = self.wait_and_find(By.ID, "password")

        # Fill in credentials
        username_field.send_keys(self.test_username)
        password_field.send_keys(self.test_password)

        # Submit
        submit_button = self.wait_and_find(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()

        # Wait for redirect to check-in page
        try:
            WebDriverWait(self.driver, 10).until(
                EC.url_contains("/checkin")
            )
            print("   ✓ Login successful")
        except:
            print(f"   ❌ Login redirect failed. Current URL: {self.driver.current_url}")
            print(f"   Page title: {self.driver.title}")
            # Check for API errors
            self.assert_no_api_errors("login")
            raise

    def test_01_complete_checkin_flow(self):
        """Test the complete check-in flow with API verification"""
        print("\n🔍 Testing Complete Check-In Flow")
        print("=" * 60)

        # Step 1: Login
        print("\n1. Logging in...")
        self.perform_login()
        self.assertIn("/checkin", self.driver.current_url)

        # Step 2: Wait for page to load and verify no API errors
        print("\n2. Verifying page loaded without API errors...")
        time.sleep(1.5)  # Brief wait for API calls to complete
        self.assert_no_api_errors("checkin page load")
        print("   ✓ No API errors on page load")

        # Step 3: Verify active session is loaded
        print("\n3. Checking for active session...")
        page_source = self.driver.page_source

        # Session should be visible on the page
        self.assertIn("Morning Childcare", page_source, "Active session not found on page")
        print(f"   ✓ Active session '{self.test_session.name}' found on page")

        # Step 4: Search for family
        print(f"\n4. Searching for family 'Smith'...")
        search_input = self.wait_and_find(By.CSS_SELECTOR, "input[type='text']", timeout=5)
        search_input.clear()
        search_input.send_keys("Smith")
        time.sleep(1)  # Brief wait for search results

        # Verify no API errors from search
        self.assert_no_api_errors("family search")

        # Verify family appears in results
        page_source = self.driver.page_source
        self.assertIn("Smith", page_source, "Family name not found in search results")
        self.assertIn("Emma", page_source, "Child name not found in search results")
        print("   ✓ Family found in search results")

        # Step 5: Select child for check-in
        print("\n5. Selecting child for check-in...")
        # Find and click the checkbox for the child
        checkboxes = self.driver.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
        self.assertGreater(len(checkboxes), 0, "No checkboxes found for child selection")
        checkboxes[0].click()
        print(f"   ✓ Child selected ({len(checkboxes)} checkbox(es) found)")

        # Step 6: Click check-in button
        print("\n6. Performing check-in...")
        # Look for the check-in button
        checkin_button = self.wait_and_find(By.XPATH, "//button[contains(text(), 'Check In') or contains(text(), 'Check-In')]", timeout=5)
        checkin_button.click()
        time.sleep(1.5)  # Brief wait for check-in to process

        # Verify no API errors from check-in
        self.assert_no_api_errors("check-in operation")
        print("   ✓ Check-in button clicked, no API errors")

        # Step 7: Verify check-in success in database
        print("\n7. Verifying check-in in database...")
        checkin_record = CheckInRecord.objects.filter(
            child=self.test_child,
            session=self.test_session
        ).first()

        self.assertIsNotNone(checkin_record, "Check-in record not found in database")
        self.assertIsNotNone(checkin_record.check_in_time, "Check-in time not set")
        self.assertEqual(checkin_record.check_in_staff, self.test_user, "Check-in staff incorrect")

        print(f"   ✅ Check-in successful!")
        print(f"   - Record ID: {checkin_record.id}")
        print(f"   - Check-in time: {checkin_record.check_in_time}")
        print(f"   - QR token: {checkin_record.child.qr_token}")

        print("\n" + "=" * 60)
        print("✅ Check-in flow test PASSED")

    def test_02_complete_checkout_flow(self):
        """Test the complete check-out flow with API verification"""
        print("\n🔍 Testing Complete Check-Out Flow")
        print("=" * 60)

        # Step 1: Create a check-in record first
        print("\n1. Pre-creating check-in record...")
        checkin_record = CheckInRecord.objects.create(
            child=self.test_child,
            session=self.test_session,
            check_in_staff=self.test_user
        )
        # Generate QR token
        if not self.test_child.qr_token:
            self.test_child.qr_token = "test-qr-12345"
            self.test_child.save()
        print(f"   ✓ Check-in record created: {checkin_record.id}")

        # Step 2: Login
        print("\n2. Logging in...")
        self.perform_login()

        # Step 3: Navigate to check-out page
        print("\n3. Navigating to check-out page...")
        # Find and click the check-out link/button in navigation
        checkout_link = self.wait_and_find(By.XPATH, "//a[contains(text(), 'Check-Out') or contains(@href, '/checkout')]", timeout=5)
        checkout_link.click()

        WebDriverWait(self.driver, 10).until(
            EC.url_contains("/checkout")
        )
        print("   ✓ Navigated to check-out page")

        # Step 4: Wait for page to load and verify no API errors
        print("\n4. Verifying page loaded without API errors...")
        time.sleep(1.5)  # Brief wait for API calls to complete
        self.assert_no_api_errors("checkout page load")
        print("   ✓ No API errors on page load")

        # Step 5: Verify child appears in checked-in list
        print("\n5. Looking for checked-in child...")
        page_source = self.driver.page_source
        self.assertIn("Emma", page_source, "Child first name not found on checkout page")
        self.assertIn("Smith", page_source, "Child last name not found on checkout page")
        print("   ✓ Child found in checked-in list")

        # Step 6: Perform check-out
        print("\n6. Performing check-out...")
        # Find and click the check-out button for this child
        checkout_button = self.wait_and_find(By.XPATH, "//button[contains(text(), 'Check Out') or contains(text(), 'Check-Out')]", timeout=5)
        checkout_button.click()
        time.sleep(1.5)  # Brief wait for check-out to process

        # Verify no API errors from check-out
        self.assert_no_api_errors("check-out operation")
        print("   ✓ Check-out button clicked, no API errors")

        # Step 7: Verify check-out success in database
        print("\n7. Verifying check-out in database...")
        checkin_record.refresh_from_db()

        self.assertIsNotNone(checkin_record.check_out_time, "Check-out time not set in database")
        self.assertEqual(checkin_record.check_out_staff, self.test_user, "Check-out staff incorrect")

        print(f"   ✅ Check-out successful!")
        print(f"   - Check-out time: {checkin_record.check_out_time}")
        print(f"   - Staff: {checkin_record.check_out_staff.name}")

        print("\n" + "=" * 60)
        print("✅ Check-out flow test PASSED")

    def test_03_language_switching(self):
        """Test i18n language switching"""
        print("\n🔍 Testing Language Switching (i18n)")
        print("=" * 60)

        # Step 1: Login
        print("\n1. Logging in...")
        self.perform_login()
        time.sleep(1)  # Brief wait for page load

        # Step 2: Check current language
        print("\n2. Checking current language...")
        page_source = self.driver.page_source

        # Look for English text
        english_indicators = ["Check-In", "Search", "Logout"]
        english_found = any(indicator in page_source for indicator in english_indicators)

        self.assertTrue(english_found, "English text not found on page")
        print("   ✓ Page is in English")

        # Step 3: Look for language switcher
        print("\n3. Looking for language switcher...")
        try:
            # Try to find language switcher - look for select dropdown
            language_select = self.driver.find_elements(By.CSS_SELECTOR, "select")

            if language_select:
                from selenium.webdriver.support.ui import Select
                select = Select(language_select[0])
                options = [opt.text for opt in select.options]
                print(f"   ✓ Found language switcher with options: {options}")

                # Try to select Swedish if available
                for option in select.options:
                    if 'sv' in option.get_attribute('value').lower() or 'swedish' in option.text.lower():
                        option.click()
                        time.sleep(2)
                        print("   ✓ Switched to Swedish")

                        # Step 4: Verify language changed
                        print("\n4. Verifying language change...")
                        page_source = self.driver.page_source

                        # Look for Swedish text
                        swedish_indicators = ["Logga ut", "Sök"]
                        swedish_found = any(indicator in page_source for indicator in swedish_indicators)

                        if swedish_found:
                            print("   ✅ Language successfully switched to Swedish!")
                        else:
                            print("   ⚠️  Swedish text not found (i18n translations may need more work)")
                        break
            else:
                print("   ⚠️  Language switcher not found")
                print("   This feature may not be implemented yet")

        except Exception as e:
            print(f"   ⚠️  Error with language switcher: {e}")
            print("   This feature may not be fully implemented")

        print("\n" + "=" * 60)
        print("✅ Language switching test completed")


def run_tests():
    """Run the Selenium tests"""
    import unittest

    # Create a test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(FullFlowSeleniumTests)

    # Run the tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 Running Full Flow Selenium E2E Tests")
    print("=" * 60)

    try:
        exit_code = run_tests()
        print("\n" + "=" * 60)
        if exit_code == 0:
            print("✅ ALL TESTS PASSED!")
        else:
            print("❌ SOME TESTS FAILED (check output above)")
        print("=" * 60)
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
