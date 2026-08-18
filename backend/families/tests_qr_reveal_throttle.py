"""
Per-IP throttle on the QR safety-info reveal endpoint: tighter than qr_info's
own generic "anon" rate, since revealing allergy/emergency-medical text is a
rarer, more deliberate act than loading the page (see
families/qr_views.py::QRSafetyInfoRevealThrottle). Mirrors
registrations/tests_throttling.py's pattern for forcing a rate onto
SimpleRateThrottle's class-level THROTTLE_RATES dict, since
override_settings(REST_FRAMEWORK=...) doesn't retroactively rebind it.
"""

from datetime import date, timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model

from checkins.models import CheckInRecord
from checkins.qr_utils import allocate_code_for_checkin
from events.models import Event, Session
from families.models import Child, Family

AdminUser = get_user_model()


def _make_checked_in_child():
    staff = AdminUser.objects.create_user(username="throttle_staff", is_staff=True)
    family = Family.objects.create(last_name="ThrottleTest")
    child = Child.objects.create(
        first_name="Ivy",
        last_name="ThrottleTest",
        family=family,
        birthdate=date(2018, 1, 1),
        allergies="Peanuts",
    )
    event = Event.objects.create(
        name="Throttle Conf",
        start_date=timezone.now().date(),
        end_date=timezone.now().date(),
    )
    session = Session.objects.create(
        name="Morning",
        event=event,
        start_time=timezone.now(),
        end_time=timezone.now() + timedelta(hours=2),
    )
    record = CheckInRecord.objects.create(
        attendee=child, session=session, check_in_staff=staff
    )
    qr_code = allocate_code_for_checkin(record)
    return qr_code.code


class QrSafetyInfoRevealThrottleTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.code = _make_checked_in_child()
        self.url = f"/api/qr/{self.code}/reveal-safety-info/"

    @patch.dict(
        "rest_framework.throttling.SimpleRateThrottle.THROTTLE_RATES",
        {"qr_safety_info_reveal": "1/day"},
    )
    def test_throttle_rate_is_enforced_per_ip(self):
        first = self.client.post(self.url)
        self.assertEqual(first.status_code, 200, first.data)

        second = self.client.post(self.url)
        self.assertEqual(second.status_code, 429)


class QrSafetyInfoRevealUserThrottleTests(TestCase):
    """AnonRateThrottle (QrSafetyInfoRevealThrottleTests above) is a no-op
    for authenticated requests — DRF only ever counts anonymous callers
    against it. Every real reveal is made by a logged-in volunteer or
    coordinator, so the per-user throttle (QRSafetyInfoRevealUserThrottle,
    scope "qr_safety_info_reveal_user") is what actually protects this
    endpoint in practice. Assert both directions: a normal burst well
    under the limit is NOT refused, and exceeding the limit IS refused —
    a test that only exercises one side proves nothing about the other.
    """

    def setUp(self):
        cache.clear()
        self.code = _make_checked_in_child()
        self.url = f"/api/qr/{self.code}/reveal-safety-info/"
        self.volunteer = AdminUser.objects.create_user(
            username="throttle_volunteer", password="pw"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.volunteer)

    @patch.dict(
        "rest_framework.throttling.SimpleRateThrottle.THROTTLE_RATES",
        {
            "qr_safety_info_reveal_user": "3/minute",
            "qr_safety_info_reveal": "1000/minute",
        },
    )
    def test_authenticated_burst_within_limit_is_not_refused(self):
        # A busy check-in desk: three reveals in quick succession, all
        # within the configured burst allowance.
        for _ in range(3):
            response = self.client.post(self.url)
            self.assertEqual(response.status_code, 200, response.data)

    @patch.dict(
        "rest_framework.throttling.SimpleRateThrottle.THROTTLE_RATES",
        {
            "qr_safety_info_reveal_user": "3/minute",
            "qr_safety_info_reveal": "1000/minute",
        },
    )
    def test_authenticated_caller_is_refused_once_limit_is_exceeded(self):
        for _ in range(3):
            response = self.client.post(self.url)
            self.assertEqual(response.status_code, 200, response.data)

        fourth = self.client.post(self.url)
        self.assertEqual(fourth.status_code, 429)

    @patch.dict(
        "rest_framework.throttling.SimpleRateThrottle.THROTTLE_RATES",
        {"qr_safety_info_reveal_user": "1/day", "qr_safety_info_reveal": "1000/minute"},
    )
    def test_authenticated_throttle_is_keyed_per_user_not_shared(self):
        first = self.client.post(self.url)
        self.assertEqual(first.status_code, 200, first.data)

        other_volunteer = AdminUser.objects.create_user(
            username="throttle_volunteer_2", password="pw"
        )
        other_client = APIClient()
        other_client.force_authenticate(user=other_volunteer)
        other_first = other_client.post(self.url)
        self.assertEqual(
            other_first.status_code,
            200,
            "a second user's own reveal should not be blocked by the first user's usage",
        )
