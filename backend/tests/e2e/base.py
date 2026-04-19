"""
Base classes and helpers for E2E tests.

This module provides shared functionality for all Selenium-based end-to-end tests,
including WebDriver setup, common actions, and test data creation.
"""
import os
import time
from typing import Optional, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webelement import WebElement

# Setup Django if not already configured (for standalone execution)
import django
from django.conf import settings
if not settings.configured:
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
    django.setup()

# Now safe to import Django models
from django.utils import timezone
from accounts.models import AdminUser
from families.models import Family, Child, Parent
from events.models import Event, Session
from checkins.models import CheckInRecord, AuditLog


class E2ETestBase:
    """Base class for all E2E tests with common setup and helpers."""

    @classmethod
    def get_test_config(cls) -> dict:
        """Get test configuration based on environment variables."""
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        is_production = ":8080" in backend_url or ":8080" in frontend_url

        return {
            'backend_url': backend_url,
            'frontend_url': frontend_url,
            'is_production': is_production,
            'selenium_hub': os.getenv("SELENIUM_HUB_URL"),
        }

    def setup_driver(self):
        """Set up Selenium WebDriver with appropriate configuration."""
        # Initialize instance attributes
        self.driver: Optional[webdriver.Remote] = None
        self.config = self.get_test_config()

        print(f"\n🔧 Test Configuration:")
        print(f"   Frontend: {self.config['frontend_url']}")
        print(f"   Backend: {self.config['backend_url']}")
        print(f"   Production mode: {self.config['is_production']}")

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

        # Use remote or local driver based on environment
        if self.config['selenium_hub']:
            print(f"   Using remote Selenium Grid: {self.config['selenium_hub']}")
            self.driver = webdriver.Remote(
                command_executor=f"{self.config['selenium_hub']}/wd/hub",
                options=chrome_options
            )
        else:
            print("   Using local ChromeDriver")
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)

        self.driver.implicitly_wait(3)
        print("   ✓ WebDriver initialized\n")

    def teardown_driver(self):
        """Clean up WebDriver and save final screenshot."""
        if self.driver:
            try:
                screenshot_path = '/tmp/final_state.png'
                self.driver.save_screenshot(screenshot_path)
                print(f"📸 Saved final screenshot to {screenshot_path}")
            except Exception as e:
                print(f"⚠️  Could not save screenshot: {e}")

            self.driver.quit()

    def login(self, username: str, password: str) -> bool:
        """
        Perform login with given credentials.

        Args:
            username: Username to log in with
            password: Password for the user

        Returns:
            True if login successful, False otherwise
        """
        print(f"   Logging in as {username}...")
        login_url = f"{self.config['frontend_url']}/login"
        self.driver.get(login_url)

        # Wait for login form
        username_field = self.wait_for_element(By.ID, "username")
        password_field = self.wait_for_element(By.ID, "password")

        # Fill in credentials
        username_field.send_keys(username)
        password_field.send_keys(password)

        # Submit
        submit_button = self.wait_for_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_button.click()

        # Wait for redirect to check-in page
        try:
            WebDriverWait(self.driver, 10).until(
                EC.url_contains("/checkin")
            )
            print("   ✓ Login successful")
            return True
        except Exception:
            print(f"   ❌ Login failed. Current URL: {self.driver.current_url}")
            return False

    def wait_for_element(self, by: By, value: str, timeout: int = 10) -> WebElement:
        """
        Wait for element to be present and return it.

        Args:
            by: Selenium By locator strategy
            value: Locator value
            timeout: Maximum time to wait in seconds

        Returns:
            WebElement when found
        """
        return WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )

    def wait_and_click(self, by: By, value: str, timeout: int = 10) -> WebElement:
        """
        Wait for element to be clickable and click it.

        Args:
            by: Selenium By locator strategy
            value: Locator value
            timeout: Maximum time to wait in seconds

        Returns:
            WebElement after clicking
        """
        element = WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        element.click()
        return element

    def wait_for_url_contains(self, text: str, timeout: int = 10):
        """Wait for URL to contain specific text."""
        WebDriverWait(self.driver, timeout).until(
            EC.url_contains(text)
        )

    def save_screenshot(self, name: str):
        """Save a screenshot with given name."""
        path = f'/tmp/{name}.png'
        self.driver.save_screenshot(path)
        print(f"📸 Saved screenshot: {path}")


