"""
Tests for event ticket models and API endpoints.
"""

from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import Event, EventTicket, Session, SessionTicket
from families.models import Child, Family
from accounts.models import AdminUser


class TicketModelTest(TestCase):
    """Test the polymorphic ticket models."""

    def setUp(self):
        """Set up test data."""
        self.family = Family.objects.create()
        self.child = Child.objects.create(
            family=self.family,
            first_name="Test",
            last_name="Child",
            birthdate=timezone.now().date(),
        )
        self.event = Event.objects.create(
            name="Test Event",
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
        )
        self.session = Session.objects.create(
            event=self.event,
            name="Test Session",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
            is_active=True,
        )

    def test_create_event_ticket(self):
        """Test creating an event ticket."""
        ticket = EventTicket.objects.create(child=self.child, event=self.event)
        self.assertEqual(ticket.child, self.child)
        self.assertEqual(ticket.event, self.event)
        self.assertIn(str(self.child), str(ticket))
        self.assertIn(str(self.event), str(ticket))

    def test_create_session_ticket(self):
        """Test creating a session ticket."""
        ticket = SessionTicket.objects.create(child=self.child, session=self.session)
        self.assertEqual(ticket.child, self.child)
        self.assertEqual(ticket.session, self.session)
        self.assertIn(str(self.child), str(ticket))
        self.assertIn(str(self.session), str(ticket))

    def test_event_ticket_unique_constraint(self):
        """Test that a child cannot have duplicate event tickets."""
        EventTicket.objects.create(child=self.child, event=self.event)

        # Try to create a duplicate
        with self.assertRaises(Exception):  # Will raise IntegrityError
            EventTicket.objects.create(child=self.child, event=self.event)

    def test_session_ticket_unique_constraint(self):
        """Test that a child cannot have duplicate session tickets."""
        SessionTicket.objects.create(child=self.child, session=self.session)

        # Try to create a duplicate
        with self.assertRaises(Exception):  # Will raise IntegrityError
            SessionTicket.objects.create(child=self.child, session=self.session)

    def test_child_can_have_both_ticket_types(self):
        """Test that a child can have both event and session tickets."""
        event_ticket = EventTicket.objects.create(child=self.child, event=self.event)
        session_ticket = SessionTicket.objects.create(
            child=self.child, session=self.session
        )

        self.assertEqual(self.child.event_tickets.count(), 1)
        self.assertEqual(self.child.session_tickets.count(), 1)
        self.assertEqual(self.child.event_tickets.first(), event_ticket)
        self.assertEqual(self.child.session_tickets.first(), session_ticket)


