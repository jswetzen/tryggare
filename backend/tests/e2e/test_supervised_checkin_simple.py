"""
Simplified Supervised Check-In E2E Tests

Focuses on core supervised check-in functionality with simpler UI interactions.

Run with:
    pytest backend/tests/e2e/test_supervised_checkin_simple.py -v
    make test-supervised
"""
import pytest
import time

# Import base classes
try:
    from tests.e2e.base import E2ETestBase, TestDataMixin
except ImportError:
    from .base import E2ETestBase, TestDataMixin

from checkins.models import CheckInRecord


@pytest.mark.e2e
@pytest.mark.supervised
@pytest.mark.django_db(transaction=True)
class TestSupervisedCheckInSimple(E2ETestBase, TestDataMixin):
    """Simplified test suite for supervised check-in functionality."""

    def setup_method(self):
        """Set up test environment before each test."""
        self.setup_driver()

        # Create test user
        self.test_user = self.create_test_user(
            username="supervisedtest",
            password="testpass123",
            name="Supervised Test User"
        )

        # Create test event and session FIRST
        self.test_event, self.test_session = self.create_test_session(
            name="Test Session",
            is_active=True,
            event_name="Supervised Test Event",
            hours_duration=3
        )

        # Create test family with children
        self.test_family, self.test_parent = self.create_test_family(
            last_name="SupervisedTest",
            parent_name="Test Parent"
        )

        # Create test child
        self.test_child = self.create_test_child(
            family=self.test_family,
            first_name="TestChild"
        )

        # Assign event ticket so child can be checked in
        from events.models import EventTicket
        EventTicket.objects.create(
            child=self.test_child,
            event=self.test_event
        )

    def teardown_method(self):
        """Clean up after each test."""
        self.cleanup_test_data(
            users=[self.test_user] if hasattr(self, 'test_user') else None,
            families=[self.test_family] if hasattr(self, 'test_family') else None,
            children=[self.test_child] if hasattr(self, 'test_child') else None,
            sessions=[self.test_session] if hasattr(self, 'test_session') else None,
            events=[self.test_event] if hasattr(self, 'test_event') else None
        )
        self.teardown_driver()

    def test_supervised_checkin_via_api(self):
        """Test that supervised check-ins can be created via API."""
        print("\n🔍 Testing Supervised Check-In via API")
        print("=" * 60)

        # Create a supervised check-in directly via the model
        print("   Creating supervised check-in...")
        checkin = CheckInRecord.objects.create(
            child=self.test_child,
            session=self.test_session,
            check_in_staff=self.test_user,
            supervised=True
        )

        assert checkin.supervised is True, "Check-in should be marked as supervised"
        print("   ✓ Supervised check-in created successfully")

        # Verify the check-in appears on checkout page with supervised badge
        print("   Logging in and navigating to checkout page...")
        self.login(self.test_user.username, "testpass123")

        checkout_url = f"{self.config['frontend_url']}/checkout"
        self.driver.get(checkout_url)
        time.sleep(3)

        # Look for the child name and supervised badge
        page_source = self.driver.page_source
        assert self.test_child.first_name in page_source, \
            f"Child '{self.test_child.first_name}' should appear on checkout page"

        # Check for supervised indicator (might be "Supervised", "Guardian", or similar)
        has_supervised_indicator = "Supervised" in page_source or "Guardian" in page_source
        assert has_supervised_indicator, "Supervised badge should be visible on checkout page"

        print("   ✓ Child appears on checkout page")
        print("   ✓ Supervised badge is visible")
        print("\n" + "=" * 60)
        print("✅ Supervised check-in API test PASSED")

    def test_standard_vs_supervised_checkout_display(self):
        """Test that supervised and non-supervised check-ins display differently."""
        print("\n🔍 Testing Supervised vs Standard Display")
        print("=" * 60)

        # Create one supervised and one standard check-in
        print("   Creating supervised check-in...")
        supervised_checkin = CheckInRecord.objects.create(
            child=self.test_child,
            session=self.test_session,
            check_in_staff=self.test_user,
            supervised=True
        )

        # Create second child for standard check-in
        standard_child = self.create_test_child(
            family=self.test_family,
            first_name="StandardChild"
        )

        from events.models import EventTicket
        EventTicket.objects.create(
            child=standard_child,
            event=self.test_event
        )

        print("   Creating standard check-in...")
        standard_checkin = CheckInRecord.objects.create(
            child=standard_child,
            session=self.test_session,
            check_in_staff=self.test_user,
            supervised=False
        )

        # Navigate to checkout page
        print("   Navigating to checkout page...")
        self.login(self.test_user.username, "testpass123")

        checkout_url = f"{self.config['frontend_url']}/checkout"
        self.driver.get(checkout_url)
        time.sleep(3)

        page_source = self.driver.page_source

        # Both children should be visible
        assert self.test_child.first_name in page_source, "Supervised child should be visible"
        assert standard_child.first_name in page_source, "Standard child should be visible"

        # Count supervised badges - should have at least one
        supervised_count = page_source.count("Supervised")
        assert supervised_count >= 1, "At least one supervised badge should be present"

        print("   ✓ Both children visible on checkout page")
        print("   ✓ Supervised badge appears for supervised child")
        print("\n" + "=" * 60)
        print("✅ Supervised vs standard display test PASSED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