class TestDataMixin:
    """Mixin for creating and cleaning up test data."""

    def create_test_user(
        self,
        username: str = "testuser",
        password: str = "testpass123",
        name: Optional[str] = None
    ) -> 'AdminUser':
        """
        Create a test admin user, cleaning up any existing user with same username.

        Args:
            username: Username for the user
            password: Password for the user
            name: Display name (defaults to "Test User {username}")

        Returns:
            Created AdminUser instance
        """
        # Clean up existing user
        existing = AdminUser.objects.filter(username=username).first()
        if existing:
            AuditLog.objects.filter(user=existing).delete()
            existing.delete()

        if name is None:
            name = f"Test User {username}"

        return AdminUser.objects.create_user(
            username=username,
            password=password,
            name=name
        )

    def create_test_family(
        self,
        last_name: str = "TestFamily",
        parent_name: Optional[str] = None,
        phone: str = "555-0000"
    ) -> Tuple[Family, Parent]:
        """
        Create a test family with one parent.

        Args:
            last_name: Family last name
            parent_name: Parent's name (defaults to "Test Parent {last_name}")
            phone: Parent's phone number

        Returns:
            Tuple of (Family, Parent)
        """
        # Clean up any existing family with same name
        existing_families = Family.objects.filter(last_name=last_name)
        for family in existing_families:
            # Clean up children first
            Child.objects.filter(family=family).delete()
            # Clean up parents
            Parent.objects.filter(family=family).delete()
            # Clean up family
            family.delete()

        family = Family.objects.create(last_name=last_name)

        if parent_name is None:
            parent_name = f"Test Parent {last_name}"

        parent = Parent.objects.create(
            family=family,
            name=parent_name,
            phone=phone,
            email=f"{last_name.lower()}@test.com",
            relationship_type="Parent"
        )

        return family, parent

    def create_test_child(
        self,
        family: Family,
        first_name: str = "TestChild",
        birthdate: str = "2018-01-01",
        allergies: str = "",
    ) -> Child:
        """
        Create a test child for a family.

        Args:
            family: Family instance
            first_name: Child's first name
            birthdate: Birth date in YYYY-MM-DD format
            allergies: Allergy information

        Returns:
            Created Child instance
        """
        return Child.objects.create(
            family=family,
            first_name=first_name,
            last_name=family.last_name,
            birthdate=birthdate,
            allergies=allergies,
        )

    def create_test_session(
        self,
        name: str = "Test Session",
        is_active: bool = True,
        event_name: Optional[str] = None,
        hours_duration: int = 2
    ) -> Tuple[Event, Session]:
        """
        Create a test event and session.

        Args:
            name: Session name
            is_active: Whether session is active
            event_name: Event name (defaults to "Test Event {name}")
            hours_duration: Session duration in hours

        Returns:
            Tuple of (Event, Session)
        """
        # Clean up existing sessions with same name
        Session.objects.filter(name=name).delete()

        if event_name is None:
            event_name = f"Test Event {name}"

        # Clean up existing events with same name
        Event.objects.filter(name=event_name).delete()

        now = timezone.now()

        event = Event.objects.create(
            name=event_name,
            start_date=now.date(),
            end_date=now.date()
        )

        session = Session.objects.create(
            event=event,
            name=name,
            start_time=now,
            end_time=now + timezone.timedelta(hours=hours_duration),
            is_active=is_active,
            requires_ticket=False
        )

        return event, session

    def cleanup_test_data(
        self,
        users: list = None,
        families: list = None,
        children: list = None,
        sessions: list = None,
        events: list = None
    ):
        """
        Clean up test data in correct order to respect foreign key constraints.

        Args:
            users: List of AdminUser instances to delete
            families: List of Family instances to delete
            children: List of Child instances to delete
            sessions: List of Session instances to delete
            events: List of Event instances to delete
        """
        print("\n   Cleaning up test data...")

        # Delete children and their check-in records first
        if children:
            for child in children:
                try:
                    CheckInRecord.objects.filter(child=child).delete()
                    child.delete()
                except Exception as e:
                    print(f"   ⚠️  Error deleting child {child.id}: {e}")

        # Delete families and their parents
        if families:
            for family in families:
                try:
                    Child.objects.filter(family=family).delete()
                    Parent.objects.filter(family=family).delete()
                    family.delete()
                except Exception as e:
                    print(f"   ⚠️  Error deleting family {family.id}: {e}")

        # Delete sessions
        if sessions:
            for session in sessions:
                try:
                    session.delete()
                except Exception as e:
                    print(f"   ⚠️  Error deleting session {session.id}: {e}")

        # Delete events
        if events:
            for event in events:
                try:
                    event.delete()
                except Exception as e:
                    print(f"   ⚠️  Error deleting event {event.id}: {e}")

        # Delete users and their audit logs
        if users:
            for user in users:
                try:
                    AuditLog.objects.filter(user=user).delete()
                    user.delete()
                except Exception as e:
                    print(f"   ⚠️  Error deleting user {user.username}: {e}")

        print("   ✓ Test data cleaned up")
