"""TicketType.requires_ticket_type / max_per_required — the family-ticket
pricing loophole fix (a paid "family ticket" type gating how many free
"family member" tickets a registration may carry).

Covers ticket_rules.py::validate_ticket_composition directly (row-level
control over which tickets exist) and the submission-flow wiring in
views.py::_create_registration (end-to-end via the public API).
"""

from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from events.models import AppliesTo, Event, EventTicket, TicketType
from families.models import Family, Parent

from .models import Registration
from .ticket_rules import validate_ticket_composition
from .tokens import generate_verification_token, hash_token


def _make_event(name="Weekend 2026"):
    today = timezone.now().date()
    return Event.objects.create(
        name=name,
        start_date=today,
        end_date=today,
        registration_opens_at=timezone.now() - timezone.timedelta(days=1),
    )


def _make_registration(event):
    family = Family.objects.create(last_name="Test")
    return Registration.objects.create(
        event=event,
        family=family,
        contact_email="guardian@example.com",
        verification_token_hash=hash_token(generate_verification_token()),
    )


class ValidateTicketCompositionTests(TestCase):
    def setUp(self):
        self.event = _make_event()
        self.family_type = TicketType.objects.create(
            event=self.event,
            name="Familjebiljett",
            price=2000,
            applies_to=AppliesTo.EITHER,
        )
        self.member_type = TicketType.objects.create(
            event=self.event,
            name="Familjebiljett - familjemedlem",
            price=0,
            applies_to=AppliesTo.EITHER,
            requires_ticket_type=self.family_type,
            max_per_required=2,
        )

    def _add_ticket(self, registration, ticket_type, *, name="Attendee"):
        family = registration.family
        attendee = Parent.objects.create(
            first_name=name, relationship_type="Mother", family=family
        )
        return EventTicket.objects.create(
            attendee=attendee,
            event=self.event,
            registration=registration,
            ticket_type=ticket_type,
            price_at_registration=ticket_type.price,
        )

    def test_independent_ticket_types_are_unaffected(self):
        registration = _make_registration(self.event)
        plain_type = TicketType.objects.create(
            event=self.event, name="Adult", price=500, applies_to=AppliesTo.EITHER
        )
        self._add_ticket(registration, plain_type)

        validate_ticket_composition(registration)  # must not raise

    def test_dependent_type_without_the_required_type_is_rejected(self):
        registration = _make_registration(self.event)
        self._add_ticket(registration, self.member_type)

        with self.assertRaises(ValidationError):
            validate_ticket_composition(registration)

    def test_dependent_type_within_cap_is_accepted(self):
        registration = _make_registration(self.event)
        self._add_ticket(registration, self.family_type)
        self._add_ticket(registration, self.member_type, name="Member 1")
        self._add_ticket(registration, self.member_type, name="Member 2")

        validate_ticket_composition(registration)  # must not raise

    def test_dependent_type_over_cap_is_rejected(self):
        registration = _make_registration(self.event)
        self._add_ticket(registration, self.family_type)
        for i in range(3):
            self._add_ticket(registration, self.member_type, name=f"Member {i}")

        with self.assertRaises(ValidationError):
            validate_ticket_composition(registration)

    def test_cap_scales_with_number_of_required_tickets(self):
        registration = _make_registration(self.event)
        self._add_ticket(registration, self.family_type, name="Family A")
        self._add_ticket(registration, self.family_type, name="Family B")
        for i in range(4):  # 2 family tickets * max_per_required=2
            self._add_ticket(registration, self.member_type, name=f"Member {i}")

        validate_ticket_composition(registration)  # must not raise

    def test_null_max_per_required_is_unlimited_but_still_requires_one(self):
        unlimited_type = TicketType.objects.create(
            event=self.event,
            name="Unlimited member",
            price=0,
            applies_to=AppliesTo.EITHER,
            requires_ticket_type=self.family_type,
            max_per_required=None,
        )
        registration = _make_registration(self.event)
        self._add_ticket(registration, self.family_type)
        for i in range(10):
            self._add_ticket(registration, unlimited_type, name=f"Member {i}")

        validate_ticket_composition(registration)  # must not raise

        registration_without_family = _make_registration(self.event)
        self._add_ticket(registration_without_family, unlimited_type)

        with self.assertRaises(ValidationError):
            validate_ticket_composition(registration_without_family)

    def test_no_tickets_is_a_no_op(self):
        registration = _make_registration(self.event)

        validate_ticket_composition(registration)  # must not raise


class TicketCompositionSubmissionTests(TestCase):
    """End-to-end through the public submit_registration endpoint — proves
    the validate_ticket_composition wiring in _create_registration, not
    just the isolated function above."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.event = _make_event()
        self.family_type = TicketType.objects.create(
            event=self.event,
            name="Familjebiljett",
            price=2000,
            applies_to=AppliesTo.EITHER,
        )
        self.member_type = TicketType.objects.create(
            event=self.event,
            name="Familjebiljett - familjemedlem",
            price=0,
            applies_to=AppliesTo.EITHER,
            requires_ticket_type=self.family_type,
            max_per_required=1,
        )
        self.url = "/api/registrations/"

    def _payload(self, *, parent_ticket_type, num_children, child_ticket_type):
        return {
            "event": str(self.event.id),
            "contact_email": "guardian@example.com",
            "parents": [
                {
                    "first_name": "Anna",
                    "relationship_type": "Mother",
                    "ticket_type": str(parent_ticket_type.id),
                }
            ],
            "children": [
                {
                    "first_name": f"Child{i}",
                    "last_name": "Andersson",
                    "birthdate": "2018-01-01",
                    "ticket_type": str(child_ticket_type.id),
                }
                for i in range(num_children)
            ],
        }

    def test_family_members_without_a_family_ticket_are_rejected(self):
        payload = self._payload(
            parent_ticket_type=self.member_type,
            num_children=0,
            child_ticket_type=self.member_type,
        )

        with patch("registrations.views.send_verification_email", return_value=True):
            response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Registration.objects.exists())

    def test_family_members_within_cap_are_accepted(self):
        payload = self._payload(
            parent_ticket_type=self.family_type,
            num_children=1,
            child_ticket_type=self.member_type,
        )

        with patch("registrations.views.send_verification_email", return_value=True):
            response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 201, response.data)

    def test_family_members_over_cap_are_rejected(self):
        payload = self._payload(
            parent_ticket_type=self.family_type,
            num_children=2,  # cap is max_per_required=1 per family ticket
            child_ticket_type=self.member_type,
        )

        with patch("registrations.views.send_verification_email", return_value=True):
            response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Registration.objects.exists())
