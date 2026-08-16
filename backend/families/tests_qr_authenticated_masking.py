"""The QR page's authenticated (logged-in-volunteer) path used to hand
allergy/medical-notes text to anyone who could log in at all — no reveal
step, no per-view audit row — while the check-in screen and the anonymous
QR path both mask and audit. These tests assert the authenticated path now
matches: masked unless the viewer already holds change_child/change_parent,
unmasked for a Koordinator (who may edit the field), and every logged-in
reveal writes exactly one qr_safety_info_revealed row naming the viewer.

Also proves the anonymous path is unchanged: still masked on GET, still
unmasked-only-through-reveal, still one audit row per reveal with no user
attached.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.roles import COORDINATOR, VOLUNTEER, grant
from checkins.models import AuditLog, CheckInRecord
from checkins.qr_utils import allocate_code_for_checkin
from events.models import Event, Session
from families.models import Child, Family, Parent

User = get_user_model()


class QrAuthenticatedMaskingTests(TestCase):
    def setUp(self):
        self.family = Family.objects.create(last_name="Lindqvist")
        self.child = Child.objects.create(
            first_name="Elsa",
            last_name="Lindqvist",
            family=self.family,
            allergies="Jordnötter",
            notes="Astma",
        )
        self.parent = Parent.objects.create(
            first_name="Nils",
            last_name="Lindqvist",
            family=self.family,
            allergies="Penicillin",
        )
        event = Event.objects.create(
            name="QR Masking Conf",
            start_date=timezone.now().date(),
            end_date=timezone.now().date(),
        )
        session = Session.objects.create(
            name="Morning",
            event=event,
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(hours=2),
        )
        self.volunteer = grant(
            User.objects.create_user("volontar", "pw-12345678"), VOLUNTEER
        )
        self.coordinator = grant(
            User.objects.create_user("koordinator", "pw-12345678"), COORDINATOR
        )

        self.child_checkin = CheckInRecord.objects.create(
            attendee=self.child, session=session, check_in_staff=self.coordinator
        )
        self.child_code = allocate_code_for_checkin(self.child_checkin).code

        self.parent_checkin = CheckInRecord.objects.create(
            attendee=self.parent, session=session, check_in_staff=self.coordinator
        )
        self.parent_code = allocate_code_for_checkin(self.parent_checkin).code

    def _client(self, user=None):
        client = APIClient()
        if user is not None:
            client.force_authenticate(user)
        return client

    # -- the GET is masked for anyone who can't already edit ----------------

    def test_anonymous_get_does_not_contain_the_health_text(self):
        response = self._client().get(f"/api/qr/{self.child_code}/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsNone(payload["child"]["allergies"])
        self.assertIsNone(payload["child"]["notes"])
        self.assertTrue(payload["child"]["has_safety_info"])
        self.assertNotIn("Jordnötter", response.content.decode())

    def test_logged_in_volunteer_get_does_not_contain_the_health_text(self):
        """The gap this increment closes: being logged in used to be enough
        on its own."""
        response = self._client(self.volunteer).get(f"/api/qr/{self.child_code}/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIsNone(payload["child"]["allergies"])
        self.assertIsNone(payload["child"]["notes"])
        self.assertTrue(payload["child"]["has_safety_info"])
        self.assertNotIn("Jordnötter", response.content.decode())

    def test_logged_in_volunteer_get_masks_a_parents_text_too(self):
        response = self._client(self.volunteer).get(f"/api/qr/{self.parent_code}/")
        payload = response.json()
        self.assertIsNone(payload["child"]["allergies"])
        self.assertTrue(payload["child"]["has_safety_info"])

    def test_coordinator_get_still_reads_the_text_directly(self):
        """They may edit the field; an edit form that hides its own value is
        not an edit form."""
        response = self._client(self.coordinator).get(f"/api/qr/{self.child_code}/")
        payload = response.json()
        self.assertEqual(payload["child"]["allergies"], "Jordnötter")
        self.assertEqual(payload["child"]["notes"], "Astma")

    # -- the reveal, and its audit row ---------------------------------------

    def test_volunteer_reveal_writes_exactly_one_audit_row_naming_them(self):
        response = self._client(self.volunteer).post(
            f"/api/qr/{self.child_code}/reveal-safety-info/"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["allergies"], "Jordnötter")

        rows = AuditLog.objects.filter(action="qr_safety_info_revealed")
        self.assertEqual(rows.count(), 1)
        row = rows.get()
        self.assertEqual(row.user, self.volunteer)
        self.assertEqual(row.entity_type, "Child")
        self.assertEqual(row.entity_id, str(self.child.id))

    def test_anonymous_reveal_still_writes_one_unattributed_row(self):
        """Proves the anonymous path is unchanged by this increment."""
        response = self._client().post(f"/api/qr/{self.child_code}/reveal-safety-info/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["allergies"], "Jordnötter")

        rows = AuditLog.objects.filter(action="qr_safety_info_revealed")
        self.assertEqual(rows.count(), 1)
        self.assertIsNone(rows.get().user)

    def test_a_glance_stays_distinguishable_from_a_reveal_for_a_volunteer(self):
        client = self._client(self.volunteer)
        client.get(f"/api/qr/{self.child_code}/")
        self.assertEqual(AuditLog.objects.filter(action="qr_viewed").count(), 1)
        self.assertEqual(
            AuditLog.objects.filter(action="qr_safety_info_revealed").count(), 0
        )
        client.post(f"/api/qr/{self.child_code}/reveal-safety-info/")
        self.assertEqual(
            AuditLog.objects.filter(action="qr_safety_info_revealed").count(), 1
        )
