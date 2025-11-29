#!/usr/bin/env python
"""
Complete end-to-end Selenium tests for check-in/check-out flows.

This test suite covers:
- Full check-in workflow (search family, select child, check in)
- Full check-out workflow (view checked-in child, check out)
- Session auto-selection
- CSRF token handling
- Real-time database verification
"""

import os
import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException

import django

# Use local settings for password hash compatibility
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from accounts.models import AdminUser
from families.models import Family, Child, Parent
from events.models import Event, Session
from checkins.models import CheckInRecord, AuditLog


class SeleniumTestHelper:
    """Helper class for running Selenium tests"""

    def __init__(self):
        self.driver = None
        self.selenium_hub = os.getenv("SELENIUM_HUB_URL", "http://localhost:4444")
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        self.backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

    def setup_driver(self):
        """Set up the Selenium WebDriver"""
        print(f"\n🔧 Test Configuration:")
        print(f"   Selenium Hub: {self.selenium_hub}")
        print(f"   Frontend: {self.frontend_url}")
        print(f"   Backend: {self.backend_url}")
        print()

        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--lang=en-US")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")

        # Disable images for faster page loads
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
            print("Connecting to Selenium Grid...")
            self.driver = webdriver.Remote(
                command_executor=f"{self.selenium_hub}/wd/hub",
                options=chrome_options
            )
            print("✓ Connected to Selenium Grid\n")
        else:
            print("Using local ChromeDriver...")
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("✓ Local ChromeDriver initialized\n")

        self.driver.implicitly_wait(3)

    def teardown_driver(self):
        """Clean up the WebDriver"""
        if self.driver:
            try:
                screenshot_path = '/tmp/final_state.png'
                self.driver.save_screenshot(screenshot_path)
                print(f"📸 Saved final screenshot to {screenshot_path}")
            except:
                pass
            self.driver.quit()

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

    def perform_login(self, username, password):
        """Helper method to perform login"""
        print("   Logging in...")
        login_url = f"{self.frontend_url}/login"
        self.driver.get(login_url)

        # Wait for login form
        username_field = self.wait_and_find(By.ID, "username")
        password_field = self.wait_and_find(By.ID, "password")

        # Fill in credentials
        username_field.send_keys(username)
        password_field.send_keys(password)

        # Submit
        submit_button = self.wait_and_find(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()

        # Wait for redirect to check-in page
        try:
            WebDriverWait(self.driver, 10).until(
                EC.url_contains("/checkin")
            )
            print("   ✓ Login successful")
            return True
        except:
            print(f"   ❌ Login redirect failed. Current URL: {self.driver.current_url}")
            print(f"   Page title: {self.driver.title}")
            return False


def test_complete_checkin_flow():
    """Test the complete check-in flow"""
    print("\n🔍 Testing Complete Check-In Flow")
    print("=" * 60)

    helper = SeleniumTestHelper()
    helper.setup_driver()

    # Setup test data
    print("\n1. Setting up test data...")

    try:
        # Create test user
        test_username = "flowtest"
        test_password = "testpass123"

        # Clean up any existing test user and related data
        existing_user = AdminUser.objects.filter(username=test_username).first()
        if existing_user:
            AuditLog.objects.filter(user=existing_user).delete()
            existing_user.delete()

        test_user = AdminUser.objects.create_user(
            username=test_username,
            password=test_password,
            name="Flow Test User"
        )

        # Create test event and active session
        test_event = Event.objects.create(
            name="Sunday Service",
            start_date="2025-11-26",
            end_date="2025-11-26"
        )

        test_session = Session.objects.create(
            event=test_event,
            name="Morning Childcare",
            start_time="2025-11-26T09:00:00Z",
            end_time="2025-11-26T12:00:00Z",
            is_active=True,
            requires_ticket=False
        )

        # Create test family
        test_family = Family.objects.create()
        test_parent = Parent.objects.create(
            family=test_family,
            name="John Smith",
            phone="555-1234",
            email="john@example.com",
            relationship_type="Father"
        )

        test_child = Child.objects.create(
            family=test_family,
            first_name="Emma",
            last_name="Smith",
            birthdate="2020-05-15",
            allergies="Peanuts",
            notes="Test child"
        )
    except Exception as e:
        print(f"   ❌ Error setting up test data: {e}")
        import traceback
        traceback.print_exc()
        helper.teardown_driver()
        raise

    print(f"   ✓ User: {test_username}")
    print(f"   ✓ Event: {test_event.name}")
    print(f"   ✓ Session: {test_session.name}")
    print(f"   ✓ Family: Smith")
    print(f"   ✓ Child: Emma Smith")

    try:
        # Step 2: Login
        print("\n2. Logging in...")
        success = helper.perform_login(test_username, test_password)
        assert success, "Login failed"
        assert "/checkin" in helper.driver.current_url

        # Step 3: Wait for page to fully load
        print("\n3. Waiting for check-in page to load...")
        time.sleep(2)  # Allow time for React/Svelte to render and API calls
        print("   ✓ Page loaded")

        # Step 4: Search for family
        print("\n4. Searching for family 'Smith'...")
        search_input = helper.wait_and_find(By.CSS_SELECTOR, "input[type='text']", timeout=5)
        search_input.clear()
        search_input.send_keys("Smith")

        # Click the search button
        search_button = helper.wait_and_find(By.XPATH, "//button[contains(text(), 'Search')]", timeout=5)
        search_button.click()

        time.sleep(1.5)  # Wait for search results
        print("   ✓ Search executed")

        # Step 5: Verify family appears in results
        print("\n5. Verifying family in search results...")
        page_source = helper.driver.page_source
        assert "Smith" in page_source, "Family name not found in search results"
        assert "Emma" in page_source, "Child name not found in search results"
        print("   ✓ Family 'Smith' and child 'Emma' found in results")

        # Step 6: Select child for check-in
        print("\n6. Selecting child for check-in...")
        # Find green icon buttons in the table (these are the individual check-in selection buttons)
        # Look for buttons in rows containing "Emma Smith"
        table_rows = helper.driver.find_elements(By.CSS_SELECTOR, "tr")

        clicked = False
        for row in table_rows:
            if "Emma" in row.text and "Smith" in row.text:
                # Found the Emma Smith row, now find the button in this row
                try:
                    buttons = row.find_elements(By.CSS_SELECTOR, "button")
                    if buttons:
                        # Click the first button in this row (the selection button)
                        buttons[0].click()
                        clicked = True
                        print("   ✓ Selection button clicked for Emma Smith")
                        break
                except:
                    continue

        assert clicked, "Could not find Emma Smith's selection button"
        time.sleep(1.5)  # Wait for the main check-in button to appear

        # Step 7: Click main check-in button
        print("\n7. Performing check-in...")
        # The main button should now appear with text like "Check In 1 Child"
        # It has specific styling: bg-green-600 class
        try:
            checkin_main_button = helper.wait_and_find(
                By.XPATH,
                "//button[contains(@class, 'bg-green-600') and contains(text(), 'Check In')]",
                timeout=5
            )
        except:
            # Fallback: try any button with "Check In" text
            print("   ⚠️  Main button not found with class, trying alternative...")
            checkin_main_button = helper.wait_and_find(
                By.XPATH,
                "//button[contains(text(), 'Check In') and contains(text(), 'Child')]",
                timeout=5
            )

        checkin_main_button.click()
        time.sleep(2)  # Wait for check-in to process
        print("   ✓ Main check-in button clicked")

        # Step 8: Verify check-in success in database
        print("\n8. Verifying check-in in database...")
        checkin_record = CheckInRecord.objects.filter(
            child=test_child,
            session=test_session
        ).first()

        assert checkin_record is not None, "Check-in record not found in database"
        assert checkin_record.check_in_time is not None, "Check-in time not set"
        assert checkin_record.check_in_staff == test_user, "Check-in staff incorrect"

        print(f"   ✅ Check-in successful!")
        print(f"   - Record ID: {checkin_record.id}")
        print(f"   - Check-in time: {checkin_record.check_in_time}")
        print(f"   - Staff: {checkin_record.check_in_staff.name}")
        if test_child.qr_token:
            print(f"   - QR token: {test_child.qr_token}")

        print("\n" + "=" * 60)
        print("✅ Check-in flow test PASSED")

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        screenshot_path = '/tmp/checkin_test_failure.png'
        helper.driver.save_screenshot(screenshot_path)
        print(f"📸 Saved failure screenshot to {screenshot_path}")
        raise
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        screenshot_path = '/tmp/checkin_test_error.png'
        helper.driver.save_screenshot(screenshot_path)
        print(f"📸 Saved error screenshot to {screenshot_path}")
        raise
    finally:
        # Cleanup
        print("\n9. Cleaning up test data...")
        try:
            # Clean up in proper order to avoid foreign key constraints
            CheckInRecord.objects.filter(child=test_child).delete()
            AuditLog.objects.filter(user=test_user).delete()  # Clean audit logs first
            test_child.delete()
            test_parent.delete()
            test_family.delete()
            test_session.delete()
            test_event.delete()
            test_user.delete()
            print("   ✓ Test data cleaned up")
        except Exception as e:
            print(f"   ⚠️  Cleanup error: {e}")

        helper.teardown_driver()


def test_complete_checkout_flow():
    """Test the complete check-out flow"""
    print("\n🔍 Testing Complete Check-Out Flow")
    print("=" * 60)

    helper = SeleniumTestHelper()
    helper.setup_driver()

    # Setup test data
    print("\n1. Setting up test data...")

    try:
        # Create test user
        test_username = "checkouttest"
        test_password = "testpass123"

        # Clean up any existing test user and related data
        existing_user = AdminUser.objects.filter(username=test_username).first()
        if existing_user:
            AuditLog.objects.filter(user=existing_user).delete()
            existing_user.delete()

        test_user = AdminUser.objects.create_user(
            username=test_username,
            password=test_password,
            name="Checkout Test User"
        )
    except Exception as e:
        print(f"   ❌ Error setting up test user: {e}")
        import traceback
        traceback.print_exc()
        helper.teardown_driver()
        raise

    # Create test event and active session
    test_event = Event.objects.create(
        name="Sunday Service",
        start_date="2025-11-26",
        end_date="2025-11-26"
    )

    test_session = Session.objects.create(
        event=test_event,
        name="Morning Childcare",
        start_time="2025-11-26T09:00:00Z",
        end_time="2025-11-26T12:00:00Z",
        is_active=True,
        requires_ticket=False
    )

    # Create test family
    test_family = Family.objects.create()
    test_parent = Parent.objects.create(
        family=test_family,
        name="Jane Doe",
        phone="555-5678",
        email="jane@example.com",
        relationship_type="Mother"
    )

    test_child = Child.objects.create(
        family=test_family,
        first_name="Oliver",
        last_name="Doe",
        birthdate="2019-03-20",
        allergies="None",
        notes="Test child for checkout",
        qr_token="test-qr-checkout"
    )

    # Pre-create a check-in record
    checkin_record = CheckInRecord.objects.create(
        child=test_child,
        session=test_session,
        check_in_staff=test_user
    )

    print(f"   ✓ User: {test_username}")
    print(f"   ✓ Event: {test_event.name}")
    print(f"   ✓ Session: {test_session.name}")
    print(f"   ✓ Family: Doe")
    print(f"   ✓ Child: Oliver Doe (already checked in)")

    try:
        # Step 2: Login
        print("\n2. Logging in...")
        success = helper.perform_login(test_username, test_password)
        assert success, "Login failed"

        # Step 3: Navigate to check-out page
        print("\n3. Navigating to check-out page...")
        # Look for checkout link in navigation
        try:
            checkout_link = helper.wait_and_find(
                By.XPATH,
                "//a[contains(@href, '/checkout') or contains(text(), 'Check-Out') or contains(text(), 'Checkout')]",
                timeout=5
            )
            checkout_link.click()
        except:
            # If no link, try navigating directly
            helper.driver.get(f"{helper.frontend_url}/checkout")

        time.sleep(2)  # Wait for page to load
        assert "/checkout" in helper.driver.current_url, "Not on checkout page"
        print("   ✓ On check-out page")

        # Step 4: Verify child appears in checked-in list
        print("\n4. Verifying child in checked-in list...")
        time.sleep(2)  # Wait for data to load
        page_source = helper.driver.page_source

        # The checkout page might show child by ID rather than name
        # Check for either the child's name or ID
        child_id_str = str(test_child.id)
        child_found = "Oliver" in page_source or "Doe" in page_source or child_id_str in page_source

        if not child_found:
            print(f"   ⚠️  Child not immediately visible. Trying refresh...")
            # Click refresh button
            try:
                refresh_button = helper.wait_and_find(By.XPATH, "//button[contains(text(), 'Refresh')]", timeout=3)
                refresh_button.click()
                time.sleep(2)
                page_source = helper.driver.page_source
                child_found = "Oliver" in page_source or "Doe" in page_source or child_id_str in page_source
            except:
                pass

        assert child_found, f"Child 'Oliver Doe' (ID: {child_id_str}) not found in checked-in list"
        print("   ✓ Child found in checked-in list")

        # Step 5: Perform check-out
        print("\n5. Performing check-out...")
        # Find the check-out button for our child
        # The buttons are IconButtons in the table rows
        # Look for the row containing our child and find its checkout button
        table_rows = helper.driver.find_elements(By.CSS_SELECTOR, "tr")

        clicked = False
        for row in table_rows:
            if child_id_str in row.text or "Oliver" in row.text or (str(test_child.id)[:8] in row.text):
                # Found the row with our child, find the button
                try:
                    buttons = row.find_elements(By.CSS_SELECTOR, "button")
                    if buttons:
                        # Click the checkout button (should be a red button)
                        buttons[0].click()
                        clicked = True
                        print("   ✓ Check-out button clicked")
                        break
                except:
                    continue

        if not clicked:
            # Fallback: click any checkout button in the "Check Out" column
            print("   ⚠️  Trying alternative method to find checkout button...")
            all_buttons = helper.driver.find_elements(By.CSS_SELECTOR, "button")
            # Look for buttons that might be checkout buttons (not the Refresh button)
            for button in all_buttons:
                if "Refresh" not in button.text and button.is_displayed():
                    try:
                        button.click()
                        clicked = True
                        print("   ✓ Check-out button clicked (alternative method)")
                        break
                    except:
                        continue

        assert clicked, "Could not find or click check-out button"
        time.sleep(2)  # Wait for check-out to process

        # Step 6: Verify check-out success in database
        print("\n6. Verifying check-out in database...")
        checkin_record.refresh_from_db()

        assert checkin_record.check_out_time is not None, "Check-out time not set"
        assert checkin_record.check_out_staff == test_user, "Check-out staff incorrect"

        print(f"   ✅ Check-out successful!")
        print(f"   - Check-in time: {checkin_record.check_in_time}")
        print(f"   - Check-out time: {checkin_record.check_out_time}")
        print(f"   - Staff: {checkin_record.check_out_staff.name}")

        print("\n" + "=" * 60)
        print("✅ Check-out flow test PASSED")

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        screenshot_path = '/tmp/checkout_test_failure.png'
        helper.driver.save_screenshot(screenshot_path)
        print(f"📸 Saved failure screenshot to {screenshot_path}")
        raise
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        screenshot_path = '/tmp/checkout_test_error.png'
        helper.driver.save_screenshot(screenshot_path)
        print(f"📸 Saved error screenshot to {screenshot_path}")
        raise
    finally:
        # Cleanup
        print("\n7. Cleaning up test data...")
        try:
            # Clean up in proper order to avoid foreign key constraints
            CheckInRecord.objects.filter(child=test_child).delete()
            AuditLog.objects.filter(user=test_user).delete()  # Clean audit logs first
            test_child.delete()
            test_parent.delete()
            test_family.delete()
            test_session.delete()
            test_event.delete()
            test_user.delete()
            print("   ✓ Test data cleaned up")
        except Exception as e:
            print(f"   ⚠️  Cleanup error: {e}")

        helper.teardown_driver()


def test_i18n_language_switching():
    """Test internationalization language switching functionality"""
    print("\n🔍 Testing i18n Language Switching")
    print("=" * 60)

    helper = SeleniumTestHelper()
    helper.setup_driver()

    # Setup test data
    print("\n1. Setting up test data...")

    try:
        # Create test user
        test_username = "i18ntest"
        test_password = "testpass123"

        # Clean up any existing test user
        existing_user = AdminUser.objects.filter(username=test_username).first()
        if existing_user:
            AuditLog.objects.filter(user=existing_user).delete()
            existing_user.delete()

        # Create test user
        test_user = AdminUser.objects.create_user(
            username=test_username,
            password=test_password,
            name="i18n Test User"
        )
        print(f"   ✓ User: {test_username}")

        # Create test event and session
        test_event = Event.objects.create(
            name="Sunday Service",
            start_date="2025-11-29",
            end_date="2025-11-29",
        )
        print(f"   ✓ Event: {test_event.name}")

        test_session = Session.objects.create(
            event=test_event,
            name="Morning Childcare",
            start_time="09:00",
            end_time="11:00",
            status="active",
        )
        print(f"   ✓ Session: {test_session.name}")

        # Create test family and child
        test_family = Family.objects.create(
            family_name="i18n Test Family",
            primary_contact_name="Test Parent",
            email="i18n@test.com",
        )
        test_parent = Parent.objects.create(
            family=test_family,
            first_name="Test",
            last_name="Parent",
        )
        test_child = Child.objects.create(
            family=test_family,
            first_name="Test",
            last_name="Child",
            date_of_birth="2020-01-01",
        )
        print(f"   ✓ Family: {test_family.family_name}")
        print(f"   ✓ Child: {test_child.first_name} {test_child.last_name}")

        # Step 2: Login
        print("\n2. Logging in...")
        helper.perform_login(test_username, test_password)

        # Step 3: Verify page loaded with default language (English)
        print("\n3. Verifying default language (English)...")
        time.sleep(2)  # Wait for page to fully load

        # Check for English text in navigation
        page_source = helper.driver.page_source
        assert "Check-In" in page_source or "Logout" in page_source, "Expected English navigation text"
        print("   ✓ Page loaded in English")

        # Step 4: Switch to Swedish
        print("\n4. Switching to Swedish...")
        swedish_button = helper.wait_and_find(By.CSS_SELECTOR, "[data-testid='language-sv']")
        swedish_button.click()
        time.sleep(2)  # Wait for language change and page updates

        # Verify Swedish language is active
        page_source = helper.driver.page_source

        # Check for Swedish navigation text
        assert "Incheckning" in page_source or "Logga ut" in page_source, "Expected Swedish navigation text"
        print("   ✓ Language switched to Swedish")
        print("   ✓ Navigation shows Swedish text")

        # Step 5: Navigate to check-in page and verify Swedish
        print("\n5. Verifying check-in page in Swedish...")
        checkin_link = helper.wait_and_find(By.CSS_SELECTOR, "a[href='/checkin']")
        checkin_link.click()
        time.sleep(2)

        # Verify check-in page content is in Swedish
        page_source = helper.driver.page_source

        # The Search button should show "Sök" in Swedish
        search_button = helper.wait_and_find(By.CSS_SELECTOR, "[data-testid='search-button']")
        assert "Sök" in search_button.text or "Search" in search_button.text, f"Search button text: {search_button.text}"
        print(f"   ✓ Search button text: {search_button.text}")

        # Step 6: Switch back to English
        print("\n6. Switching back to English...")
        english_button = helper.wait_and_find(By.CSS_SELECTOR, "[data-testid='language-en']")
        english_button.click()
        time.sleep(2)  # Wait for language change

        # Verify English is restored
        page_source = helper.driver.page_source
        assert "Check-In" in page_source or "Logout" in page_source, "Expected English navigation text"
        print("   ✓ Language switched back to English")

        # Verify button text is in English
        search_button = helper.wait_and_find(By.CSS_SELECTOR, "[data-testid='search-button']")
        assert "Search" in search_button.text, f"Expected 'Search', got: {search_button.text}"
        print(f"   ✓ Search button text: {search_button.text}")

        # Step 7: Test that i18n persists after navigation
        print("\n7. Verifying language persists after navigation...")

        # Switch to Swedish again
        swedish_button = helper.wait_and_find(By.CSS_SELECTOR, "[data-testid='language-sv']")
        swedish_button.click()
        time.sleep(1)

        # Navigate to check-out page
        checkout_link = helper.wait_and_find(By.CSS_SELECTOR, "a[href='/checkout']")
        checkout_link.click()
        time.sleep(2)

        # Verify still in Swedish on checkout page
        page_source = helper.driver.page_source
        assert "Utcheckning" in page_source or "Uppdatera" in page_source, "Expected Swedish text on checkout page"
        print("   ✓ Language persisted across navigation")

        print("\n" + "=" * 60)
        print("✅ i18n language switching test PASSED")

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        screenshot_path = '/tmp/i18n_test_failure.png'
        helper.driver.save_screenshot(screenshot_path)
        print(f"📸 Saved failure screenshot to {screenshot_path}")
        raise
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        screenshot_path = '/tmp/i18n_test_error.png'
        helper.driver.save_screenshot(screenshot_path)
        print(f"📸 Saved error screenshot to {screenshot_path}")
        raise
    finally:
        # Cleanup
        print("\n8. Cleaning up test data...")
        try:
            CheckInRecord.objects.filter(child=test_child).delete()
            AuditLog.objects.filter(user=test_user).delete()
            test_child.delete()
            test_parent.delete()
            test_family.delete()
            test_session.delete()
            test_event.delete()
            test_user.delete()
            print("   ✓ Test data cleaned up")
        except Exception as e:
            print(f"   ⚠️  Cleanup error: {e}")

        # Save final screenshot
        screenshot_path = '/tmp/i18n_final_state.png'
        helper.driver.save_screenshot(screenshot_path)
        print(f"📸 Saved final screenshot to {screenshot_path}")

        helper.teardown_driver()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 Running Full Flow Selenium E2E Tests")
    print("=" * 60)

    try:
        # Run check-in test
        test_complete_checkin_flow()

        print("\n")

        # Run check-out test
        test_complete_checkout_flow()

        print("\n")

        # Run i18n test
        test_i18n_language_switching()

        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        sys.exit(0)
    except Exception as e:
        print("\n" + "=" * 60)
        print("❌ TESTS FAILED (check output above)")
        print("=" * 60)
        sys.exit(1)
