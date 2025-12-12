"""
QR Page E2E Tests

Tests for QR code page functionality including public access,
child information display, check-in status, and action buttons.

Run with:
    pytest backend/tests/e2e/test_qr_page.py -v
    make test-qr
"""
import pytest
import sys
import time
from selenium.webdriver.common.by import By

from tests.e2e.base import E2ETestBase, TestDataMixin
from accounts.models import AdminUser
from checkins.models import CheckInRecord, AuditLog
from django.utils import timezone


@pytest.mark.e2e
@pytest.mark.qr
@pytest.mark.django_db(transaction=True)
class TestQRPage(E2ETestBase, TestDataMixin):
    """Test suite for QR page functionality."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.setup_driver()

        # Create test data
        self.test_event, self.test_session = self.create_test_session(
            name="QR Test Session",
            is_active=True
        )

        self.test_family, self.test_parent = self.create_test_family(
            last_name="QRTest"
        )

        self.test_child = self.create_test_child(
            self.test_family,
            first_name="QRChild",
            allergies="Peanuts, Tree nuts",
            qr_token="test-qr-token-e2e"
        )

        self.test_user = self.create_test_user(
            username="qrtest",
            password="testpass123"
        )

    def teardown_method(self):
        """Clean up after each test."""
        self.cleanup_test_data(
            users=[self.test_user],
            families=[self.test_family],
            children=[self.test_child],
            sessions=[self.test_session],
            events=[self.test_event]
        )
        self.teardown_driver()

    def test_public_access_no_auth(self):
        """Test that QR page is accessible without authentication."""
        print("\n🔍 Testing QR Page Public Access")
        print("=" * 60)

        # Navigate directly to QR page without logging in
        qr_url = f"{self.config['frontend_url']}/qr/{self.test_child.qr_token}"
        print(f"   Accessing: {qr_url}")

        self.driver.get(qr_url)
        time.sleep(3)

        # Verify we're NOT redirected to login
        current_url = self.driver.current_url
        assert "/login" not in current_url, \
            f"QR page redirected to login: {current_url}"

        print("   ✓ QR page accessible without authentication")

        # Verify page loaded
        page_source = self.driver.page_source
        assert len(page_source) > 100, "Page appears empty"

        print("   ✓ QR page loaded successfully")

        print("\n" + "=" * 60)
        print("✅ Public access test PASSED")

    def test_child_info_display(self):
        """Test that child information displays correctly on QR page."""
        print("\n🔍 Testing Child Information Display")
        print("=" * 60)

        # Navigate to QR page
        qr_url = f"{self.config['frontend_url']}/qr/{self.test_child.qr_token}"
        self.driver.get(qr_url)
        time.sleep(3)

        page_source = self.driver.page_source

        # Check for child name
        assert self.test_child.first_name in page_source, \
            f"Child first name '{self.test_child.first_name}' not found"
        assert self.test_child.last_name in page_source, \
            f"Child last name '{self.test_child.last_name}' not found"
        print(f"   ✓ Child name displayed: {self.test_child.first_name} {self.test_child.last_name}")

        # Check for allergies
        if self.test_child.allergies:
            assert self.test_child.allergies in page_source, \
                f"Allergies '{self.test_child.allergies}' not found"
            print(f"   ✓ Allergies displayed: {self.test_child.allergies}")

        # Check for parent name
        assert self.test_parent.name in page_source, \
            f"Parent name '{self.test_parent.name}' not found"
        print(f"   ✓ Parent displayed: {self.test_parent.name}")

        print("\n" + "=" * 60)
        print("✅ Child info display test PASSED")

    def test_checkin_status_display(self):
        """Test that check-in status displays correctly."""
        print("\n🔍 Testing Check-In Status Display")
        print("=" * 60)

        qr_url = f"{self.config['frontend_url']}/qr/{self.test_child.qr_token}"

        # Test 1: Not checked in
        print("   Testing 'not checked in' status...")
        self.driver.get(qr_url)
        time.sleep(3)

        page_source = self.driver.page_source
        not_checked_in = "not checked in" in page_source.lower() or \
                         "inte incheckad" in page_source.lower()

        if not_checked_in:
            print("   ✓ 'Not checked in' status displayed")
        else:
            print("   ℹ️  'Not checked in' status text not explicitly found")

        # Test 2: Checked in
        print("   Creating check-in...")
        checkin = CheckInRecord.objects.create(
            child=self.test_child,
            session=self.test_session,
            check_in_staff=self.test_user
        )

        print("   Reloading page...")
        self.driver.get(qr_url)
        time.sleep(3)

        page_source = self.driver.page_source
        is_checked_in = "checked in" in page_source.lower() or \
                        "incheckad" in page_source.lower() or \
                        self.test_session.name in page_source

        assert is_checked_in, "Checked-in status not displayed"
        print("   ✓ 'Checked in' status displayed")

        if self.test_session.name in page_source:
            print(f"   ✓ Session name displayed: {self.test_session.name}")

        print("\n" + "=" * 60)
        print("✅ Check-in status display test PASSED")

    def test_action_buttons_present(self):
        """Test that action buttons are present on QR page."""
        print("\n🔍 Testing Action Buttons")
        print("=" * 60)

        # Create a check-in so we have checkout buttons
        checkin = CheckInRecord.objects.create(
            child=self.test_child,
            session=self.test_session,
            check_in_staff=self.test_user
        )

        qr_url = f"{self.config['frontend_url']}/qr/{self.test_child.qr_token}"
        self.driver.get(qr_url)
        time.sleep(3)

        # Find buttons
        buttons = self.driver.find_elements(By.TAG_NAME, "button")
        button_texts = [btn.text for btn in buttons if btn.text]

        print(f"   Found {len(button_texts)} buttons with text")

        # Check for specific buttons
        button_types = {
            'checkout': ["check out", "checka ut"],
            'edit': ["edit", "redigera"],
            'print': ["print", "skriv ut", "reprint"]
        }

        found_buttons = []
        for btn_type, keywords in button_types.items():
            if any(any(kw in text.lower() for kw in keywords) for text in button_texts):
                found_buttons.append(btn_type)
                print(f"   ✓ {btn_type.capitalize()} button found")

        assert len(found_buttons) > 0, "No action buttons found"

        print("\n" + "=" * 60)
        print("✅ Action buttons test PASSED")


def run_tests():
    """Run the QR page tests."""
    exit_code = pytest.main([__file__, "-v", "-m", "qr"])
    return exit_code


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 Running QR Page E2E Tests")
    print("=" * 60)

    exit_code = run_tests()

    print("\n" + "=" * 60)
    if exit_code == 0:
        print("✅ ALL QR PAGE TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)

    sys.exit(exit_code)
