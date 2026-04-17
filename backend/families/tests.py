from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from events.models import Event, EventTicket, Session, SessionTicket
from families.models import Child, Family, Parent

User = get_user_model()


class ChildModelTests(TestCase):
    """Test cases for Child model convenience methods"""

    def setUp(self):
        """Set up test data"""
        self.family = Family.objects.create(last_name="Smith")
        self.child = Child.objects.create(
            first_name="John",
            last_name="Smith",
            birthdate=date(2018, 5, 15),
            family=self.family,
        )
        self.event = Event.objects.create(
            name="Conference 2025",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 5),
        )
        self.session = Session.objects.create(
            name="Morning Session",
            event=self.event,
            start_time="2025-06-01T09:00:00Z",
            end_time="2025-06-01T12:00:00Z",
        )

    def test_has_ticket_with_no_tickets(self):
        """Test has_ticket returns False when child has no tickets"""
        self.assertFalse(self.child.has_ticket)

    def test_has_ticket_with_event_ticket(self):
        """Test has_ticket returns True when child has an event ticket"""
        EventTicket.objects.create(child=self.child, event=self.event)
        self.assertTrue(self.child.has_ticket)

    def test_has_ticket_with_session_ticket(self):
        """Test has_ticket returns True when child has a session ticket"""
        SessionTicket.objects.create(child=self.child, session=self.session)
        self.assertTrue(self.child.has_ticket)

    def test_get_ticket_type_none(self):
        """Test get_ticket_type returns 'none' when child has no tickets"""
        self.assertEqual(self.child.get_ticket_type(), 'none')

    def test_get_ticket_type_event(self):
        """Test get_ticket_type returns 'event' when child has an event ticket"""
        EventTicket.objects.create(child=self.child, event=self.event)
        self.assertEqual(self.child.get_ticket_type(), 'event')

    def test_get_ticket_type_session(self):
        """Test get_ticket_type returns 'session' when child has only session tickets"""
        SessionTicket.objects.create(child=self.child, session=self.session)
        self.assertEqual(self.child.get_ticket_type(), 'session')

    def test_get_ticket_type_event_precedence(self):
        """Test that event tickets take precedence over session tickets"""
        EventTicket.objects.create(child=self.child, event=self.event)
        SessionTicket.objects.create(child=self.child, session=self.session)
        self.assertEqual(self.child.get_ticket_type(), 'event')

    def test_get_ticket_details_no_tickets(self):
        """Test get_ticket_details with no tickets"""
        details = self.child.get_ticket_details()
        self.assertEqual(details['ticket_type'], 'none')
        self.assertEqual(details['event_tickets'], [])
        self.assertEqual(details['session_tickets'], [])

    def test_get_ticket_details_with_event_ticket(self):
        """Test get_ticket_details with an event ticket"""
        event_ticket = EventTicket.objects.create(child=self.child, event=self.event)
        details = self.child.get_ticket_details()

        self.assertEqual(details['ticket_type'], 'event')
        self.assertEqual(len(details['event_tickets']), 1)
        self.assertEqual(details['event_tickets'][0]['event'], str(self.event.id))
        self.assertEqual(details['event_tickets'][0]['event_name'], 'Conference 2025')
        self.assertEqual(details['event_tickets'][0]['id'], str(event_ticket.id))
        self.assertEqual(details['session_tickets'], [])

    def test_get_ticket_details_with_session_ticket(self):
        """Test get_ticket_details with a session ticket"""
        session_ticket = SessionTicket.objects.create(child=self.child, session=self.session)
        details = self.child.get_ticket_details()

        self.assertEqual(details['ticket_type'], 'session')
        self.assertEqual(len(details['session_tickets']), 1)
        self.assertEqual(details['session_tickets'][0]['session'], str(self.session.id))
        self.assertEqual(details['session_tickets'][0]['session_name'], 'Morning Session')
        self.assertEqual(details['session_tickets'][0]['id'], str(session_ticket.id))
        self.assertEqual(details['event_tickets'], [])

    def test_get_ticket_details_with_multiple_tickets(self):
        """Test get_ticket_details with multiple tickets of different types"""
        event_ticket = EventTicket.objects.create(child=self.child, event=self.event)
        session_ticket = SessionTicket.objects.create(child=self.child, session=self.session)
        details = self.child.get_ticket_details()

        self.assertEqual(details['ticket_type'], 'event')
        self.assertEqual(len(details['event_tickets']), 1)
        self.assertEqual(len(details['session_tickets']), 1)


