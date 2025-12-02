"""
End-to-end tests for print queue workflow using Selenium
"""

import time
from django.test import LiveServerTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from families.models import Family, Child, Parent
from events.models import Event, Session
from checkins.models import CheckInRecord


class PrintQueueE2ETest(LiveServerTestCase):
    """End-to-end tests for print queue functionality"""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        cls.selenium = webdriver.Chrome(options=options)
        cls.selenium.implicitly_wait(10)

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def setUp(self):
        """Set up test data"""
        # Create admin user
        User = get_user_model()
        self.admin_user = User.objects.create_user(
            username="printtest", password="testpass123", name="Print Test Admin"
        )

        # Create family with children
        self.family = Family.objects.create()
        self.parent = Parent.objects.create(
            family=self.family,
            name="John Doe",
            phone="555-1234",
            relationship_type="DAD",
        )
        self.child1 = Child.objects.create(
            family=self.family,
            first_name="Charlie",
            last_name="Doe",
            birthdate="2017-06-10",
            qr_token="test-token-1",
            allergies="Milk",
        )
        self.child2 = Child.objects.create(
            family=self.family,
            first_name="Diana",
            last_name="Doe",
            birthdate="2019-09-15",
            qr_token="test-token-2",
        )

        # Create event and session
        self.event = Event.objects.create(
            name="Print Test Event",
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
        )
        now = timezone.now()
        from datetime import timedelta
        self.session = Session.objects.create(
            event=self.event,
            name="Print Test Session",
            start_time=now,
            end_time=now + timedelta(hours=2),
            is_active=True,
        )

    def login(self):
        """Helper to login as admin"""
        self.selenium.get(f"{self.live_server_url}/")
        wait = WebDriverWait(self.selenium, 10)

        # Wait for login form
        username_field = wait.until(
            EC.presence_of_element_located((By.NAME, "username"))
        )
        username_field.send_keys("printtest")

        password_field = self.selenium.find_element(By.NAME, "password")
        password_field.send_keys("testpass123")

        login_button = self.selenium.find_element(By.CSS_SELECTOR, "button[type='submit']")
        login_button.click()

        # Wait for redirect to check-in page
        wait.until(EC.url_contains("/checkin"))

    def test_print_queue_shows_unprintable_checkins(self):
        """Test that print queue displays unprintable check-ins"""
        # Create unprintable check-ins
        checkin1 = CheckInRecord.objects.create(
            child=self.child1,
            session=self.session,
            check_in_staff=self.admin_user,
            label_printed=False,
        )
        checkin2 = CheckInRecord.objects.create(
            child=self.child2,
            session=self.session,
            check_in_staff=self.admin_user,
            label_printed=False,
        )

        # Login
        self.login()

        # Navigate to print queue
        self.selenium.get(f"{self.live_server_url}/print-queue")
        wait = WebDriverWait(self.selenium, 10)

        # Wait for queue to load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))

        # Verify both children are shown
        page_text = self.selenium.page_source
        self.assertIn("Charlie Doe", page_text)
        self.assertIn("Diana Doe", page_text)
        self.assertIn("Print Test Session", page_text)

        # Verify allergy is shown
        self.assertIn("Milk", page_text)

    def test_print_queue_empty_state(self):
        """Test print queue when no labels need printing"""
        # Login
        self.login()

        # Navigate to print queue
        self.selenium.get(f"{self.live_server_url}/print-queue")
        wait = WebDriverWait(self.selenium, 10)

        # Should show empty state
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))

        page_text = self.selenium.page_source
        self.assertIn("No labels need printing", page_text)

    def test_select_and_mark_as_printed(self):
        """Test selecting items and marking as printed"""
        # Create unprintable check-in
        checkin = CheckInRecord.objects.create(
            child=self.child1,
            session=self.session,
            check_in_staff=self.admin_user,
            label_printed=False,
        )

        # Login
        self.login()

        # Navigate to print queue
        self.selenium.get(f"{self.live_server_url}/print-queue")
        wait = WebDriverWait(self.selenium, 10)

        # Wait for table to load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))

        # Find and click the checkbox for the child
        checkboxes = self.selenium.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
        # First checkbox should be in the table row
        if len(checkboxes) > 1:
            checkboxes[1].click()  # Skip the "select all" checkbox

        # Click "Mark as Printed" button
        mark_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Mark as Printed')]"))
        )
        mark_button.click()

        # Wait for success message
        try:
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "alert-success")))
            page_text = self.selenium.page_source
            self.assertIn("marked as printed", page_text.lower())
        except TimeoutException:
            print("Success message not found, checking database directly")

        # Verify database was updated
        checkin.refresh_from_db()
        self.assertTrue(checkin.label_printed)

    def test_select_all_functionality(self):
        """Test select all button"""
        # Create multiple unprintable check-ins
        CheckInRecord.objects.create(
            child=self.child1,
            session=self.session,
            check_in_staff=self.admin_user,
            label_printed=False,
        )
        CheckInRecord.objects.create(
            child=self.child2,
            session=self.session,
            check_in_staff=self.admin_user,
            label_printed=False,
        )

        # Login
        self.login()

        # Navigate to print queue
        self.selenium.get(f"{self.live_server_url}/print-queue")
        wait = WebDriverWait(self.selenium, 10)

        # Wait for table to load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))

        # Click "Select All" button
        select_all_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Select All')]"))
        )
        select_all_button.click()

        # Verify checkboxes are checked
        time.sleep(0.5)  # Give UI time to update
        checkboxes = self.selenium.find_elements(By.CSS_SELECTOR, "input[type='checkbox']:checked")
        # Should have at least 2 checked (the row checkboxes)
        self.assertGreaterEqual(len(checkboxes), 2)

    def test_navigation_to_qr_page(self):
        """Test that View QR link works"""
        # Create unprintable check-in
        CheckInRecord.objects.create(
            child=self.child1,
            session=self.session,
            check_in_staff=self.admin_user,
            label_printed=False,
        )

        # Login
        self.login()

        # Navigate to print queue
        self.selenium.get(f"{self.live_server_url}/print-queue")
        wait = WebDriverWait(self.selenium, 10)

        # Wait for table to load
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))

        # Find and click "View QR" link
        qr_link = wait.until(
            EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, "View QR"))
        )
        qr_link.click()

        # Switch to new tab
        time.sleep(1)
        self.selenium.switch_to.window(self.selenium.window_handles[-1])

        # Wait for QR page to load
        wait.until(EC.url_contains("/qr/"))

        # Verify we're on the QR page
        page_text = self.selenium.page_source
        self.assertIn("Charlie Doe", page_text)

    def test_print_queue_navigation_link(self):
        """Test that Print Queue link appears in navigation"""
        # Login
        self.login()

        # Should be on check-in page
        wait = WebDriverWait(self.selenium, 10)
        wait.until(EC.url_contains("/checkin"))

        # Find Print Queue link in nav
        nav_link = wait.until(
            EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Print Queue"))
        )

        # Click it
        nav_link.click()

        # Verify we're on print queue page
        wait.until(EC.url_contains("/print-queue"))
        self.assertIn("/print-queue", self.selenium.current_url)

    def test_checked_out_not_in_queue(self):
        """Test that checked-out children don't appear in queue"""
        # Create checked-out check-in
        CheckInRecord.objects.create(
            child=self.child1,
            session=self.session,
            check_in_staff=self.admin_user,
            label_printed=False,
            check_out_time=timezone.now(),
            check_out_staff=self.admin_user,
        )

        # Login
        self.login()

        # Navigate to print queue
        self.selenium.get(f"{self.live_server_url}/print-queue")
        wait = WebDriverWait(self.selenium, 10)

        # Should show empty state
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))

        page_text = self.selenium.page_source
        self.assertIn("No labels need printing", page_text)
        self.assertNotIn("Charlie Doe", page_text)
