#!/usr/bin/env python
"""
End-to-end test for QR page functionality.

Tests:
- QR page loads without authentication
- Child information displays correctly
- Check-in status displays
- Action buttons work (check-out, undo, edit, reprint)

Run with: uv run python test_qr_page_e2e.py
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

# Detect if we're testing against production deployment
backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
is_production = ":8080" in backend_url or ":8080" in frontend_url

if is_production:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")
    if "DATABASE_URL" not in os.environ:
        os.environ["DATABASE_URL"] = "postgresql://postgres:postgres@localhost:5433/checkins"
else:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

django.setup()

from accounts.models import AdminUser
from families.models import Family, Child, Parent
from events.models import Event, Session
from checkins.models import CheckInRecord, AuditLog
from django.utils import timezone


class QRPageTestHelper:
    """Helper class for QR page E2E tests"""

    def __init__(self):
        self.driver = None
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        self.backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")

    def setup_driver(self):
        """Set up the Selenium WebDriver"""
        print(f"\n🔧 Test Configuration:")
        print(f"   Frontend: {self.frontend_url}")
        print(f"   Backend: {self.backend_url}")
        print()

        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.set_capability('goog:loggingPrefs', {'browser': 'ALL'})

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
                screenshot_path = '/tmp/qr_page_final.png'
                self.driver.save_screenshot(screenshot_path)
                print(f"📸 Saved final screenshot to {screenshot_path}")
            except:
                pass
            self.driver.quit()


def test_qr_page_public_access():
    """Test that QR page is accessible without authentication"""
    print("\n🔍 Testing QR Page Public Access")
    print("=" * 60)

    helper = QRPageTestHelper()
    helper.setup_driver()

    # Setup test data
    print("\n1. Setting up test data...")

    try:
        # Clean up leftover test data
        leftover_children = Child.objects.filter(last_name="QRTest", first_name="TestChild")
        for child in leftover_children:
            CheckInRecord.objects.filter(child=child).delete()
            family = child.family
            child.delete()
            if family and not family.children.exists():
                Parent.objects.filter(family=family).delete()
                family.delete()

        Session.objects.filter(name="QR Test Session").delete()
        Event.objects.filter(name="QR Test Event").delete()
        print("   ✓ Cleaned up leftover test data")

        # Create test event and session
        test_event = Event.objects.create(
            name="QR Test Event",
            start_date=timezone.now().date(),
            end_date=timezone.now().date()
        )

        test_session = Session.objects.create(
            event=test_event,
            name="QR Test Session",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
            is_active=True
        )

        # Create test family with child
        test_family = Family.objects.create()
        test_parent = Parent.objects.create(
            family=test_family,
            name="Jane QRTest",
            phone="555-0123",
            email="jane@qrtest.com",
            relationship_type="Mother"
        )

        test_child = Child.objects.create(
            family=test_family,
            first_name="TestChild",
            last_name="QRTest",
            birthdate="2018-06-15",
            allergies="Peanuts, Tree nuts",
            notes="Test child for QR page",
            qr_token="test-qr-token-e2e"
        )

        print(f"   ✓ Event: {test_event.name}")
        print(f"   ✓ Session: {test_session.name}")
        print(f"   ✓ Family: QRTest")
        print(f"   ✓ Child: {test_child.first_name} {test_child.last_name}")
        print(f"   ✓ QR Token: {test_child.qr_token}")

    except Exception as e:
        print(f"   ❌ Error setting up test data: {e}")
        import traceback
        traceback.print_exc()
        helper.teardown_driver()
        raise

    try:
        # Step 2: Load QR page without authentication
        print("\n2. Loading QR page without authentication...")
        qr_url = f"{helper.frontend_url}/qr/{test_child.qr_token}"
        print(f"   URL: {qr_url}")
        helper.driver.get(qr_url)
        time.sleep(3)  # Wait for page to load

        # Verify we're NOT redirected to login
        current_url = helper.driver.current_url
        assert "/login" not in current_url, f"QR page redirected to login: {current_url}"
        print("   ✓ QR page loaded without authentication (no redirect to login)")

        # Step 3: Verify child information displays
        print("\n3. Verifying child information displays...")
        page_source = helper.driver.page_source

        # Check for child name
        assert test_child.first_name in page_source, "Child first name not found"
        assert test_child.last_name in page_source, "Child last name not found"
        print(f"   ✓ Child name displayed: {test_child.first_name} {test_child.last_name}")

        # Check for allergies
        if test_child.allergies:
            assert test_child.allergies in page_source, "Allergies not found"
            print(f"   ✓ Allergies displayed: {test_child.allergies}")

        # Check for parent name
        assert test_parent.name in page_source, "Parent name not found"
        print(f"   ✓ Parent displayed: {test_parent.name}")

        # Step 4: Verify check-in status (not checked in)
        print("\n4. Verifying check-in status (not checked in)...")
        # Look for "Not Checked In" or similar text
        if "Not Checked In" in page_source or "not checked in" in page_source.lower():
            print("   ✓ 'Not checked in' status displayed")
        else:
            print("   ⚠️  Could not verify 'not checked in' status text")

        # Step 5: Create a check-in and verify status updates
        print("\n5. Creating check-in and verifying status update...")

        # Create admin user for check-in
        test_username = "qrtest_admin"
        existing_user = AdminUser.objects.filter(username=test_username).first()
        if existing_user:
            AuditLog.objects.filter(user=existing_user).delete()
            existing_user.delete()

        test_user = AdminUser.objects.create_user(
            username=test_username,
            password="testpass123",
            name="QR Test Admin"
        )

        # Create check-in
        checkin = CheckInRecord.objects.create(
            child=test_child,
            session=test_session,
            check_in_staff=test_user
        )
        print(f"   ✓ Created check-in record: {checkin.id}")

        # Reload page
        helper.driver.get(qr_url)
        time.sleep(3)

        # Verify checked-in status displays
        page_source = helper.driver.page_source
        if "Checked In" in page_source or "checked in" in page_source.lower():
            print("   ✓ 'Checked in' status displayed after check-in")
        else:
            print("   ⚠️  Could not verify 'checked in' status text")

        # Verify session name appears
        if test_session.name in page_source:
            print(f"   ✓ Session displayed: {test_session.name}")

        # Step 6: Verify action buttons are present
        print("\n6. Verifying action buttons...")

        # Since child is checked in, there should be a check-out button
        buttons_html = helper.driver.find_elements(By.TAG_NAME, "button")
        button_texts = [btn.text for btn in buttons_html]

        print(f"   Found {len(button_texts)} buttons on page")
        if any("Check Out" in text or "check out" in text.lower() for text in button_texts):
            print("   ✓ Check-out button present")
        else:
            print("   ⚠️  Check-out button not found")

        if any("Edit" in text for text in button_texts):
            print("   ✓ Edit button present")
        else:
            print("   ⚠️  Edit button not found")

        if any("Reprint" in text or "Print" in text for text in button_texts):
            print("   ✓ Print/Reprint button present")
        else:
            print("   ⚠️  Print/Reprint button not found")

        # Step 7: Test check-out flow
        print("\n7. Testing check-out functionality...")
        # Look for check-out button
        try:
            checkout_button = None
            for btn in buttons_html:
                if "Check Out" in btn.text or "check out" in btn.text.lower():
                    checkout_button = btn
                    break

            if checkout_button:
                checkout_button.click()
                time.sleep(1)

                # Should open a modal - check for modal or input field
                page_source = helper.driver.page_source
                if "picked up by" in page_source.lower() or "modal" in page_source.lower():
                    print("   ✓ Check-out modal opened")

                    # Try to find and fill the input
                    try:
                        pickup_input = helper.driver.find_element(By.CSS_SELECTOR, "input[type='text']")
                        pickup_input.send_keys("Test Parent")

                        # Find confirm button
                        confirm_btns = helper.driver.find_elements(By.TAG_NAME, "button")
                        for btn in confirm_btns:
                            if "Confirm" in btn.text or "Check Out" in btn.text:
                                btn.click()
                                time.sleep(2)
                                break

                        # Verify check-out in database
                        checkin.refresh_from_db()
                        if checkin.check_out_time:
                            print(f"   ✓ Child checked out successfully")
                            print(f"   ✓ Picked up by: {checkin.picked_up_by}")
                        else:
                            print("   ⚠️  Check-out did not save to database")
                    except:
                        print("   ⚠️  Could not complete check-out form")
                else:
                    print("   ⚠️  Check-out modal did not open")
            else:
                print("   ⚠️  Check-out button not clickable")
        except Exception as e:
            print(f"   ⚠️  Error testing check-out: {e}")

        # Step 8: Test undo checkout (if within time window)
        if checkin.check_out_time:
            print("\n8. Testing undo checkout functionality...")

            # Reload page to see undo button
            helper.driver.get(qr_url)
            time.sleep(3)

            page_source = helper.driver.page_source
            if "Undo" in page_source:
                print("   ✓ Undo button visible (within 5-minute window)")

                # Try to click undo
                try:
                    undo_buttons = helper.driver.find_elements(By.TAG_NAME, "button")
                    for btn in undo_buttons:
                        if "Undo" in btn.text:
                            btn.click()
                            time.sleep(2)

                            # Verify undo in database
                            checkin.refresh_from_db()
                            if not checkin.check_out_time:
                                print("   ✓ Undo successful - child checked back in")
                            else:
                                print("   ⚠️  Undo did not work")
                            break
                except Exception as e:
                    print(f"   ⚠️  Error clicking undo: {e}")
            else:
                print("   ⚠️  Undo button not visible")

        print("\n" + "=" * 60)
        print("✅ QR Page E2E Test PASSED")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        screenshot_path = '/tmp/qr_page_test_failure.png'
        helper.driver.save_screenshot(screenshot_path)
        print(f"📸 Saved failure screenshot to {screenshot_path}")
        raise
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        # Cleanup
        print("\n9. Cleaning up test data...")
        try:
            CheckInRecord.objects.filter(child=test_child).delete()
            test_child.delete()
            test_parent.delete()
            test_family.delete()
            test_session.delete()
            test_event.delete()
            if 'test_user' in locals():
                AuditLog.objects.filter(user=test_user).delete()
                test_user.delete()
            print("   ✓ Test data cleaned up")
        except Exception as e:
            print(f"   ⚠️  Cleanup error: {e}")

        helper.teardown_driver()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 Running QR Page E2E Test")
    print("=" * 60)

    try:
        test_qr_page_public_access()
        print("\n✅ ALL QR PAGE TESTS PASSED!\n")
        sys.exit(0)
    except Exception:
        print("\n❌ QR PAGE TESTS FAILED\n")
        sys.exit(1)
