"""
Tests for event ticket models and API endpoints.
"""
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
            end_time=timezone.now() + timezone.timedelta(hours=2),
            is_active=True
        )

    def test_create_event_ticket(self):
        """Test creating an event ticket."""
        ticket = EventTicket.objects.create(
            child=self.child,
            event=self.event
        )
        self.assertEqual(ticket.child, self.child)
        self.assertEqual(ticket.event, self.event)
        self.assertIn(str(self.child), str(ticket))
        self.assertIn(str(self.event), str(ticket))

    def test_create_session_ticket(self):
        """Test creating a session ticket."""
        ticket = SessionTicket.objects.create(
            child=self.child,
            session=self.session
        )
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
        session_ticket = SessionTicket.objects.create(child=self.child, session=self.session)
        
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
            end_time=timezone.now() + timezone.timedelta(hours=2)
        )

    def test_list_event_tickets(self):
        """Test listing event tickets."""
        EventTicket.objects.create(child=self.child, event=self.event)
        
        response = self.client.get('/api/event-tickets/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['ticket_type'], 'EVENT_PASS')

    def test_create_event_ticket(self):
        """Test creating an event ticket via API."""
        data = {
            'child': str(self.child.id),
            'event': str(self.event.id)
        }
        response = self.client.post('/api/event-tickets/', data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(EventTicket.objects.count(), 1)

    def test_list_session_tickets(self):
        """Test listing session tickets."""
        SessionTicket.objects.create(child=self.child, session=self.session)
        
        response = self.client.get('/api/session-tickets/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['ticket_type'], 'SESSION_TICKET')

    def test_create_session_ticket(self):
        """Test creating a session ticket via API."""
        data = {
            'child': str(self.child.id),
            'session': str(self.session.id)
        }
        response = self.client.post('/api/session-tickets/', data)
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
            birthdate=timezone.now().date()
        )

        EventTicket.objects.create(child=self.child, event=self.event)
        EventTicket.objects.create(child=child2, event=self.event)

        response = self.client.get(f'/api/event-tickets/?child={self.child.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1, f"Expected 1 ticket, got {len(response.data)}: {response.data}")
        # The response contains UUID objects, not strings
        self.assertEqual(str(response.data[0]['child']), str(self.child.id))

    def test_unauthenticated_access_denied(self):
        """Test that unauthenticated users cannot access ticket endpoints."""
        self.client.force_authenticate(user=None)
        
        response = self.client.get('/api/event-tickets/')
        self.assertEqual(response.status_code, 403)
        
        response = self.client.get('/api/session-tickets/')
        self.assertEqual(response.status_code, 403)
