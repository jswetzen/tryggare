"""
Dedup + resend behavior: a second submission for a still-pending
(event, contact_email) pair resends instead of creating a duplicate row,
subject to a resend cooldown.
"""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import Event

from .models import Registration


def _make_event(name="Summer Camp"):
    today = timezone.now().date()
    return Event.objects.create(
        name=name,
        start_date=today,
        end_date=today,
        registration_opens_at=timezone.now() - timedelta(days=1),
    )


class RegistrationDedupTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.event = _make_event()
        self.url = "/api/registrations/"

    def _payload(self, **overrides):
        payload = {
            "event": str(self.event.id),
            "contact_email": "guardian@example.com",
            "parents": [
                {
                    "first_name": "Anna",
                    "relationship_type": "Mother",
                    "email": "guardian@example.com",
                }
            ],
            "children": [],
        }
        payload.update(overrides)
        return payload

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_second_submission_past_cooldown_resends_not_duplicates(self, mock_send):
        self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(Registration.objects.count(), 1)
        registration = Registration.objects.get()
        # Simulate the cooldown having elapsed.
        Registration.objects.filter(pk=registration.pk).update(
            verification_sent_at=timezone.now() - timedelta(minutes=11)
        )

        response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Registration.objects.count(), 1)
        self.assertEqual(mock_send.call_count, 2)
        registration.refresh_from_db()
        first_token = mock_send.call_args_list[0][0][1]
        second_token = mock_send.call_args_list[1][0][1]
        self.assertNotEqual(first_token, second_token)

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_resend_never_extends_expiry_past_original_ttl(self, mock_send):
        """A1: a resend must not refresh expires_at — otherwise an attacker
        who put a victim's address in contact_email could keep the row (and
        its resend-email volume) alive indefinitely."""
        self.client.post(self.url, self._payload(), format="json")
        registration = Registration.objects.get()
        original_expires_at = registration.expires_at
        Registration.objects.filter(pk=registration.pk).update(
            verification_sent_at=timezone.now() - timedelta(minutes=11)
        )

        response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, 201, response.data)
        registration.refresh_from_db()
        self.assertEqual(registration.expires_at, original_expires_at)

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_second_submission_within_cooldown_is_throttled(self, mock_send):
        self.client.post(self.url, self._payload(), format="json")
        mock_send.reset_mock()

        response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Registration.objects.count(), 1)
        mock_send.assert_not_called()

    # ------------------------------------------------------------------
    # "registration_already_pending" (registration dev-cycle round 4,
    # increment 6, 2026-09-29): a resubmit that hits this dedup used to come
    # back looking exactly like a fresh success (2xx, no way to tell it
    # apart) while silently discarding whatever the guardian just changed —
    # e.g. a forgotten child added via "Edit and resend" (2026-09-28
    # incident, knowitall 6d4f0964). These tests cover the new `code` field
    # the frontend now branches on (+page.svelte::submitPayload). The
    # status codes are deliberately unchanged (200 throttled / 201 resent —
    # see the inline comment on this branch in views.py for why a 4xx would
    # have broken the confirmation screen's own explicit "resend" button,
    # which also lands on this exact branch and has no code-check at all).
    # ------------------------------------------------------------------

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_pending_resubmit_within_cooldown_carries_the_code(self, mock_send):
        self.client.post(self.url, self._payload(), format="json")
        mock_send.reset_mock()

        response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data.get("code"), "registration_already_pending")
        # No new email attempted on the throttled branch — must not read as
        # "we just sent you a fresh one" on the frontend (see
        # pendingDuplicate's own comment in +page.svelte for how it reads
        # this field).
        self.assertNotIn("email_sent", response.data)

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_pending_resubmit_past_cooldown_also_carries_the_code(self, mock_send):
        self.client.post(self.url, self._payload(), format="json")
        registration = Registration.objects.get()
        Registration.objects.filter(pk=registration.pk).update(
            verification_sent_at=timezone.now() - timedelta(minutes=11)
        )

        response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data.get("code"), "registration_already_pending")
        # This branch DID just send a fresh token/email — the frontend must
        # be able to tell the two dedup branches apart on this field.
        self.assertIs(response.data.get("email_sent"), True)

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_different_email_same_event_has_no_pending_code(self, mock_send):
        self.client.post(self.url, self._payload(), format="json")
        response = self.client.post(
            self.url,
            self._payload(
                contact_email="other@example.com",
                parents=[
                    {
                        "first_name": "Bo",
                        "relationship_type": "Father",
                        "email": "other@example.com",
                    }
                ],
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotIn("code", response.data)

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_verified_registration_does_not_trigger_the_dedup_code(self, mock_send):
        """A resubmit for an email whose existing registration is no longer
        PENDING_VERIFICATION (already confirmed) must create a genuine new
        registration, not be routed into the dedup/code path — the dedup
        filter is explicitly scoped to PENDING_VERIFICATION rows only."""
        self.client.post(self.url, self._payload(), format="json")
        registration = Registration.objects.get()
        registration.status = Registration.Status.CONFIRMED
        registration.save(update_fields=["status"])

        response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotIn("code", response.data)
        self.assertEqual(Registration.objects.count(), 2)

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_expired_pending_registration_has_no_pending_code(self, mock_send):
        self.client.post(self.url, self._payload(), format="json")
        old = Registration.objects.get()
        Registration.objects.filter(pk=old.pk).update(
            expires_at=timezone.now() - timedelta(hours=1)
        )

        response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotIn("code", response.data)
        self.assertEqual(Registration.objects.count(), 2)

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_expired_pending_registration_gets_a_fresh_row_not_resent(self, mock_send):
        self.client.post(self.url, self._payload(), format="json")
        old = Registration.objects.get()
        Registration.objects.filter(pk=old.pk).update(
            expires_at=timezone.now() - timedelta(hours=1)
        )

        response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Registration.objects.count(), 2)

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_different_email_same_event_is_independent(self, mock_send):
        self.client.post(self.url, self._payload(), format="json")
        response = self.client.post(
            self.url,
            self._payload(
                contact_email="other@example.com",
                parents=[
                    {
                        "first_name": "Bo",
                        "relationship_type": "Father",
                        "email": "other@example.com",
                    }
                ],
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Registration.objects.count(), 2)

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_resubmission_with_differently_cased_email_resends_not_duplicates(
        self, mock_send
    ):
        """A case-varied resubmission (autofill vs. manual typing) must hit
        the same resend path as an exact match — a case-sensitive filter()
        would create a second Family/Registration with duplicate child data
        and bypass the resend-cooldown abuse control."""
        self.client.post(self.url, self._payload(), format="json")
        self.assertEqual(Registration.objects.count(), 1)
        registration = Registration.objects.get()
        Registration.objects.filter(pk=registration.pk).update(
            verification_sent_at=timezone.now() - timedelta(minutes=11)
        )

        response = self.client.post(
            self.url,
            self._payload(contact_email="Guardian@Example.com"),
            format="json",
        )

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Registration.objects.count(), 1)
        self.assertEqual(mock_send.call_count, 2)

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_same_email_different_event_is_independent(self, mock_send):
        self.client.post(self.url, self._payload(), format="json")
        other_event = _make_event(name="Winter Camp")
        response = self.client.post(
            self.url,
            self._payload(event=str(other_event.id)),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Registration.objects.count(), 2)
