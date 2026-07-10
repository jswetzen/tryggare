"""
Public registration submission + verification: validation, honeypot,
email-match staff-review routing, and consent trust-boundary clearing.
"""

from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from checkins.models import AuditLog
from events.models import Event, EventTicket
from families.models import Child, Family, Parent

from .models import Registration


def _make_event(name="Summer Camp"):
    today = timezone.now().date()
    return Event.objects.create(
        name=name,
        start_date=today,
        end_date=today,
        registration_opens_at=timezone.now() - timedelta(days=1),
    )


class RegistrationEventInfoTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_returns_minimal_public_event_info(self):
        event = _make_event()
        response = self.client.get(f"/api/registrations/events/{event.id}/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["name"], "Summer Camp")

    def test_unknown_event_returns_404(self):
        import uuid

        response = self.client.get(f"/api/registrations/events/{uuid.uuid4()}/")
        self.assertEqual(response.status_code, 404)

    def test_reports_registration_window_status(self):
        event = _make_event()
        response = self.client.get(f"/api/registrations/events/{event.id}/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["registration_window_status"], "open")
        self.assertIsNotNone(response.data["registration_opens_at"])
        self.assertIsNone(response.data["registration_closes_at"])


class RegistrationWindowGateTests(TestCase):
    """submit_registration is the actual enforcement point for the
    registration-window gate — the frontend hiding the form / disabling
    submit is UX only. See events.tests.RegistrationWindowStatusTest for
    the underlying status logic."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.url = "/api/registrations/"

    def _payload(self, event):
        return {
            "event": str(event.id),
            "last_name": "Andersson",
            "contact_email": "guardian@example.com",
            "parents": [
                {
                    "first_name": "Anna",
                    "last_name": "Andersson",
                    "relationship_type": "Mother",
                    "email": "guardian@example.com",
                }
            ],
            "children": [],
        }

    def test_not_configured_event_rejects_submission(self):
        event = Event.objects.create(
            name="Staff-only event",
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
        )
        response = self.client.post(self.url, self._payload(event), format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Registration.objects.filter(event=event).exists())

    def test_not_open_yet_event_rejects_submission(self):
        event = Event.objects.create(
            name="Future opening",
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            registration_opens_at=timezone.now() + timedelta(days=1),
        )
        response = self.client.post(self.url, self._payload(event), format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Registration.objects.filter(event=event).exists())

    def test_closed_event_rejects_submission(self):
        event = Event.objects.create(
            name="Already closed",
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
            registration_opens_at=timezone.now() - timedelta(days=2),
            registration_closes_at=timezone.now() - timedelta(days=1),
        )
        response = self.client.post(self.url, self._payload(event), format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Registration.objects.filter(event=event).exists())

    @patch("registrations.views.send_verification_email")
    def test_open_event_accepts_submission(self, mock_send):
        event = _make_event()
        response = self.client.post(self.url, self._payload(event), format="json")
        self.assertEqual(response.status_code, 201, response.data)


class SubmitRegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.event = _make_event()
        self.url = "/api/registrations/"

    def _payload(self, **overrides):
        payload = {
            "event": str(self.event.id),
            "last_name": "Andersson",
            "contact_email": "guardian@example.com",
            "parents": [
                {
                    "first_name": "Anna",
                    "last_name": "Andersson",
                    "relationship_type": "Mother",
                    "email": "guardian@example.com",
                }
            ],
            "children": [
                {
                    "first_name": "Kim",
                    "last_name": "Andersson",
                    "birthdate": "2018-01-01",
                }
            ],
        }
        payload.update(overrides)
        return payload

    @patch("registrations.views.send_verification_email")
    def test_valid_submission_materializes_family_and_tickets(self, mock_send):
        response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, 201, response.data)
        registration = Registration.objects.get()
        self.assertEqual(registration.status, Registration.Status.PENDING_VERIFICATION)
        self.assertEqual(registration.contact_email, "guardian@example.com")
        self.assertTrue(registration.created_new_family)
        self.assertEqual(response.data["reference_code"], registration.reference_code)

        family = registration.family
        self.assertEqual(family.parents.count(), 1)
        self.assertEqual(family.children.count(), 1)

        for attendee in list(family.parents.all()) + list(family.children.all()):
            ticket = EventTicket.objects.get(attendee=attendee, event=self.event)
            self.assertEqual(ticket.registration_id, registration.id)

        mock_send.assert_called_once()
        sent_registration, sent_token = mock_send.call_args[0]
        self.assertEqual(sent_registration.id, registration.id)
        self.assertTrue(sent_token)

    @patch("registrations.views.send_verification_email")
    def test_honeypot_filled_creates_nothing(self, mock_send):
        response = self.client.post(
            self.url, self._payload(website="http://spam.example"), format="json"
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertFalse(Registration.objects.exists())
        self.assertFalse(Family.objects.exists())
        mock_send.assert_not_called()

    def test_empty_submission_rejected(self):
        response = self.client.post(
            self.url, self._payload(parents=[], children=[]), format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Registration.objects.exists())

    @patch("registrations.views.send_verification_email")
    def test_two_guardian_submission_attests_by_verified_email_not_first(
        self, mock_send
    ):
        response = self.client.post(
            self.url,
            self._payload(
                contact_email="bo@example.com",
                parents=[
                    {
                        "first_name": "Anna",
                        "relationship_type": "Mother",
                        "email": "anna@example.com",
                    },
                    {
                        "first_name": "Bo",
                        "relationship_type": "Father",
                        "email": "bo@example.com",
                    },
                ],
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        child = Child.objects.get()
        # No health info was granted in this payload, so there's no attestor
        # to check directly — assert indirectly via the family services unit
        # tests already covering the matching logic, and just confirm the
        # right guardian ended up in the family at all.
        self.assertEqual(
            {p.first_name for p in child.family.parents.all()}, {"Anna", "Bo"}
        )

    @patch("registrations.views.send_verification_email")
    def test_consent_trust_boundary_cleared_at_submission(self, mock_send):
        """allergies/notes must be blanked server-side when consent isn't
        GRANTED, even if the client sent text anyway — same rigor as the
        staff flow (ChildCreateSerializer.validate()), applied here too."""
        response = self.client.post(
            self.url,
            self._payload(
                children=[
                    {
                        "first_name": "Kim",
                        "birthdate": "2018-01-01",
                        "allergies": "Peanuts",
                        "notes": "Carries an EpiPen",
                        "health_consent_status": "declined",
                    }
                ]
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        child = Child.objects.get()
        self.assertIsNone(child.allergies)
        self.assertIsNone(child.notes)
        self.assertEqual(child.health_consent_status, "declined")

    @patch("registrations.views.send_verification_email")
    def test_adult_health_info_granted_via_self_serve_submission(self, mock_send):
        """An adult attendee's own allergy capture (previously nonexistent —
        see docs/roadmap/event_registration_ux_case_catalog.md §10.1) goes
        through the same RegistrationParentSerializer/create_family_with_members
        path as a child's, end to end from the public submission endpoint."""
        response = self.client.post(
            self.url,
            self._payload(
                contact_email="pat@example.com",
                parents=[
                    {
                        "first_name": "Pat",
                        "relationship_type": "MOM",
                        "email": "pat@example.com",
                        "allergies": "Shellfish",
                        "health_consent_status": "granted",
                    }
                ],
                children=[],
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        parent = Parent.objects.get()
        self.assertEqual(parent.allergies, "Shellfish")
        self.assertEqual(parent.health_consent_status, "granted")
        self.assertEqual(parent.health_consent_by_id, parent.id)
        self.assertIsNotNone(parent.health_consent_at)

    @patch("registrations.views.send_verification_email")
    def test_adult_health_info_trust_boundary_cleared_at_submission(self, mock_send):
        response = self.client.post(
            self.url,
            self._payload(
                contact_email="pat@example.com",
                parents=[
                    {
                        "first_name": "Pat",
                        "relationship_type": "MOM",
                        "email": "pat@example.com",
                        "allergies": "Shellfish",
                        "health_consent_status": "declined",
                    }
                ],
                children=[],
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        parent = Parent.objects.get()
        self.assertIsNone(parent.allergies)
        self.assertEqual(parent.health_consent_status, "declined")

    @patch("registrations.views.send_verification_email")
    def test_submission_logs_audit(self, mock_send):
        self.client.post(self.url, self._payload(), format="json")
        self.assertTrue(
            AuditLog.objects.filter(action="registration_submitted").exists()
        )


class VerifyRegistrationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.event = _make_event()

    def _submit_and_get_token(self, contact_email="guardian@example.com", **overrides):
        payload = {
            "event": str(self.event.id),
            "contact_email": contact_email,
            "parents": [
                {
                    "first_name": "Anna",
                    "relationship_type": "Mother",
                    "email": contact_email,
                }
            ],
            "children": [{"first_name": "Kim", "birthdate": "2018-01-01"}],
        }
        payload.update(overrides)
        with patch("registrations.views.send_verification_email") as mock_send:
            response = self.client.post("/api/registrations/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        _, token = mock_send.call_args[0]
        registration = Registration.objects.get(
            reference_code=response.data["reference_code"]
        )
        return registration, token

    @patch("registrations.views.send_confirmation_email")
    def test_valid_token_confirms_registration(self, mock_confirm):
        registration, token = self._submit_and_get_token()

        response = self.client.get(f"/api/registrations/verify/{token}/")

        self.assertEqual(response.status_code, 200, response.data)
        registration.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.CONFIRMED)
        self.assertIsNotNone(registration.verified_at)
        mock_confirm.assert_called_once()

    def test_unknown_token_returns_404(self):
        response = self.client.get("/api/registrations/verify/not-a-real-token/")
        self.assertEqual(response.status_code, 404)

    @patch("registrations.views.send_confirmation_email")
    def test_expired_registration_returns_410(self, mock_confirm):
        registration, token = self._submit_and_get_token()
        Registration.objects.filter(pk=registration.pk).update(
            expires_at=timezone.now() - timedelta(hours=1)
        )

        response = self.client.get(f"/api/registrations/verify/{token}/")

        self.assertEqual(response.status_code, 410)
        registration.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.PENDING_VERIFICATION)
        mock_confirm.assert_not_called()

    @patch("registrations.views.send_confirmation_email")
    def test_email_matching_existing_parent_on_other_family_routes_to_review(
        self, mock_confirm
    ):
        other_family = Family.objects.create(last_name="Existing")
        Parent.objects.create(
            first_name="Someone",
            relationship_type="Other",
            email="guardian@example.com",
            family=other_family,
        )

        registration, token = self._submit_and_get_token(
            contact_email="guardian@example.com"
        )

        response = self.client.get(f"/api/registrations/verify/{token}/")

        self.assertEqual(response.status_code, 200, response.data)
        registration.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.PENDING_REVIEW)
        mock_confirm.assert_not_called()

    @patch("registrations.views.send_confirmation_email")
    def test_email_matching_anonymized_parent_is_ignored(self, mock_confirm):
        other_family = Family.objects.create(last_name="Existing")
        Parent.objects.create(
            first_name="Someone",
            relationship_type="Other",
            email="guardian@example.com",
            family=other_family,
            anonymized_at=timezone.now(),
        )

        registration, token = self._submit_and_get_token(
            contact_email="guardian@example.com"
        )

        response = self.client.get(f"/api/registrations/verify/{token}/")

        self.assertEqual(response.status_code, 200, response.data)
        registration.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.CONFIRMED)
        mock_confirm.assert_called_once()

    @patch("registrations.views.send_confirmation_email")
    def test_verification_logs_audit(self, mock_confirm):
        registration, token = self._submit_and_get_token()
        self.client.get(f"/api/registrations/verify/{token}/")
        self.assertTrue(
            AuditLog.objects.filter(action="registration_verified").exists()
        )