class FamilyModelTests(TestCase):
    """Test cases for Family model"""

    def test_display_name_with_last_name(self):
        """Test display_name property with a last name"""
        family = Family.objects.create(last_name="Garcia")
        self.assertEqual(family.display_name, "Garcia Family")

    def test_display_name_without_last_name_no_parents(self):
        """Test display_name property without last name or parents"""
        family = Family.objects.create(last_name="")
        self.assertIn("Family", family.display_name)
        self.assertIn(str(family.id), family.display_name)

    def test_display_name_without_last_name_with_parent(self):
        """Test display_name property without last name but with parent"""
        family = Family.objects.create(last_name="")
        Parent.objects.create(
            name="Jane Doe",
            relationship_type="Mother",
            family=family,
        )
        self.assertIn("Jane Doe", family.display_name)


class ChildSerializerTests(TestCase):
    """Test cases for ChildSerializer with ticket information"""

    def setUp(self):
        """Set up test data and authenticated client"""
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.family = Family.objects.create(last_name="Johnson")
        self.child = Child.objects.create(
            first_name="Emily",
            last_name="Johnson",
            birthdate=date(2019, 3, 20),
            family=self.family,
        )
        self.event = Event.objects.create(
            name="Summer Camp 2025",
            start_date=date(2025, 7, 1),
            end_date=date(2025, 7, 10),
        )
        self.session = Session.objects.create(
            name="Afternoon Session",
            event=self.event,
            start_time="2025-07-01T13:00:00Z",
            end_time="2025-07-01T17:00:00Z",
        )

    def test_child_serializer_no_tickets(self):
        """Test ChildSerializer with a child that has no tickets"""
        response = self.client.get(f'/api/children/{self.child.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['ticket_type'], 'none')
        self.assertEqual(response.data['ticket_details']['ticket_type'], 'none')
        self.assertEqual(response.data['ticket_details']['event_tickets'], [])
        self.assertEqual(response.data['ticket_details']['session_tickets'], [])

    def test_child_serializer_with_event_ticket(self):
        """Test ChildSerializer with a child that has an event ticket"""
        EventTicket.objects.create(child=self.child, event=self.event)
        response = self.client.get(f'/api/children/{self.child.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['ticket_type'], 'event')
        self.assertEqual(len(response.data['ticket_details']['event_tickets']), 1)
        self.assertEqual(
            response.data['ticket_details']['event_tickets'][0]['event'],
            str(self.event.id)
        )
        self.assertEqual(
            response.data['ticket_details']['event_tickets'][0]['event_name'],
            'Summer Camp 2025'
        )

    def test_child_serializer_with_session_ticket(self):
        """Test ChildSerializer with a child that has a session ticket"""
        SessionTicket.objects.create(child=self.child, session=self.session)
        response = self.client.get(f'/api/children/{self.child.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['ticket_type'], 'session')
        self.assertEqual(len(response.data['ticket_details']['session_tickets']), 1)
        self.assertEqual(
            response.data['ticket_details']['session_tickets'][0]['session'],
            str(self.session.id)
        )
        self.assertEqual(
            response.data['ticket_details']['session_tickets'][0]['session_name'],
            'Afternoon Session'
        )

    def test_child_serializer_ticket_fields_readonly(self):
        """Test that ticket_type and ticket_details are read-only"""
        # Attempt to update ticket_type and ticket_details
        response = self.client.patch(
            f'/api/children/{self.child.id}/',
            {
                'ticket_type': 'event',
                'ticket_details': {'fake': 'data'},
                'first_name': 'Updated',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        # The name should be updated
        self.assertEqual(response.data['first_name'], 'Updated')
        # But ticket_type should still be 'none' (not changed)
        self.assertEqual(response.data['ticket_type'], 'none')


class FamilySerializerTests(TestCase):
    """Test cases for FamilySerializer with display_name"""

    def setUp(self):
        """Set up test data and authenticated client"""
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.family = Family.objects.create(last_name="Martinez")
        Parent.objects.create(
            name="Carlos Martinez",
            relationship_type="Father",
            phone="555-1234",
            family=self.family,
        )
        Child.objects.create(
            first_name="Sofia",
            last_name="Martinez",
            birthdate=date(2020, 1, 10),
            family=self.family,
        )

    def test_family_serializer_display_name(self):
        """Test that FamilySerializer includes display_name"""
        response = self.client.get(f'/api/families/{self.family.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['display_name'], 'Martinez Family')

    def test_family_serializer_display_name_readonly(self):
        """Test that display_name is read-only"""
        response = self.client.patch(
            f'/api/families/{self.family.id}/',
            {
                'display_name': 'Fake Family',
                'last_name': 'Updated',
            },
        )

        self.assertEqual(response.status_code, 200)
        # last_name should be updated
        self.assertEqual(response.data['last_name'], 'Updated')
        # display_name should reflect the new last_name
        self.assertEqual(response.data['display_name'], 'Updated Family')

    def test_family_list_includes_display_name(self):
        """Test that family list endpoint includes display_name"""
        response = self.client.get('/api/families/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertIn('display_name', response.data[0])
        self.assertEqual(response.data[0]['display_name'], 'Martinez Family')


class TicketIntegrationTests(TestCase):
    """Integration tests for ticket information in family/child endpoints"""

    def setUp(self):
        """Set up test data with tickets"""
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.family = Family.objects.create(last_name="Wilson")
        self.child1 = Child.objects.create(
            first_name="Alice",
            last_name="Wilson",
            birthdate=date(2017, 8, 5),
            family=self.family,
        )
        self.child2 = Child.objects.create(
            first_name="Bob",
            last_name="Wilson",
            birthdate=date(2019, 11, 12),
            family=self.family,
        )

        self.event = Event.objects.create(
            name="Winter Conference",
            start_date=date(2025, 12, 1),
            end_date=date(2025, 12, 5),
        )
        self.session = Session.objects.create(
            name="Workshop A",
            event=self.event,
            start_time="2025-12-01T10:00:00Z",
            end_time="2025-12-01T12:00:00Z",
        )

        # Give child1 an event ticket, child2 a session ticket
        EventTicket.objects.create(child=self.child1, event=self.event)
        SessionTicket.objects.create(child=self.child2, session=self.session)

    def test_family_detail_includes_children_with_tickets(self):
        """Test that family detail endpoint includes children with ticket info"""
        response = self.client.get(f'/api/families/{self.family.id}/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['children']), 2)

        # Find Alice and Bob in the response
        alice = next(c for c in response.data['children'] if c['first_name'] == 'Alice')
        bob = next(c for c in response.data['children'] if c['first_name'] == 'Bob')

        # Check Alice has event ticket
        self.assertEqual(alice['ticket_type'], 'event')
        self.assertEqual(len(alice['ticket_details']['event_tickets']), 1)

        # Check Bob has session ticket
        self.assertEqual(bob['ticket_type'], 'session')
        self.assertEqual(len(bob['ticket_details']['session_tickets']), 1)

    def test_child_list_query_performance(self):
        """Test that child list doesn't have N+1 query problems"""
        # Create more children with tickets
        for i in range(10):
            child = Child.objects.create(
                first_name=f"Child{i}",
                last_name="Wilson",
                birthdate=date(2018, 1, 1),
                family=self.family,
            )
            if i % 2 == 0:
                EventTicket.objects.create(child=child, event=self.event)
            else:
                SessionTicket.objects.create(child=child, session=self.session)

        # The query should be efficient due to prefetch_related
        # Expecting: 1 child query + 1 event ticket prefetch + 1 session ticket prefetch + 1 check-in record prefetch
        with self.assertNumQueries(4):
            response = self.client.get('/api/children/')
            self.assertEqual(response.status_code, 200)
            # Ensure all children are returned with ticket info and check-in status
            for child_data in response.data:
                self.assertIn('ticket_type', child_data)
                self.assertIn('ticket_details', child_data)
                self.assertIn('is_checked_in', child_data)
                self.assertIn('active_checkin_id', child_data)
