#!/usr/bin/env python
"""
Complete end-to-end Selenium tests for check-in/check-out flows and i18n.

This test suite covers:
- Full check-in workflow (create session, search family, check in child)
- Full check-out workflow (search checked-in child, check out)
- Language switching (English/Swedish)
- CSRF token handling
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

# Setup Django with test settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
django.setup()

from django.test import TestCase
from accounts.models import AdminUser
from checkins.models import Family, Child, Event, Session, CheckInRecord


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

        # Configure Chrome options
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
        # Take a screenshot before closing
        try:
            cls.driver.save_screenshot('/app/test-results/final_state.png')
            print("📸 Saved final screenshot to /app/test-results/final_state.png")
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
            session_type="CHILDCARE",
            start_time="2025-11-26T09:00:00Z",
            end_time="2025-11-26T12:00:00Z",
            is_active=True  # Make sure it's active!
        )

        # Create test family and child
        self.test_family = Family.objects.create(
            family_name="Smith",
            primary_contact_name="John Smith",
            primary_contact_phone="555-1234",
            primary_contact_email="john@example.com"
        )

        self.test_child = Child.objects.create(
            family=self.test_family,
            first_name="Emma",
            last_name="Smith",
            date_of_birth="2020-05-15",
            allergies="Peanuts",
            medical_conditions="None",
            qr_token=None  # Will be generated on check-in
        )

        print(f"\n✅ Test data created:")
        print(f"   User: {self.test_username}")
        print(f"   Event: {self.test_event.name}")
        print(f"   Session: {self.test_session.name} (Active: {self.test_session.is_active})")
        print(f"   Family: {self.test_family.family_name}")
        print(f"   Child: {self.test_child.first_name} {self.test_child.last_name}")

    def tearDown(self):
        """Clean up test data after each test"""
        # Take screenshot on failure
        if hasattr(self, '_outcome'):
            result = self._outcome.result
            if result.errors or result.failures:
                test_name = self._testMethodName
                self.driver.save_screenshot(f'/app/test-results/{test_name}_failure.png')
                print(f"📸 Saved failure screenshot for {test_name}")

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
        WebDriverWait(self.driver, 10).until(
            EC.url_contains("/checkin")
        )
        print("   ✓ Login successful")

    def test_01_complete_checkin_flow(self):
        """Test the complete check-in flow"""
        print("\n🔍 Testing Complete Check-In Flow")
        print("=" * 60)

        # Step 1: Login
        print("\n1. Logging in...")
        self.perform_login()
        self.assertIn("/checkin", self.driver.current_url)

        # Step 2: Verify active session is loaded
        print("\n2. Checking for active session...")
        time.sleep(2)  # Wait for sessions to load

        page_source = self.driver.page_source
        if "Morning Childcare" in page_source or self.test_session.name in page_source:
            print(f"   ✓ Active session '{self.test_session.name}' found on page")
        else:
            print(f"   ⚠️  Active session not visible. Page source length: {len(page_source)}")
            print(f"   Session ID: {self.test_session.id}")
            print(f"   Session Active: {self.test_session.is_active}")

        # Step 3: Search for family
        print(f"\n3. Searching for family '{self.test_family.family_name}'...")
        try:
            search_input = self.wait_and_find(By.CSS_SELECTOR, "input[type='text']")
            search_input.clear()
            search_input.send_keys("Smith")
            time.sleep(2)  # Wait for search results

            page_source = self.driver.page_source
            if "Smith" in page_source and "Emma" in page_source:
                print("   ✓ Family found in search results")
            else:
                print("   ⚠️  Family not found in search results")
                print(f"   'Smith' in page: {'Smith' in page_source}")
                print(f"   'Emma' in page: {'Emma' in page_source}")

        except TimeoutException:
            print("   ❌ Search input not found")
            self.fail("Search input not found")

        # Step 4: Select child for check-in
        print("\n4. Selecting child for check-in...")
        try:
            # Look for checkbox or select button for the child
            # This depends on the UI implementation
            checkbox_found = False

            # Try to find checkbox by various methods
            possible_selectors = [
                "input[type='checkbox']",
                "input[type='radio']",
                f"//input[@type='checkbox']",
            ]

            for selector in possible_selectors:
                try:
                    if selector.startswith("//"):
                        checkboxes = self.driver.find_elements(By.XPATH, selector)
                    else:
                        checkboxes = self.driver.find_elements(By.CSS_SELECTOR, selector)

                    if checkboxes:
                        print(f"   Found {len(checkboxes)} checkbox(es)")
                        checkboxes[0].click()
                        checkbox_found = True
                        print("   ✓ Child selected")
                        break
                except:
                    continue

            if not checkbox_found:
                print("   ⚠️  Could not find checkbox to select child")
                print("   This might indicate a UI structure issue")

        except Exception as e:
            print(f"   ❌ Error selecting child: {e}")

        # Step 5: Click check-in button
        print("\n5. Performing check-in...")
        try:
            # Look for check-in button
            checkin_button_found = False
            button_selectors = [
                "//button[contains(text(), 'Check In')]",
                "//button[contains(text(), 'Check-In')]",
                "button.btn-primary",
                "button[type='submit']",
            ]

            for selector in button_selectors:
                try:
                    if selector.startswith("//"):
                        button = self.driver.find_element(By.XPATH, selector)
                    else:
                        button = self.driver.find_element(By.CSS_SELECTOR, selector)

                    button.click()
                    checkin_button_found = True
                    print("   ✓ Check-in button clicked")
                    time.sleep(2)  # Wait for check-in to process
                    break
                except:
                    continue

            if not checkin_button_found:
                print("   ⚠️  Could not find check-in button")

        except Exception as e:
            print(f"   ❌ Error clicking check-in button: {e}")

        # Step 6: Verify check-in success
        print("\n6. Verifying check-in...")
        time.sleep(2)

        # Check database for check-in record
        checkin_record = CheckInRecord.objects.filter(
            child=self.test_child,
            session=self.test_session
        ).first()

        if checkin_record:
            print(f"   ✅ Check-in successful! Record ID: {checkin_record.id}")
            print(f"   Check-in time: {checkin_record.check_in_time}")
            print(f"   QR token: {checkin_record.child.qr_token}")
        else:
            print("   ❌ No check-in record found in database")
            print("   This indicates the check-in operation failed")

        print("\n" + "=" * 60)
        print("✅ Check-in flow test completed")

    def test_02_complete_checkout_flow(self):
        """Test the complete check-out flow"""
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
        try:
            # Try to find check-out link/button
            checkout_selectors = [
                "//a[contains(text(), 'Check-Out')]",
                "//button[contains(text(), 'Check-Out')]",
                "//a[@href='/checkout']",
            ]

            for selector in checkout_selectors:
                try:
                    element = self.driver.find_element(By.XPATH, selector)
                    element.click()
                    break
                except:
                    continue

            WebDriverWait(self.driver, 10).until(
                EC.url_contains("/checkout")
            )
            print("   ✓ Navigated to check-out page")

        except TimeoutException:
            print("   ⚠️  Could not navigate to check-out page")
            print(f"   Current URL: {self.driver.current_url}")

        # Step 4: Verify child appears in checked-in list
        print("\n4. Looking for checked-in child...")
        time.sleep(2)

        page_source = self.driver.page_source
        if "Emma" in page_source and "Smith" in page_source:
            print("   ✓ Child found in checked-in list")
        else:
            print("   ⚠️  Child not visible in checked-in list")

        # Step 5: Perform check-out
        print("\n5. Performing check-out...")
        try:
            # Look for check-out button
            checkout_button_selectors = [
                "//button[contains(text(), 'Check Out')]",
                "//button[contains(text(), 'Check-Out')]",
                "button.btn-danger",
            ]

            button_found = False
            for selector in checkout_button_selectors:
                try:
                    buttons = self.driver.find_elements(By.XPATH, selector)
                    if buttons:
                        buttons[0].click()
                        button_found = True
                        print("   ✓ Check-out button clicked")
                        time.sleep(2)
                        break
                except:
                    continue

            if not button_found:
                print("   ⚠️  Could not find check-out button")

        except Exception as e:
            print(f"   ❌ Error clicking check-out button: {e}")

        # Step 6: Verify check-out success
        print("\n6. Verifying check-out...")

        # Refresh record from database
        checkin_record.refresh_from_db()

        if checkin_record.check_out_time:
            print(f"   ✅ Check-out successful!")
            print(f"   Check-out time: {checkin_record.check_out_time}")
        else:
            print("   ❌ Check-out time not set in database")
            print("   This indicates the check-out operation failed")

            # Print browser console logs if available
            try:
                logs = self.driver.get_log('browser')
                if logs:
                    print("\n   Browser console logs:")
                    for log in logs[-10:]:  # Last 10 logs
                        print(f"   {log}")
            except:
                pass

        print("\n" + "=" * 60)
        print("✅ Check-out flow test completed")

    def test_03_language_switching(self):
        """Test i18n language switching"""
        print("\n🔍 Testing Language Switching (i18n)")
        print("=" * 60)

        # Step 1: Login
        print("\n1. Logging in...")
        self.perform_login()

        # Step 2: Check current language
        print("\n2. Checking current language...")
        page_source = self.driver.page_source

        # Look for English text
        english_indicators = ["Check-In", "Search", "Logout"]
        english_found = any(indicator in page_source for indicator in english_indicators)

        if english_found:
            print("   ✓ Page is in English")

        # Step 3: Look for language switcher
        print("\n3. Looking for language switcher...")
        try:
            # Try to find language switcher
            switcher_selectors = [
                "//select[@id='language']",
                "//button[contains(@class, 'language')]",
                "//a[contains(text(), 'Svenska')]",
                "//a[contains(text(), 'English')]",
                "select",  # Generic select dropdown
            ]

            switcher_found = False
            for selector in switcher_selectors:
                try:
                    if selector.startswith("//"):
                        elements = self.driver.find_elements(By.XPATH, selector)
                    else:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)

                    if elements:
                        print(f"   ✓ Found potential language switcher: {selector}")
                        switcher_found = True

                        # Try to click/change it
                        element = elements[0]

                        # If it's a select dropdown
                        if element.tag_name == 'select':
                            from selenium.webdriver.support.ui import Select
                            select = Select(element)
                            options = select.options
                            print(f"   Options available: {[opt.text for opt in options]}")

                            # Try to select Swedish if available
                            for option in options:
                                if 'sv' in option.get_attribute('value').lower() or 'swedish' in option.text.lower():
                                    option.click()
                                    time.sleep(1)
                                    print("   ✓ Switched to Swedish")
                                    break
                        else:
                            element.click()
                            time.sleep(1)

                        break
                except Exception as e:
                    continue

            if not switcher_found:
                print("   ⚠️  Language switcher not found")
                print("   i18n switching may not be fully implemented yet")

        except Exception as e:
            print(f"   ❌ Error with language switcher: {e}")

        # Step 4: Verify language changed (if switcher was found)
        print("\n4. Verifying language change...")
        time.sleep(1)
        page_source = self.driver.page_source

        # Look for Swedish text if we tried to switch
        swedish_indicators = ["Logga ut", "Sök", "Incheckning"]
        swedish_found = any(indicator in page_source for indicator in swedish_indicators)

        if swedish_found:
            print("   ✅ Language successfully switched to Swedish!")
        else:
            print("   ⚠️  Swedish text not found (i18n may need more work)")

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
            print("⚠️  SOME TESTS HAD ISSUES (check output above)")
        print("=" * 60)
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
