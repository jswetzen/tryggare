"""
Per-IP submit throttle: exists and is loose by design (bulk on-site
registration from one venue wifi hotspot is a normal workload — see
registrations/views.py::RegistrationSubmitThrottle). Also guards against the
settings-module trap where a settings module redefines REST_FRAMEWORK
wholesale (as config.settings.local does) without carrying the
'registration_submit' scope, which would raise ImproperlyConfigured on the
very first submission.
"""

from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import Event


def _make_event():
    today = timezone.now().date()
    return Event.objects.create(
        name="Camp",
        start_date=today,
        end_date=today,
        registration_opens_at=timezone.now() - timezone.timedelta(days=1),
    )


class RegistrationSubmitThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.event = _make_event()
        self.url = "/api/registrations/"

    def _payload(self, email):
        return {
            "event": str(self.event.id),
            "contact_email": email,
            "parents": [
                {"first_name": "Anna", "relationship_type": "Mother", "email": email}
            ],
            "children": [],
        }

    @patch("registrations.views.send_verification_email")
    # SimpleRateThrottle.THROTTLE_RATES is bound once at import time as a
    # class attribute — override_settings(REST_FRAMEWORK=...) changes
    # django.conf.settings but doesn't retroactively rebind it, so the usual
    # override_settings pattern silently no-ops here. Patching the dict in
    # place (same object api_settings.DEFAULT_THROTTLE_RATES points at) is
    # the correct way to force a rate for a single test.
    @patch.dict(
        "rest_framework.throttling.SimpleRateThrottle.THROTTLE_RATES",
        {"registration_submit": "1/day"},
    )
    def test_throttle_rate_is_enforced_per_ip(self, mock_send):
        first = self.client.post(
            self.url, self._payload("a@example.com"), format="json"
        )
        self.assertEqual(first.status_code, 201, first.data)

        second = self.client.post(
            self.url, self._payload("b@example.com"), format="json"
        )
        self.assertEqual(second.status_code, 429)

    @patch("registrations.views.send_verification_email")
    def test_bulk_submissions_from_one_ip_are_not_blocked_by_default_rate(
        self, mock_send
    ):
        """The default rate must stay loose enough for a youth leader
        registering many families from one shared wifi hotspot."""
        for i in range(10):
            response = self.client.post(
                self.url, self._payload(f"guardian{i}@example.com"), format="json"
            )
            self.assertEqual(response.status_code, 201, response.data)
