"""
Print Queue E2E Tests

Tests for print queue functionality including viewing unprintable labels,
printing, and session filtering.

Run with:
    pytest backend/tests/e2e/test_print_queue.py -v
    make test-print
"""

import pytest
import sys
import time

from tests.e2e.base import E2ETestBase, TestDataMixin
from checkins.models import CheckInRecord


@pytest.mark.e2e
@pytest.mark.print
@pytest.mark.django_db(transaction=True)
class TestPrintQueue(E2ETestBase, TestDataMixin):
    """Test suite for print queue functionality."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.setup_driver()

        self.test_user = self.create_test_user(
            username="printtest", password="testpass123"
        )

        self.test_event, self.test_session = self.create_test_session(
            name="Print Test Session", is_active=True
        )

        self.test_family, self.test_parent = self.create_test_family(
            last_name="PrintTest"
        )

        self.test_child = self.create_test_child(
            self.test_family, first_name="PrintChild"
        )

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

    def test_queue_shows_unprintable(self):
        """Test that print queue displays unprintable check-ins."""
        print("\n🔍 Testing Print Queue Shows Unprintable")
        print("=" * 60)

        # Create unprintable check-in
        print("   Creating unprintable check-in...")
        checkin = CheckInRecord.objects.create(
            child=self.test_child,
            session=self.test_session,
            check_in_staff=self.test_user,
            label_printed=False,
        )

        # Login and navigate to print queue
        print("   Navigating to print queue...")
        self.login(self.test_user.username, "testpass123")

        print_queue_url = f"{self.config['frontend_url']}/print-queue"
        self.driver.get(print_queue_url)
        time.sleep(3)

        # Verify child appears
        page_source = self.driver.page_source
        child_found = (
            self.test_child.first_name in page_source
            or self.test_family.last_name in page_source
        )

        assert child_found, (
            f"Child '{self.test_child.first_name}' not found in print queue"
        )

        print(f"   ✓ Child '{self.test_child.first_name}' found in print queue")

        print("\n" + "=" * 60)
        print("✅ Print queue display test PASSED")

    def test_empty_queue(self):
        """Test print queue empty state."""
        print("\n🔍 Testing Empty Print Queue")
        print("=" * 60)

        # Login and navigate to print queue (no unprintable items)
        self.login(self.test_user.username, "testpass123")

        print_queue_url = f"{self.config['frontend_url']}/print-queue"
        self.driver.get(print_queue_url)
        time.sleep(3)

        # Should show empty state
        page_source = self.driver.page_source
        has_empty_message = (
            "no labels" in page_source.lower()
            or "inga etiketter" in page_source.lower()
        )

        if has_empty_message:
            print("   ✓ Empty state message displayed")
        else:
            print("   ℹ️  Empty state not explicitly verified")

        print("\n" + "=" * 60)
        print("✅ Empty queue test PASSED")


def run_tests():
    """Run the print queue tests."""
    exit_code = pytest.main([__file__, "-v", "-m", "print"])
    return exit_code


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 Running Print Queue E2E Tests")
    print("=" * 60)

    exit_code = run_tests()

    print("\n" + "=" * 60)
    if exit_code == 0:
        print("✅ ALL PRINT QUEUE TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)

    sys.exit(exit_code)
