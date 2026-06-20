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
from checkins.models import CheckInRecord
from checkins.qr_utils import allocate_code_for_checkin


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
            name="QR Test Session", is_active=True
        )

        self.test_family, self.test_parent = self.create_test_family(last_name="QRTest")

        self.test_child = self.create_test_child(
            self.test_family,
            first_name="QRChild",
            allergies="Peanuts, Tree nuts",
        )

        self.test_user = self.create_test_user(
            username="qrtest", password="testpass123"
        )

        # The new QR flow requires an active check-in to surface child info.
        # Tests that need the "not checked in" path should delete this record
        # (and release the allocated code) before navigating.
        self.test_checkin = CheckInRecord.objects.create(
            child=self.test_child,
            session=self.test_session,
            check_in_staff=self.test_user,
        )
        self.test_qr_code = allocate_code_for_checkin(self.test_checkin)
        self.qr_code_value = self.test_qr_code.code

    def teardown_method(self):
        """Clean up after each test."""
        self.cleanup_test_data(
            users=[self.test_user],
            families=[self.test_family],
            children=[self.test_child],
            sessions=[self.test_session],
            events=[self.test_event],
        )
        self.teardown_driver()

    def test_public_access_no_auth(self):
        """Test that QR page is accessible without authentication."""
        print("\n🔍 Testing QR Page Public Access")
        print("=" * 60)

        # Navigate directly to QR page without logging in
        qr_url = f"{self.config['frontend_url']}/qr/{self.qr_code_value}"
        print(f"   Accessing: {qr_url}")

        self.driver.get(qr_url)
        time.sleep(3)

        # Verify we're NOT redirected to login
        current_url = self.driver.current_url
        assert "/login" not in current_url, (
            f"QR page redirected to login: {current_url}"
        )

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
        qr_url = f"{self.config['frontend_url']}/qr/{self.qr_code_value}"
        self.driver.get(qr_url)
        time.sleep(3)

        page_source = self.driver.page_source

        # Check for child name
        assert self.test_child.first_name in page_source, (
            f"Child first name '{self.test_child.first_name}' not found"
        )
        assert self.test_child.last_name in page_source, (
            f"Child last name '{self.test_child.last_name}' not found"
        )
        print(
            f"   ✓ Child name displayed: {self.test_child.first_name} {self.test_child.last_name}"
        )

        # Check for allergies
        if self.test_child.allergies:
            assert self.test_child.allergies in page_source, (
                f"Allergies '{self.test_child.allergies}' not found"
            )
            print(f"   ✓ Allergies displayed: {self.test_child.allergies}")

        # Check for parent name
        assert self.test_parent.name in page_source, (
            f"Parent name '{self.test_parent.name}' not found"
        )
        print(f"   ✓ Parent displayed: {self.test_parent.name}")

        print("\n" + "=" * 60)
        print("✅ Child info display test PASSED")

    def test_checkin_status_display(self):
        """Test that check-in status displays correctly for the active check-in.

        The new privacy-first QR API only surfaces child info while actively
        checked in, so this test verifies the positive case on the check-in
        allocated in setup_method.
        """
        print("\n🔍 Testing Check-In Status Display")
        print("=" * 60)

        qr_url = f"{self.config['frontend_url']}/qr/{self.qr_code_value}"

        self.driver.get(qr_url)
        time.sleep(3)

        page_source = self.driver.page_source
        is_checked_in = (
            "checked in" in page_source.lower()
            or "incheckad" in page_source.lower()
            or self.test_session.name in page_source
        )

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

        qr_url = f"{self.config['frontend_url']}/qr/{self.qr_code_value}"
        self.driver.get(qr_url)
        time.sleep(3)

        # Find buttons
        buttons = self.driver.find_elements(By.TAG_NAME, "button")
        button_texts = [btn.text for btn in buttons if btn.text]

        print(f"   Found {len(button_texts)} buttons with text")

        # Check for specific buttons
        button_types = {
            "checkout": ["check out", "checka ut"],
            "edit": ["edit", "redigera"],
            "print": ["print", "skriv ut", "reprint"],
        }

        found_buttons = []
        for btn_type, keywords in button_types.items():
            if any(any(kw in text.lower() for kw in keywords) for text in button_texts):
                found_buttons.append(btn_type)
                print(f"   ✓ {btn_type.capitalize()} button found")

        assert len(found_buttons) > 0, "No action buttons found"

        print("\n" + "=" * 60)
        print("✅ Action buttons test PASSED")

    def test_allergy_banner_displayed(self):
        """Allergy alert renders as a prominent role='alert' banner at the top."""
        print("\n🔍 Testing Allergy Alert Banner")
        print("=" * 60)

        qr_url = f"{self.config['frontend_url']}/qr/{self.qr_code_value}"
        self.driver.get(qr_url)
        time.sleep(3)

        alerts = self.driver.find_elements(By.CSS_SELECTOR, "[role='alert']")
        assert alerts, "Expected an allergy alert banner (role='alert')"

        banner_text = alerts[0].text
        assert "Peanuts" in banner_text, (
            f"Allergy text missing from banner: {banner_text!r}"
        )
        # The label is rendered through a CSS uppercase transform, so match
        # case-insensitively and accept either locale (app defaults to Swedish).
        banner_lower = banner_text.lower()
        assert "allergy alert" in banner_lower or "allergivarning" in banner_lower, (
            f"Allergy alert label missing from banner: {banner_text!r}"
        )
        print(f"   ✓ Allergy banner shown: {banner_text!r}")

        # Banner should sit above the child info card (safety info above the fold).
        body = self.driver.find_element(By.TAG_NAME, "body").text.lower()
        label = "allergy alert" if "allergy alert" in body else "allergivarning"
        assert body.index(label) < body.index(self.test_child.first_name.lower()), (
            "Allergy banner should appear above the child name/info card"
        )
        print("   ✓ Banner positioned above the info card")

        print("\n" + "=" * 60)
        print("✅ Allergy banner test PASSED")

    def test_age_displayed(self):
        """Child age (whole years from birthdate) is displayed next to the name."""
        from datetime import date

        print("\n🔍 Testing Age Display")
        print("=" * 60)

        bd = self.test_child.birthdate
        dob = bd if isinstance(bd, date) else date.fromisoformat(str(bd))
        today = date.today()
        expected_age = (
            today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        )

        qr_url = f"{self.config['frontend_url']}/qr/{self.qr_code_value}"
        self.driver.get(qr_url)
        time.sleep(3)

        # App defaults to Swedish ("{years} år"); accept either locale.
        page_source = self.driver.page_source
        assert (
            f"{expected_age} years" in page_source
            or f"{expected_age} år" in page_source
        ), f"Expected age '{expected_age}' (years/år) not found on page"
        print(f"   ✓ Age displayed: {expected_age}")

        print("\n" + "=" * 60)
        print("✅ Age display test PASSED")

    def test_no_allergy_no_banner(self):
        """A child without allergies shows no allergy banner."""
        print("\n🔍 Testing No-Allergy Child (no banner)")
        print("=" * 60)

        child2 = self.create_test_child(
            self.test_family, first_name="NoAllergyKid", allergies=""
        )
        checkin2 = CheckInRecord.objects.create(
            child=child2,
            session=self.test_session,
            check_in_staff=self.test_user,
        )
        code2 = allocate_code_for_checkin(checkin2).code

        self.driver.get(f"{self.config['frontend_url']}/qr/{code2}")
        time.sleep(3)

        page_source = self.driver.page_source
        assert "NoAllergyKid" in page_source, "Child info did not load"

        alerts = self.driver.find_elements(By.CSS_SELECTOR, "[role='alert']")
        assert not alerts, "No allergy banner expected for a child without allergies"
        print("   ✓ No allergy banner for child without allergies")

        print("\n" + "=" * 60)
        print("✅ No-allergy banner test PASSED")

    def test_reprint_logged_out_opens_print_page(self):
        """Reprint while logged out (no printers) falls back to the print page."""
        print("\n🔍 Testing Reprint Fallback (logged out)")
        print("=" * 60)

        self.driver.get(f"{self.config['frontend_url']}/qr/{self.qr_code_value}")
        time.sleep(3)

        reprint = None
        for btn in self.driver.find_elements(By.TAG_NAME, "button"):
            if btn.text and (
                "reprint" in btn.text.lower() or "skriv ut" in btn.text.lower()
            ):
                reprint = btn
                break
        assert reprint, "Reprint button not found"

        initial_handles = len(self.driver.window_handles)
        reprint.click()
        time.sleep(2)

        opened_new_tab = len(self.driver.window_handles) > initial_handles
        page_source = self.driver.page_source
        shows_message = (
            "Opening print page" in page_source
            or "Öppnar utskriftssida" in page_source
        )
        assert opened_new_tab or shows_message, (
            "Reprint did not trigger the print-page fallback (no new tab / message)"
        )
        print(
            f"   ✓ Reprint fallback triggered (new_tab={opened_new_tab}, "
            f"message={shows_message})"
        )

        print("\n" + "=" * 60)
        print("✅ Reprint fallback test PASSED")


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
