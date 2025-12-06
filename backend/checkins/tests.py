"""
Tests for check-in/check-out functionality.
"""
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from checkins.models import AuditLog, CheckInRecord
from events.models import Event, Session
from families.models import Child, Family
from accounts.models import AdminUser


class UndoCheckInTest(TestCase):
    """Test the undo check-in endpoint."""

    def setUp(self):
        """Set up test data and authentication."""
        self.client = APIClient()
        self.user = AdminUser.objects.create_user(
            username="testuser",
            password="testpass123",
            name="Test User"
        )
        self.client.force_authenticate(user=self.user)

        self.family = Family.objects.create()
        self.child = Child.objects.create(
            family=self.family,
            first_name="Test",
            last_name="Child",
            birthdate=timezone.now().date()
        )
        self.event = Event.objects.create(
            name="Test Event",
            start_date=timezone.now().date(),
            end_date=timezone.now().date()
        )
        self.session = Session.objects.create(
            event=self.event,
            name="Test Session",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=2),
            is_active=True
        )

    def test_successful_undo_within_time_window(self):
        """Test successful undo of recent check-in within 5 minute window."""
        # Create a check-in record
        checkin = CheckInRecord.objects.create(
            child=self.child,
            session=self.session,
            check_in_staff=self.user
        )

        # Verify check-in exists
        self.assertEqual(CheckInRecord.objects.count(), 1)

        # Undo the check-in
        response = self.client.post(f'/api/checkins/{checkin.id}/undo/')

        # Verify response
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])
        self.assertIn('successfully undone', response.data['message'])

        # Verify check-in record was deleted
        self.assertEqual(CheckInRecord.objects.count(), 0)

        # Verify audit log was created
        audit_logs = AuditLog.objects.filter(action='undo_checkin')
        self.assertEqual(audit_logs.count(), 1)
        audit_log = audit_logs.first()
        self.assertEqual(audit_log.user, self.user)
        self.assertEqual(audit_log.entity_id, str(checkin.id))
        self.assertEqual(audit_log.details['child_id'], str(self.child.id))

    def test_undo_fails_when_already_checked_out(self):
        """Test that undo fails when child is already checked out."""
        # Create a check-in record and check out
        checkin = CheckInRecord.objects.create(
            child=self.child,
            session=self.session,
            check_in_staff=self.user,
            check_out_time=timezone.now(),
            check_out_staff=self.user
        )

        # Try to undo the check-in
        response = self.client.post(f'/api/checkins/{checkin.id}/undo/')

        # Verify response
        self.assertEqual(response.status_code, 400)
        self.assertIn('already checked out', response.data['error'])

        # Verify check-in record still exists
        self.assertEqual(CheckInRecord.objects.count(), 1)

    def test_undo_fails_beyond_time_window(self):
        """Test that undo fails when check-in is older than 5 minutes."""
        # Create a check-in record with old timestamp
        checkin = CheckInRecord.objects.create(
            child=self.child,
            session=self.session,
            check_in_staff=self.user
        )

        # Manually set check_in_time to 6 minutes ago
        checkin.check_in_time = timezone.now() - timedelta(minutes=6)
        checkin.save()

        # Try to undo the check-in
        response = self.client.post(f'/api/checkins/{checkin.id}/undo/')

        # Verify response
        self.assertEqual(response.status_code, 400)
        self.assertIn('more than 5 minutes ago', response.data['error'])

        # Verify check-in record still exists
        self.assertEqual(CheckInRecord.objects.count(), 1)

    def test_undo_exactly_at_time_boundary(self):
        """Test undo at exactly 5 minutes (should fail since time_elapsed > 5 minutes)."""
        # Create a check-in record
        checkin = CheckInRecord.objects.create(
            child=self.child,
            session=self.session,
            check_in_staff=self.user
        )

        # Set check_in_time to exactly 5 minutes and 1 second ago
        # This ensures we're definitely past the boundary
        checkin.check_in_time = timezone.now() - timedelta(minutes=5, seconds=1)
        checkin.save()

        # Try to undo the check-in
        response = self.client.post(f'/api/checkins/{checkin.id}/undo/')

        # Verify response (should fail as it's MORE than 5 minutes)
        self.assertEqual(response.status_code, 400)
        self.assertIn('more than 5 minutes ago', response.data['error'])

        # Verify check-in record still exists
        self.assertEqual(CheckInRecord.objects.count(), 1)

    def test_undo_just_before_time_boundary(self):
        """Test undo at 4 minutes 59 seconds (should succeed)."""
        # Create a check-in record
        checkin = CheckInRecord.objects.create(
            child=self.child,
            session=self.session,
            check_in_staff=self.user
        )

        # Set check_in_time to 4 minutes 59 seconds ago
        checkin.check_in_time = timezone.now() - timedelta(minutes=4, seconds=59)
        checkin.save()

        # Try to undo the check-in
        response = self.client.post(f'/api/checkins/{checkin.id}/undo/')

        # Verify response (should succeed)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['success'])

        # Verify check-in record was deleted
        self.assertEqual(CheckInRecord.objects.count(), 0)

    def test_undo_requires_authentication(self):
        """Test that unauthenticated users cannot undo check-ins."""
        checkin = CheckInRecord.objects.create(
            child=self.child,
            session=self.session,
            check_in_staff=self.user
        )

        # Remove authentication
        self.client.force_authenticate(user=None)

        # Try to undo
        response = self.client.post(f'/api/checkins/{checkin.id}/undo/')

        # Verify response
        self.assertEqual(response.status_code, 403)

        # Verify check-in still exists
        self.assertEqual(CheckInRecord.objects.count(), 1)

    def test_undo_nonexistent_record(self):
        """Test that undo returns 404 for non-existent check-in."""
        # Try to undo a non-existent check-in
        fake_uuid = '00000000-0000-0000-0000-000000000000'
        response = self.client.post(f'/api/checkins/{fake_uuid}/undo/')

        # Verify response
        self.assertEqual(response.status_code, 404)

    def test_multiple_undo_attempts(self):
        """Test that undo cannot be called twice on the same record."""
        checkin = CheckInRecord.objects.create(
            child=self.child,
            session=self.session,
            check_in_staff=self.user
        )
        checkin_id = checkin.id

        # First undo should succeed
        response1 = self.client.post(f'/api/checkins/{checkin_id}/undo/')
        self.assertEqual(response1.status_code, 200)

        # Second undo should fail (record doesn't exist)
        response2 = self.client.post(f'/api/checkins/{checkin_id}/undo/')
        self.assertEqual(response2.status_code, 404)

        # Verify only one audit log entry
        self.assertEqual(AuditLog.objects.filter(action='undo_checkin').count(), 1)
