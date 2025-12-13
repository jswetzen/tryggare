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


class PrintLabelTest(TestCase):
    """Test the print label functionality."""

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
        self.checkin = CheckInRecord.objects.create(
            child=self.child,
            session=self.session,
            check_in_staff=self.user
        )

    def test_print_page_returns_html(self):
        """Test that print_page endpoint returns HTML."""
        response = self.client.get(f'/api/print-queue/{self.checkin.id}/print_page/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response['Content-Type'])

    def test_print_page_contains_child_name(self):
        """Test that print label contains child's name."""
        response = self.client.get(f'/api/print-queue/{self.checkin.id}/print_page/')
        content = response.content.decode('utf-8')
        self.assertIn('Test', content)
        self.assertIn('Child', content)

    def test_print_page_contains_qr_code_as_data_url(self):
        """Test that print label contains QR code as base64 data URL."""
        response = self.client.get(f'/api/print-queue/{self.checkin.id}/print_page/')
        content = response.content.decode('utf-8')
        # Should contain base64 encoded image
        self.assertIn('data:image/png;base64,', content)
        # Should NOT contain API URL
        self.assertNotIn('/api/qr/', content)

    def test_print_page_has_correct_dimensions(self):
        """Test that print label has correct page dimensions (54.3mm x 17mm)."""
        response = self.client.get(f'/api/print-queue/{self.checkin.id}/print_page/')
        content = response.content.decode('utf-8')
        self.assertIn('54.3mm', content)
        self.assertIn('17mm', content)

    def test_print_page_does_not_contain_session_or_allergies(self):
        """Test that simplified label doesn't contain session name or allergies."""
        # Add allergies to child
        self.child.allergies = "Peanuts, Dairy"
        self.child.save()

        response = self.client.get(f'/api/print-queue/{self.checkin.id}/print_page/')
        content = response.content.decode('utf-8')

        # Get the label div content
        if '<div class="label">' in content:
            label_content = content.split('<div class="label">')[1].split('</div>')[0]
            # Should NOT contain session name in label content
            self.assertNotIn('Test Session', label_content)

        # Should NOT contain allergies anywhere
        self.assertNotIn('ALLERGIES', content)
        self.assertNotIn('Peanuts', content)


class SupervisedCheckInTest(TestCase):
    """Test supervised check-in functionality."""

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

        # Create multiple sessions for testing transitions
        self.session1 = Session.objects.create(
            event=self.event,
            name="Session 1",
            start_time=timezone.now() - timedelta(hours=2),
            end_time=timezone.now() - timedelta(hours=1),
            is_active=False  # Ended session
        )

        self.session2 = Session.objects.create(
            event=self.event,
            name="Session 2",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=2),
            is_active=True  # Active session
        )

        self.session3 = Session.objects.create(
            event=self.event,
            name="Session 3",
            start_time=timezone.now() + timedelta(hours=3),
            end_time=timezone.now() + timedelta(hours=5),
            is_active=False  # Future session (not started yet)
        )

    def test_standard_check_in_without_supervised_flag(self):
        """Test that standard check-in works as before (no supervised flag)."""
        response = self.client.post('/api/checkins/check_in/', {
            'child': str(self.child.id),
            'session': str(self.session2.id)
        })

        self.assertEqual(response.status_code, 201)
        self.assertFalse(response.data['supervised'])

        record = CheckInRecord.objects.get(id=response.data['id'])
        self.assertFalse(record.supervised)

    def test_supervised_check_in_creates_record_with_flag(self):
        """Test that supervised check-in creates record with supervised=True."""
        response = self.client.post('/api/checkins/check_in/', {
            'child': str(self.child.id),
            'session': str(self.session2.id),
            'supervised': True
        })

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data['supervised'])

        record = CheckInRecord.objects.get(id=response.data['id'])
        self.assertTrue(record.supervised)

    def test_supervised_check_in_to_ended_session_allows_new_check_in(self):
        """Test supervised check-in to ended session allows check-in to new session."""
        # Create supervised check-in to ended session (session1)
        CheckInRecord.objects.create(
            child=self.child,
            session=self.session1,
            check_in_staff=self.user,
            supervised=True
        )

        # Should be able to check into new session (session2)
        response = self.client.post('/api/checkins/check_in/', {
            'child': str(self.child.id),
            'session': str(self.session2.id),
            'supervised': True
        })

        self.assertEqual(response.status_code, 201)
        # Verify both records exist
        self.assertEqual(CheckInRecord.objects.filter(child=self.child).count(), 2)

    def test_supervised_check_in_to_active_session_blocks_new_check_in(self):
        """Test supervised check-in to active session blocks check-in to new session."""
        # Create supervised check-in to active session (session2)
        CheckInRecord.objects.create(
            child=self.child,
            session=self.session2,
            check_in_staff=self.user,
            supervised=True
        )

        # Should NOT be able to check into another session (session3)
        response = self.client.post('/api/checkins/check_in/', {
            'child': str(self.child.id),
            'session': str(self.session3.id),
            'supervised': True
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn('active supervised session', response.data['error'])

    def test_supervised_check_in_with_is_active_true_but_end_time_passed(self):
        """Test supervised check-in with is_active=True but end_time passed allows new check-in."""
        # Create session that is marked active but time has passed
        past_session = Session.objects.create(
            event=self.event,
            name="Past Active Session",
            start_time=timezone.now() - timedelta(hours=3),
            end_time=timezone.now() - timedelta(minutes=1),  # Just ended
            is_active=True  # Still marked active
        )

        # Create supervised check-in to this session
        CheckInRecord.objects.create(
            child=self.child,
            session=past_session,
            check_in_staff=self.user,
            supervised=True
        )

        # Should be able to check into new session since end_time has passed
        response = self.client.post('/api/checkins/check_in/', {
            'child': str(self.child.id),
            'session': str(self.session2.id),
            'supervised': True
        })

        self.assertEqual(response.status_code, 201)

    def test_supervised_check_in_with_is_active_false_but_end_time_future(self):
        """Test supervised check-in with is_active=False but end_time in future allows new check-in."""
        # Create session that is not active but time hasn't passed
        inactive_session = Session.objects.create(
            event=self.event,
            name="Inactive Session",
            start_time=timezone.now() - timedelta(hours=1),
            end_time=timezone.now() + timedelta(hours=1),  # Still going
            is_active=False  # Manually deactivated
        )

        # Create supervised check-in to this session
        CheckInRecord.objects.create(
            child=self.child,
            session=inactive_session,
            check_in_staff=self.user,
            supervised=True
        )

        # Should be able to check into new session since is_active=False
        response = self.client.post('/api/checkins/check_in/', {
            'child': str(self.child.id),
            'session': str(self.session2.id),
            'supervised': True
        })

        self.assertEqual(response.status_code, 201)

    def test_standard_check_in_always_blocks_regardless_of_session_status(self):
        """Test standard (non-supervised) check-in always blocks new check-in."""
        # Create standard check-in to ended session
        CheckInRecord.objects.create(
            child=self.child,
            session=self.session1,
            check_in_staff=self.user,
            supervised=False
        )

        # Should NOT be able to check into new session
        response = self.client.post('/api/checkins/check_in/', {
            'child': str(self.child.id),
            'session': str(self.session2.id)
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn('active check-in to another session', response.data['error'])

    def test_print_queue_shows_supervised_from_active_sessions_only(self):
        """
        Test print queue shows supervised check-ins only from sessions marked as active.
        The is_active flag is the single source of truth - end_time doesn't matter.
        """
        # Create supervised check-in to inactive session (is_active=False)
        ended_checkin = CheckInRecord.objects.create(
            child=self.child,
            session=self.session1,
            check_in_staff=self.user,
            supervised=True,
            label_printed=False
        )

        # Create another child for active session
        child2 = Child.objects.create(
            family=self.family,
            first_name="Active",
            last_name="Child",
            birthdate=timezone.now().date()
        )

        # Create supervised check-in to active session (is_active=True)
        active_checkin = CheckInRecord.objects.create(
            child=child2,
            session=self.session2,
            check_in_staff=self.user,
            supervised=True,
            label_printed=False
        )

        # Get print queue
        response = self.client.get('/api/print-queue/')

        self.assertEqual(response.status_code, 200)
        # Should only show check-in from session with is_active=True
        results = response.data if isinstance(response.data, list) else response.data.get('results', [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], str(active_checkin.id))

    def test_print_queue_excludes_supervised_from_inactive_sessions(self):
        """
        Test print queue excludes supervised check-ins from sessions marked as inactive.
        Only the is_active flag matters, not the end_time.
        """
        # Create supervised check-in to inactive session (is_active=False)
        CheckInRecord.objects.create(
            child=self.child,
            session=self.session1,
            check_in_staff=self.user,
            supervised=True,
            label_printed=False
        )

        # Get print queue
        response = self.client.get('/api/print-queue/')

        self.assertEqual(response.status_code, 200)
        results = response.data if isinstance(response.data, list) else response.data.get('results', [])
        self.assertEqual(len(results), 0)

    def test_print_queue_shows_supervised_past_end_time_if_session_active(self):
        """
        Test print queue shows supervised check-ins even after end_time has passed,
        as long as the session is still marked as active (is_active=True).
        This gives administrators maximum flexibility.
        """
        # Create a session that has ended (end_time in past) but is still active
        past_but_active_session = Session.objects.create(
            event=self.event,
            name="Extended Session",
            start_time=timezone.now() - timedelta(hours=3),
            end_time=timezone.now() - timedelta(minutes=30),  # Ended 30 min ago
            is_active=True  # But still marked as active - admin's choice!
        )

        # Create supervised check-in to this session
        checkin = CheckInRecord.objects.create(
            child=self.child,
            session=past_but_active_session,
            check_in_staff=self.user,
            supervised=True,
            label_printed=False
        )

        # Get print queue
        response = self.client.get('/api/print-queue/')

        self.assertEqual(response.status_code, 200)
        results = response.data if isinstance(response.data, list) else response.data.get('results', [])
        # Should show the check-in because is_active=True, regardless of end_time
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], str(checkin.id))

    def test_print_queue_shows_standard_check_ins_regardless_of_session(self):
        """Test print queue shows standard check-ins regardless of session status."""
        # Create standard check-in to ended session
        ended_checkin = CheckInRecord.objects.create(
            child=self.child,
            session=self.session1,
            check_in_staff=self.user,
            supervised=False,
            label_printed=False
        )

        # Get print queue
        response = self.client.get('/api/print-queue/')

        self.assertEqual(response.status_code, 200)
        # Should show standard check-in even though session ended
        results = response.data if isinstance(response.data, list) else response.data.get('results', [])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], str(ended_checkin.id))

    def test_checkout_works_for_supervised_records(self):
        """Test that checkout functionality works for supervised records."""
        # Create supervised check-in
        checkin = CheckInRecord.objects.create(
            child=self.child,
            session=self.session2,
            check_in_staff=self.user,
            supervised=True
        )

        # Checkout
        response = self.client.post(f'/api/checkins/{checkin.id}/check_out/', {
            'picked_up_by': 'Parent Name'
        })

        self.assertEqual(response.status_code, 200)

        # Verify checkout
        checkin.refresh_from_db()
        self.assertIsNotNone(checkin.check_out_time)
        self.assertEqual(checkin.picked_up_by, 'Parent Name')

    def test_undo_works_for_supervised_records(self):
        """Test that undo functionality works for supervised records within time window."""
        # Create supervised check-in
        checkin = CheckInRecord.objects.create(
            child=self.child,
            session=self.session2,
            check_in_staff=self.user,
            supervised=True
        )

        # Undo check-in
        response = self.client.post(f'/api/checkins/{checkin.id}/undo/')

        self.assertEqual(response.status_code, 200)
        # Verify record was deleted
        self.assertEqual(CheckInRecord.objects.filter(id=checkin.id).count(), 0)

    def test_audit_log_includes_supervised_field(self):
        """Test that audit log includes supervised field in details."""
        response = self.client.post('/api/checkins/check_in/', {
            'child': str(self.child.id),
            'session': str(self.session2.id),
            'supervised': True
        })

        self.assertEqual(response.status_code, 201)

        # Check audit log
        audit_log = AuditLog.objects.filter(action='check_in').first()
        self.assertIsNotNone(audit_log)
        self.assertTrue(audit_log.details['supervised'])

    def test_same_session_check_in_blocked_for_supervised(self):
        """Test that supervised child cannot be checked into same session twice."""
        # Create supervised check-in
        CheckInRecord.objects.create(
            child=self.child,
            session=self.session2,
            check_in_staff=self.user,
            supervised=True
        )

        # Try to check into same session again
        response = self.client.post('/api/checkins/check_in/', {
            'child': str(self.child.id),
            'session': str(self.session2.id),
            'supervised': True
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn('already checked in to this session', response.data['error'])
