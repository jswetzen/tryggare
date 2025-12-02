"""
Tests for print queue functionality
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from families.models import Family, Child
from events.models import Event, Session
from checkins.models import CheckInRecord


class PrintQueueTests(TestCase):
    """Test the print queue API endpoints"""

    def setUp(self):
        """Set up test data"""
        # Create admin user
        User = get_user_model()
        self.admin_user = User.objects.create_user(
            username="testadmin", password="testpass123", name="Test Admin"
        )

        # Create family and children
        self.family = Family.objects.create()
        self.child1 = Child.objects.create(
            family=self.family,
            first_name="Alice",
            last_name="Smith",
            birthdate="2018-01-15",
            allergies="Peanuts",
        )
        self.child2 = Child.objects.create(
            family=self.family,
            first_name="Bob",
            last_name="Smith",
            birthdate="2020-03-20",
        )

        # Create event and session
        self.event = Event.objects.create(
            name="Test Event",
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
        )
        now = timezone.now()
        self.session = Session.objects.create(
            event=self.event,
            name="Test Session",
            start_time=now,
            end_time=now + timedelta(hours=2),
        )

        # Login
        self.client.login(username="testadmin", password="testpass123")

    def test_unprintable_checkins_in_queue(self):
        """Test that unprintable check-ins appear in queue"""
        # Create check-in without printing
        checkin = CheckInRecord.objects.create(
            child=self.child1,
            session=self.session,
            check_in_staff=self.admin_user,
            label_printed=False,
        )

        # Get print queue
        response = self.client.get("/api/print-queue/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], str(checkin.id))
        self.assertEqual(data[0]["child_name"], "Alice")
        self.assertEqual(data[0]["child_last_name"], "Smith")
        self.assertEqual(data[0]["allergies"], "Peanuts")
        self.assertEqual(data[0]["label_printed"], False)

    def test_printed_checkins_not_in_queue(self):
        """Test that already printed check-ins don't appear in queue"""
        # Create check-in marked as printed
        CheckInRecord.objects.create(
            child=self.child1,
            session=self.session,
            check_in_staff=self.admin_user,
            label_printed=True,
            label_printed_at=timezone.now(),
            label_printed_by=self.admin_user,
        )

        # Get print queue
        response = self.client.get("/api/print-queue/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 0)

    def test_checked_out_not_in_queue(self):
        """Test that checked-out children don't appear in queue"""
        # Create check-in that was checked out
        CheckInRecord.objects.create(
            child=self.child1,
            session=self.session,
            check_in_staff=self.admin_user,
            label_printed=False,
            check_out_time=timezone.now(),
            check_out_staff=self.admin_user,
        )

        # Get print queue
        response = self.client.get("/api/print-queue/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 0)

    def test_mark_as_printed(self):
        """Test marking check-ins as printed"""
        # Create unprintable check-in
        checkin = CheckInRecord.objects.create(
            child=self.child1,
            session=self.session,
            check_in_staff=self.admin_user,
            label_printed=False,
        )

        # Mark as printed
        response = self.client.post(
            "/api/print-queue/mark_printed/",
            data={"checkin_ids": [str(checkin.id)]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["count"], 1)

        # Verify it was marked as printed
        checkin.refresh_from_db()
        self.assertTrue(checkin.label_printed)
        self.assertIsNotNone(checkin.label_printed_at)
        self.assertEqual(checkin.label_printed_by, self.admin_user)

        # Verify queue is now empty
        response = self.client.get("/api/print-queue/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_mark_multiple_as_printed(self):
        """Test marking multiple check-ins as printed"""
        # Create two unprintable check-ins
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

        # Mark both as printed
        response = self.client.post(
            "/api/print-queue/mark_printed/",
            data={"checkin_ids": [str(checkin1.id), str(checkin2.id)]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["count"], 2)

        # Verify both were marked as printed
        checkin1.refresh_from_db()
        checkin2.refresh_from_db()
        self.assertTrue(checkin1.label_printed)
        self.assertTrue(checkin2.label_printed)

    def test_mark_printed_empty_list(self):
        """Test marking with empty list returns error"""
        response = self.client.post(
            "/api/print-queue/mark_printed/",
            data={"checkin_ids": []},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_generate_pdf_requires_auth(self):
        """Test that PDF generation requires authentication"""
        # Logout
        self.client.logout()

        # Try to generate PDF
        checkin = CheckInRecord.objects.create(
            child=self.child1,
            session=self.session,
            check_in_staff=self.admin_user,
            label_printed=False,
        )

        response = self.client.get(f"/api/print-queue/generate_pdf/?ids={checkin.id}")
        # Should be redirected to login or get 403
        self.assertIn(response.status_code, [302, 403])

    def test_generate_pdf_with_valid_ids(self):
        """Test PDF generation with valid check-in IDs"""
        # Create check-in
        checkin = CheckInRecord.objects.create(
            child=self.child1,
            session=self.session,
            check_in_staff=self.admin_user,
            label_printed=False,
        )

        # Generate PDF
        response = self.client.get(f"/api/print-queue/generate_pdf/?ids={checkin.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_generate_pdf_with_invalid_ids(self):
        """Test PDF generation with invalid IDs"""
        import uuid
        # Use a valid UUID format that doesn't exist
        fake_id = str(uuid.uuid4())
        response = self.client.get(f"/api/print-queue/generate_pdf/?ids={fake_id}")
        self.assertEqual(response.status_code, 404)

    def test_queue_ordering(self):
        """Test that queue is ordered by most recent check-in first"""
        # Create three check-ins at different times
        checkin1 = CheckInRecord.objects.create(
            child=self.child1,
            session=self.session,
            check_in_staff=self.admin_user,
            label_printed=False,
        )

        # Simulate time passing
        import time
        time.sleep(0.1)

        checkin2 = CheckInRecord.objects.create(
            child=self.child2,
            session=self.session,
            check_in_staff=self.admin_user,
            label_printed=False,
        )

        # Get print queue
        response = self.client.get("/api/print-queue/")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(len(data), 2)
        # Most recent should be first
        self.assertEqual(data[0]["id"], str(checkin2.id))
        self.assertEqual(data[1]["id"], str(checkin1.id))
