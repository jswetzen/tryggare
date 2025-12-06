"""
Test to verify the Recently Printed fix works correctly
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from django.utils import timezone

from families.models import Family, Child, Parent
from events.models import Event, Session
from checkins.models import CheckInRecord


class RecentlyPrintedFixTest(TestCase):
    """Test that recently printed functionality works after the fix"""

    def setUp(self):
        """Set up test data"""
        User = get_user_model()
        self.user = User.objects.create_user(
            username="testuser", password="testpass", name="Test User"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Create family and children
        self.family = Family.objects.create(last_name="TestFamily")
        self.parent = Parent.objects.create(
            family=self.family,
            name="John Doe",
            relationship_type="Father",
            email="john@example.com",
            phone="555-1234",
        )

        self.child1 = Child.objects.create(
            family=self.family,
            first_name="Alice",
            last_name="Doe",
            birthdate="2020-01-01",
            qr_token="test-token-1",
        )

        self.child2 = Child.objects.create(
            family=self.family,
            first_name="Bob",
            last_name="Doe",
            birthdate="2021-01-01",
            qr_token="test-token-2",
        )

        # Create event and session
        self.event = Event.objects.create(
            name="Test Conference",
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
        )
        from datetime import timedelta
        now = timezone.now()
        self.session = Session.objects.create(
            event=self.event,
            name="Morning Session",
            start_time=now,
            end_time=now + timedelta(hours=2),
        )

    def test_recently_printed_returns_data(self):
        """Test that recently_printed endpoint returns data correctly"""
        # Create a check-in and mark as printed
        checkin = CheckInRecord.objects.create(
            child=self.child1,
            session=self.session,
            check_in_staff=self.user,
            label_printed=True,
            label_printed_at=timezone.now(),
            label_printed_by=self.user,
        )

        # Call recently_printed endpoint
        response = self.client.get('/api/print-queue/recently_printed/')

        # Verify response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['child_name'], 'Alice')
        self.assertEqual(response.data[0]['child_last_name'], 'Doe')
        self.assertTrue(response.data[0]['label_printed'])

    def test_recently_printed_updates_after_print(self):
        """Test that recently_printed list updates after marking a checkin as printed"""
        # Create two check-ins, only one printed
        checkin1 = CheckInRecord.objects.create(
            child=self.child1,
            session=self.session,
            check_in_staff=self.user,
            label_printed=False,
        )

        checkin2 = CheckInRecord.objects.create(
            child=self.child2,
            session=self.session,
            check_in_staff=self.user,
            label_printed=True,
            label_printed_at=timezone.now(),
            label_printed_by=self.user,
        )

        # Initially, only one should be in recently printed
        response = self.client.get('/api/print-queue/recently_printed/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['child_name'], 'Bob')
        self.assertEqual(response.data[0]['child_last_name'], 'Doe')

        # Mark first check-in as printed
        response = self.client.post(f'/api/print-queue/{checkin1.id}/mark_single_printed/')
        self.assertEqual(response.status_code, 200)

        # Now both should be in recently printed
        response = self.client.get('/api/print-queue/recently_printed/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        child_names = [item['child_name'] for item in response.data]
        self.assertIn('Alice', child_names)
        self.assertIn('Bob', child_names)

    def test_recently_printed_excludes_checked_out(self):
        """Test that checked out records are excluded from recently printed"""
        # Create two check-ins, both printed
        checkin1 = CheckInRecord.objects.create(
            child=self.child1,
            session=self.session,
            check_in_staff=self.user,
            label_printed=True,
            label_printed_at=timezone.now(),
            label_printed_by=self.user,
        )

        checkin2 = CheckInRecord.objects.create(
            child=self.child2,
            session=self.session,
            check_in_staff=self.user,
            label_printed=True,
            label_printed_at=timezone.now(),
            label_printed_by=self.user,
            check_out_time=timezone.now(),  # This one is checked out
            check_out_staff=self.user,
        )

        # Only the checked-in record should appear
        response = self.client.get('/api/print-queue/recently_printed/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['child_name'], 'Alice')
        self.assertEqual(response.data[0]['child_last_name'], 'Doe')
