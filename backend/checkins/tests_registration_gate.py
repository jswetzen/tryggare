"""
Tests for the self-serve-registration check-in eligibility gate
(checkins/eligibility.py::registration_checkin_gate_error and its wiring
into CheckInRecordViewSet.check_in).
"""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import AdminUser
from events.models import Event, EventTicket, Session
from families.models import Child, Family
from registrations.models import Registration
from registrations.tokens import generate_verification_token, hash_token

from .eligibility import registration_checkin_gate_error


def _make_event_and_session():
    today = timezone.now().date()
    event = Event.objects.create(name="Camp", start_date=today, end_date=today)
    session = Session.objects.create(
        event=event,
        name="Session 1",
        start_time=timezone.now(),
        end_time=timezone.now() + timedelta(hours=2),
        is_active=True,
    )
    return event, session


class RegistrationCheckinGateUnitTests(TestCase):
    def setUp(self):
        self.event, self.session = _make_event_and_session()
        self.family = Family.objects.create(last_name="Test")
        self.child = Child.objects.create(first_name="Kim", family=self.family)

    def _make_registration(self, status):
        return Registration.objects.create(
            event=self.event,
            family=self.family,
            contact_email="guardian@example.com",
            verification_token_hash=hash_token(generate_verification_token()),
            status=status,
        )

    def test_no_ticket_at_all_is_unaffected(self):
        """Staff-added children with no ticket at all keep working exactly
        as before self-serve registration existed."""
        self.assertIsNone(registration_checkin_gate_error(self.child, self.session))

    def test_staff_created_ticket_with_no_registration_is_unaffected(self):
        EventTicket.objects.create(attendee=self.child, event=self.event)
        self.assertIsNone(registration_checkin_gate_error(self.child, self.session))

    def test_confirmed_registration_ticket_passes(self):
        registration = self._make_registration(Registration.Status.CONFIRMED)
        EventTicket.objects.create(
            attendee=self.child, event=self.event, registration=registration
        )
        self.assertIsNone(registration_checkin_gate_error(self.child, self.session))

    def test_pending_verification_registration_ticket_blocks(self):
        registration = self._make_registration(Registration.Status.PENDING_VERIFICATION)
        EventTicket.objects.create(
            attendee=self.child, event=self.event, registration=registration
        )
        error = registration_checkin_gate_error(self.child, self.session)
        self.assertIsNotNone(error)

    def test_pending_review_registration_ticket_blocks(self):
        registration = self._make_registration(Registration.Status.PENDING_REVIEW)
        EventTicket.objects.create(
            attendee=self.child, event=self.event, registration=registration
        )
        error = registration_checkin_gate_error(self.child, self.session)
        self.assertIsNotNone(error)

    def test_pending_payment_registration_ticket_blocks(self):
        """Documents that eligibility.py needs zero changes for Phase 2 —
        pending_payment is already excluded by the existing != CONFIRMED
        check, same as any other non-confirmed status."""
        registration = self._make_registration(Registration.Status.PENDING_PAYMENT)
        EventTicket.objects.create(
            attendee=self.child, event=self.event, registration=registration
        )
        error = registration_checkin_gate_error(self.child, self.session)
        self.assertIsNotNone(error)


class RegistrationCheckinGateApiTests(TestCase):
    """End-to-end through the real check_in endpoint."""

    def setUp(self):
        self.client = APIClient()
        self.staff = AdminUser.objects.create_user(
            username="staff", password="testpass123", name="Staff"
        )
        self.client.force_authenticate(user=self.staff)
        self.event, self.session = _make_event_and_session()
        self.family = Family.objects.create(last_name="Test")
        self.child = Child.objects.create(first_name="Kim", family=self.family)

    def test_check_in_blocked_for_unconfirmed_registration(self):
        registration = Registration.objects.create(
            event=self.event,
            family=self.family,
            contact_email="guardian@example.com",
            verification_token_hash=hash_token(generate_verification_token()),
        )
        EventTicket.objects.create(
            attendee=self.child, event=self.event, registration=registration
        )

        response = self.client.post(
            "/api/checkins/check_in/",
            {"child": str(self.child.id), "session": str(self.session.id)},
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)

    def test_check_in_allowed_once_confirmed(self):
        registration = Registration.objects.create(
            event=self.event,
            family=self.family,
            contact_email="guardian@example.com",
            verification_token_hash=hash_token(generate_verification_token()),
            status=Registration.Status.CONFIRMED,
        )
        EventTicket.objects.create(
            attendee=self.child, event=self.event, registration=registration
        )

        response = self.client.post(
            "/api/checkins/check_in/",
            {"child": str(self.child.id), "session": str(self.session.id)},
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)

    def test_check_in_still_works_with_no_ticket_at_all(self):
        """Staff-added children (the vast majority today) are unaffected."""
        response = self.client.post(
            "/api/checkins/check_in/",
            {"child": str(self.child.id), "session": str(self.session.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)


class RegistrationCheckinGateGenericEndpointTests(TestCase):
    """The gate must also hold on a plain POST to the generic
    CheckInRecordViewSet create endpoint (config/urls.py's "checkins"
    router), not just the custom check_in action — mirrors
    parent_checkin_gate_error's equivalent coverage."""

    def setUp(self):
        self.client = APIClient()
        self.staff = AdminUser.objects.create_user(
            username="staff2", password="testpass123", name="Staff"
        )
        self.client.force_authenticate(user=self.staff)
        self.event, self.session = _make_event_and_session()
        self.family = Family.objects.create(last_name="Test")
        self.child = Child.objects.create(first_name="Kim", family=self.family)

    def test_generic_endpoint_blocked_for_unconfirmed_registration(self):
        registration = Registration.objects.create(
            event=self.event,
            family=self.family,
            contact_email="guardian@example.com",
            verification_token_hash=hash_token(generate_verification_token()),
        )
        EventTicket.objects.create(
            attendee=self.child, event=self.event, registration=registration
        )

        response = self.client.post(
            "/api/checkins/",
            {
                "child": str(self.child.id),
                "session": str(self.session.id),
                "check_in_staff": str(self.staff.id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("not yet confirmed", str(response.data))

    def test_generic_endpoint_allowed_once_confirmed(self):
        registration = Registration.objects.create(
            event=self.event,
            family=self.family,
            contact_email="guardian@example.com",
            verification_token_hash=hash_token(generate_verification_token()),
            status=Registration.Status.CONFIRMED,
        )
        EventTicket.objects.create(
            attendee=self.child, event=self.event, registration=registration
        )

        response = self.client.post(
            "/api/checkins/",
            {
                "child": str(self.child.id),
                "session": str(self.session.id),
                "check_in_staff": str(self.staff.id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
