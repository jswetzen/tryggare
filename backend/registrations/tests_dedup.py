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

    @patch("registrations.views.send_verification_email")
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

    @patch("registrations.views.send_verification_email")
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

    @patch("registrations.views.send_verification_email")
    def test_second_submission_within_cooldown_is_throttled(self, mock_send):
        self.client.post(self.url, self._payload(), format="json")
        mock_send.reset_mock()

        response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Registration.objects.count(), 1)
        mock_send.assert_not_called()

    @patch("registrations.views.send_verification_email")
    def test_expired_pending_registration_gets_a_fresh_row_not_resent(self, mock_send):
        self.client.post(self.url, self._payload(), format="json")
        old = Registration.objects.get()
        Registration.objects.filter(pk=old.pk).update(
            expires_at=timezone.now() - timedelta(hours=1)
        )

        response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Registration.objects.count(), 2)

    @patch("registrations.views.send_verification_email")
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

    @patch("registrations.views.send_verification_email")
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