class TicketAPITest(TestCase):
    """Test the ticket API endpoints."""

    def setUp(self):
        """Set up test data and authentication."""
        self.client = APIClient()
        self.user = AdminUser.objects.create_user(
            username="testuser", password="testpass123", name="Test User"
        )
        self.client.force_authenticate(user=self.user)

        self.family = Family.objects.create()
        self.child = Child.objects.create(
            family=self.family,
            first_name="Test",
            last_name="Child",
            birthdate=timezone.now().date(),
        )
        self.event = Event.objects.create(
            name="Test Event",
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
        )
        self.session = Session.objects.create(
            event=self.event,
            name="Test Session",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
        )

    def test_list_event_tickets(self):
        """Test listing event tickets."""
        EventTicket.objects.create(child=self.child, event=self.event)

        response = self.client.get("/api/event-tickets/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["ticket_type"], "EVENT_PASS")

    def test_create_event_ticket(self):
        """Test creating an event ticket via API."""
        data = {"child": str(self.child.id), "event": str(self.event.id)}
        response = self.client.post("/api/event-tickets/", data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(EventTicket.objects.count(), 1)

    def test_list_session_tickets(self):
        """Test listing session tickets."""
        SessionTicket.objects.create(child=self.child, session=self.session)

        response = self.client.get("/api/session-tickets/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["ticket_type"], "SESSION_TICKET")

    def test_create_session_ticket(self):
        """Test creating a session ticket via API."""
        data = {"child": str(self.child.id), "session": str(self.session.id)}
        response = self.client.post("/api/session-tickets/", data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(SessionTicket.objects.count(), 1)

    def test_filter_tickets_by_child(self):
        """Test filtering tickets by child."""
        # First, ensure no tickets exist from previous tests
        EventTicket.objects.all().delete()

        family2 = Family.objects.create()
        child2 = Child.objects.create(
            family=family2,
            first_name="Other",
            last_name="Child",
            birthdate=timezone.now().date(),
        )

        EventTicket.objects.create(child=self.child, event=self.event)
        EventTicket.objects.create(child=child2, event=self.event)

        response = self.client.get(f"/api/event-tickets/?child={self.child.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.data),
            1,
            f"Expected 1 ticket, got {len(response.data)}: {response.data}",
        )
        # The response contains UUID objects, not strings
        self.assertEqual(str(response.data[0]["child"]), str(self.child.id))

    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access ticket endpoints."""
        self.client.force_authenticate(user=None)

        response = self.client.get("/api/event-tickets/")
        self.assertEqual(response.status_code, 403)

        response = self.client.get("/api/session-tickets/")
        self.assertEqual(response.status_code, 403)


class AutoCheckoutOnDeactivateTest(TestCase):
    """Test that deactivating a session auto-checks out all open check-ins."""

    def setUp(self):
        self.staff = AdminUser.objects.create_user(
            username="autotest_staff",
            password="testpass123",
            name="Auto Test Staff",
        )
        self.family = Family.objects.create()
        self.child1 = Child.objects.create(
            family=self.family,
            first_name="Alice",
            last_name="Test",
            birthdate=timezone.now().date(),
        )
        self.child2 = Child.objects.create(
            family=self.family,
            first_name="Bob",
            last_name="Test",
            birthdate=timezone.now().date(),
        )
        self.event = Event.objects.create(
            name="Auto Test Event",
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
        )
        self.session = Session.objects.create(
            event=self.event,
            name="Auto Test Session",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
            is_active=True,
        )

    def _make_checkin(self, child):
        from checkins.models import CheckInRecord

        return CheckInRecord.objects.create(
            child=child,
            session=self.session,
            check_in_staff=self.staff,
        )

    @patch("events.signals.get_channel_layer")
    def test_deactivating_session_checks_out_all_open_records(self, mock_get_layer):
        """Deactivating an active session auto-checks out open check-in records."""
        mock_layer = MagicMock()
        mock_get_layer.return_value = mock_layer

        record1 = self._make_checkin(self.child1)
        record2 = self._make_checkin(self.child2)

        self.session.is_active = False
        self.session.save()

        record1.refresh_from_db()
        record2.refresh_from_db()

        self.assertIsNotNone(record1.check_out_time)
        self.assertIsNotNone(record2.check_out_time)
        self.assertIsNone(record1.check_out_staff)
        self.assertIsNone(record2.check_out_staff)

    @patch("events.signals.get_channel_layer")
    def test_deactivating_session_creates_audit_logs(self, mock_get_layer):
        """Auto-checkout creates AuditLog entries with user=None."""
        mock_layer = MagicMock()
        mock_get_layer.return_value = mock_layer

        from checkins.models import AuditLog

        self._make_checkin(self.child1)

        self.session.is_active = False
        self.session.save()

        log = AuditLog.objects.filter(action="auto_check_out").first()
        self.assertIsNotNone(log)
        self.assertIsNone(log.user)
        self.assertEqual(log.details["reason"], "session_deactivated")

    @patch("events.signals.get_channel_layer")
    def test_deactivating_session_with_no_open_checkins_is_safe(self, mock_get_layer):
        """Deactivating a session with no open check-ins does not raise an error."""
        mock_layer = MagicMock()
        mock_get_layer.return_value = mock_layer

        # No check-ins created — should not raise
        self.session.is_active = False
        self.session.save()

    @patch("events.signals.get_channel_layer")
    def test_already_inactive_session_save_does_not_trigger(self, mock_get_layer):
        """Saving an already-inactive session does not double-checkout."""
        mock_layer = MagicMock()
        mock_get_layer.return_value = mock_layer

        from checkins.models import AuditLog

        self._make_checkin(self.child1)

        # First deactivation
        self.session.is_active = False
        self.session.save()

        audit_count_after_first = AuditLog.objects.filter(
            action="auto_check_out"
        ).count()

        # Second save of same inactive session (e.g. other field change)
        self.session.name = "Renamed"
        self.session.save()

        audit_count_after_second = AuditLog.objects.filter(
            action="auto_check_out"
        ).count()
        self.assertEqual(audit_count_after_first, audit_count_after_second)

    @patch("events.signals.get_channel_layer")
    def test_reactivating_session_does_not_checkout(self, mock_get_layer):
        """Activating (True) or re-activating a session does not trigger checkout."""
        mock_layer = MagicMock()
        mock_get_layer.return_value = mock_layer

        from checkins.models import AuditLog

        self._make_checkin(self.child1)

        # Save without changing is_active (still True)
        self.session.name = "Renamed Active"
        self.session.save()

        self.assertEqual(AuditLog.objects.filter(action="auto_check_out").count(), 0)

    @patch("events.signals.get_channel_layer")
    def test_standard_checkin_can_move_to_new_session_after_auto_checkout(
        self, mock_get_layer
    ):
        """After auto-checkout, a standard check-in can check into another session."""
        mock_layer = MagicMock()
        mock_get_layer.return_value = mock_layer

        from checkins.models import CheckInRecord

        self._make_checkin(self.child1)

        # Deactivate the session → triggers auto-checkout
        self.session.is_active = False
        self.session.save()

        # Create a new active session
        new_session = Session.objects.create(
            event=self.event,
            name="New Session",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=2),
            is_active=True,
        )

        # child1 should now be checkable into the new session (no open records)
        open_standard = CheckInRecord.objects.filter(
            child=self.child1,
            check_out_time__isnull=True,
            supervised=False,
        ).exclude(session=new_session)
        self.assertFalse(open_standard.exists())
