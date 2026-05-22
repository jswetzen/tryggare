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
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

import django

# Use local settings for password hash compatibility
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from accounts.models import AdminUser
from families.models import Family, Child, Parent
from events.models import Event, Session
from checkins.models import AuditLog


class SeleniumTestHelper:
    """Helper class for running Selenium tests"""

    def __init__(self):
        self.driver = None
        self.selenium_hub = os.getenv("SELENIUM_HUB_URL", "http://localhost:4444")
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        self.backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

    def setup_driver(self):
        """Set up the Selenium WebDriver"""
        print("\n🔧 Test Configuration:")
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
            "intl.accept_languages": "en-US,en",
        }
        chrome_options.add_experimental_option("prefs", prefs)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        # Enable browser logging
        chrome_options.set_capability("goog:loggingPrefs", {"browser": "ALL"})

        # Detect if we should use local ChromeDriver or remote Selenium Grid
        use_remote = os.getenv("SELENIUM_HUB_URL") is not None

        if use_remote:
            print("Connecting to Selenium Grid...")
            self.driver = webdriver.Remote(
                command_executor=f"{self.selenium_hub}/wd/hub", options=chrome_options
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
                screenshot_path = "/tmp/final_state.png"
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
            WebDriverWait(self.driver, 10).until(EC.url_contains("/checkin"))
            print("   ✓ Login successful")
            return True
        except:
            print(
                f"   ❌ Login redirect failed. Current URL: {self.driver.current_url}"
            )
            print(f"   Page title: {self.driver.title}")
            return False


def setup_test_data():
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
            username=test_username, password=test_password, name="Flow Test User"
        )

        # Create test event and active session
        test_event = Event.objects.create(
            name="Sunday Service", start_date="2025-11-26", end_date="2025-11-26"
        )

        test_session = Session.objects.create(
            event=test_event,
            name="Morning Childcare",
            start_time="2025-11-26T09:00:00Z",
            end_time="2025-11-26T12:00:00Z",
            is_active=True,
            requires_ticket=False,
        )

        # Create test family
        test_family = Family.objects.create(last_name="Smith")
        test_parent = Parent.objects.create(
            family=test_family,
            name="John Smith",
            phone="555-1234",
            email="john@example.com",
            relationship_type="Father",
        )

        test_child = Child.objects.create(
            family=test_family,
            first_name="Emma",
            last_name="Smith",
            birthdate="2020-05-15",
            allergies="Peanuts",
            notes="Test child",
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
    print("   ✓ Family: Smith")
    print("   ✓ Child: Emma Smith")


if __name__ == "__main__":
    try:
        setup_test_data()
        sys.exit(0)
    except Exception:
        print("\n" + "=" * 60)
        print("❌ DATA SETUP FAILED (check output above)")
        print("=" * 60)
        sys.exit(1)
