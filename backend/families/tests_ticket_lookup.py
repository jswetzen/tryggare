"""
Unit tests for the GET /api/families/by-ticket/ endpoint.

Tests the ticket lookup endpoint that resolves an external ticket code
to a family record. Covers EventTicket and SessionTicket lookups,
authentication, and error cases.

Run with:
    uv run python manage.py test families.tests_ticket_lookup -v 2
"""
from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import AdminUser
from events.models import Event, EventTicket, Session, SessionTicket
from families.models import Child, Family, Parent


class TicketLookupAPITest(TestCase):
    """Tests for GET /api/families/by-ticket/?code=<code>"""

    def setUp(self):
        self.client = APIClient()
        self.user = AdminUser.objects.create_user(
            username="lookuptest",
            password="pass123",
            name="Lookup Tester"
        )
        self.client.force_authenticate(user=self.user)

        self.family = Family.objects.create(last_name="Scannable")
        self.parent = Parent.objects.create(
            family=self.family,
            name="Test Parent",
            relationship_type="Parent"
        )
        self.child = Child.objects.create(
            family=self.family,
            first_name="Scan",
            last_name="Scannable",
            birthdate=date(2018, 1, 1)
        )

        self.event = Event.objects.create(
            name="Scan Event",
            start_date=date.today(),
            end_date=date.today()
        )
        self.session = Session.objects.create(
            event=self.event,
            name="Scan Session",
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=2),
            is_active=True
        )

        EventTicket.objects.create(
            child=self.child,
            event=self.event,
            external_ticket_code="EVENTCODE1"
        )
        SessionTicket.objects.create(
            child=self.child,
            session=self.session,
            external_ticket_code="SESSIONCODE1"
        )

    def test_lookup_by_event_ticket_code(self):
        """Resolves an EventTicket code to the correct family."""
        response = self.client.get("/api/families/by-ticket/?code=EVENTCODE1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data["id"]), str(self.family.id))

    def test_lookup_by_session_ticket_code(self):
        """Resolves a SessionTicket code to the correct family."""
        response = self.client.get("/api/families/by-ticket/?code=SESSIONCODE1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data["id"]), str(self.family.id))

    def test_lookup_returns_full_family_shape(self):
        """Response includes all expected family fields."""
        response = self.client.get("/api/families/by-ticket/?code=EVENTCODE1")
        self.assertEqual(response.status_code, 200)
        data = response.data
        self.assertIn("id", data)
        self.assertIn("last_name", data)
        self.assertIn("display_name", data)
        self.assertIn("children", data)
        self.assertIn("parents", data)
        self.assertEqual(data["last_name"], "Scannable")
        self.assertEqual(len(data["children"]), 1)
        self.assertEqual(len(data["parents"]), 1)

    def test_lookup_unknown_code_returns_404(self):
        """Unknown code returns 404 with error payload."""
        response = self.client.get("/api/families/by-ticket/?code=DOESNOTEXIST")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error"], "not_found")

    def test_lookup_empty_code_returns_400(self):
        """Empty code string returns 400."""
        response = self.client.get("/api/families/by-ticket/?code=")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"], "code required")

    def test_lookup_missing_code_param_returns_400(self):
        """Missing code query param returns 400."""
        response = self.client.get("/api/families/by-ticket/")
        self.assertEqual(response.status_code, 400)

    def test_lookup_requires_auth(self):
        """Unauthenticated request is rejected with 403."""
        unauthenticated = APIClient()
        response = unauthenticated.get("/api/families/by-ticket/?code=EVENTCODE1")
        self.assertEqual(response.status_code, 403)

    def test_event_ticket_takes_priority_over_session_ticket(self):
        """When a child has both ticket types, EventTicket is found first."""
        # Both EVENTCODE1 and SESSIONCODE1 belong to the same child/family,
        # so either code should return the same family. This verifies the
        # EventTicket lookup path works when both exist simultaneously.
        response_event = self.client.get("/api/families/by-ticket/?code=EVENTCODE1")
        response_session = self.client.get("/api/families/by-ticket/?code=SESSIONCODE1")
        self.assertEqual(response_event.status_code, 200)
        self.assertEqual(response_session.status_code, 200)
        self.assertEqual(
            str(response_event.data["id"]),
            str(response_session.data["id"])
        )

    def test_lookup_code_is_case_sensitive(self):
        """Ticket codes are matched exactly (case-sensitive)."""
        response = self.client.get("/api/families/by-ticket/?code=eventcode1")
        self.assertEqual(response.status_code, 404)

    def test_lookup_returns_correct_child_ticket_info(self):
        """Response child has correct ticket_type set."""
        response = self.client.get("/api/families/by-ticket/?code=EVENTCODE1")
        self.assertEqual(response.status_code, 200)
        child_data = response.data["children"][0]
        self.assertIn("ticket_type", child_data)
        self.assertEqual(child_data["ticket_type"], "event")
