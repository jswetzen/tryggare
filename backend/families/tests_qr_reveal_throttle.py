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
