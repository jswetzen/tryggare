"""Read-behind-reveal for allergy/emergency-medical text on the check-in path.

The QR path already distinguishes a glance (``qr_viewed``) from an access
(``qr_safety_info_revealed``). These tests assert the authenticated check-in
path now does the same: the roster carries a flag, the text needs an explicit
reveal, and the reveal leaves a row.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from accounts.roles import COORDINATOR, VOLUNTEER, grant
from checkins.models import AuditLog
from families.models import Child, Family, Parent

User = get_user_model()


class SafetyInfoDisclosureTests(TestCase):
    def setUp(self):
        self.family = Family.objects.create(last_name="Andersson")
        self.child = Child.objects.create(
            first_name="Alva",
            last_name="Andersson",
            family=self.family,
            allergies="Jordnötter",
            notes="Epilepsi",
        )
        self.quiet_child = Child.objects.create(
            first_name="Bo", last_name="Andersson", family=self.family
        )
        self.parent = Parent.objects.create(
            first_name="Cecilia",
            last_name="Andersson",
            family=self.family,
            allergies="Penicillin",
        )
        self.other_family = Family.objects.create(last_name="Bergström")
        self.other_child = Child.objects.create(
            first_name="Doris",
            last_name="Bergström",
            family=self.other_family,
            allergies="Latex",
        )

        self.volunteer = grant(
            User.objects.create_user("volontar", "pw-12345678"), VOLUNTEER
        )
        self.coordinator = grant(
            User.objects.create_user("koordinator", "pw-12345678"), COORDINATOR
        )

    def _client(self, user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    def _child_payload(self, response, child):
        family = next(f for f in response.json() if f["id"] == str(self.family.id))
        return next(c for c in family["children"] if c["id"] == str(child.id))

    # -- the roster ---------------------------------------------------------

    def test_volunteer_roster_flags_safety_info_without_the_text(self):
        response = self._client(self.volunteer).get("/api/families/")
        self.assertEqual(response.status_code, 200)
        payload = self._child_payload(response, self.child)
        self.assertTrue(payload["has_safety_info"])
        self.assertIsNone(payload["allergies"])
        self.assertIsNone(payload["notes"])

    def test_volunteer_roster_flags_a_parents_safety_info_too(self):
        """Parent carries these fields as well — no child-only mental model."""
        response = self._client(self.volunteer).get("/api/families/")
        family = next(f for f in response.json() if f["id"] == str(self.family.id))
        parent = next(p for p in family["parents"] if p["id"] == str(self.parent.id))
        self.assertTrue(parent["has_safety_info"])
        self.assertIsNone(parent["allergies"])

    def test_flag_is_false_when_there_is_nothing_to_reveal(self):
        response = self._client(self.volunteer).get("/api/families/")
        self.assertFalse(
            self._child_payload(response, self.quiet_child)["has_safety_info"]
        )

    def test_coordinator_still_reads_the_text_directly(self):
        """They may edit the field; an edit form that hides its own value is
        not an edit form."""
        response = self._client(self.coordinator).get("/api/families/")
        payload = self._child_payload(response, self.child)
        self.assertTrue(payload["has_safety_info"])
        self.assertEqual(payload["allergies"], "Jordnötter")
        self.assertEqual(payload["notes"], "Epilepsi")

    def test_detail_view_masks_for_a_volunteer_too(self):
        response = self._client(self.volunteer).get(f"/api/families/{self.family.id}/")
        child = next(
            c for c in response.json()["children"] if c["id"] == str(self.child.id)
        )
        self.assertTrue(child["has_safety_info"])
        self.assertIsNone(child["allergies"])

    def test_nested_children_action_keeps_the_text_for_a_coordinator(self):
        """Regression guard: the action builds its serializer by hand, and a
        missing context would mask the text for everyone."""
        response = self._client(self.coordinator).get(
            f"/api/families/{self.family.id}/children/"
        )
        child = next(c for c in response.json() if c["id"] == str(self.child.id))
        self.assertEqual(child["allergies"], "Jordnötter")

    # -- the reveal ---------------------------------------------------------

    def _reveal(self, user, family, attendee_id):
        return self._client(user).post(
            f"/api/families/{family.id}/reveal-safety-info/",
            {"attendee_id": str(attendee_id)},
            format="json",
        )

    def test_volunteer_can_reveal_a_child(self):
        response = self._reveal(self.volunteer, self.family, self.child.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["allergies"], "Jordnötter")
        self.assertEqual(response.json()["notes"], "Epilepsi")

    def test_volunteer_can_reveal_a_parent(self):
        response = self._reveal(self.volunteer, self.family, self.parent.id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["allergies"], "Penicillin")

    def test_reveal_writes_exactly_one_audit_row(self):
        self._reveal(self.volunteer, self.family, self.child.id)
        rows = AuditLog.objects.filter(action="safety_info_revealed")
        self.assertEqual(rows.count(), 1)
        row = rows.get()
        self.assertEqual(row.user, self.volunteer)
        self.assertEqual(row.entity_type, "Child")
        self.assertEqual(row.entity_id, str(self.child.id))
        self.assertEqual(row.details["family_id"], str(self.family.id))
        self.assertTrue(row.details["had_allergies"])
        self.assertTrue(row.details["had_notes"])

    def test_a_parent_reveal_is_logged_as_a_parent(self):
        self._reveal(self.volunteer, self.family, self.parent.id)
        row = AuditLog.objects.get(action="safety_info_revealed")
        self.assertEqual(row.entity_type, "Parent")
        self.assertEqual(row.entity_id, str(self.parent.id))
        self.assertFalse(row.details["had_notes"])

    def test_a_glance_stays_distinguishable_from_an_access(self):
        client = self._client(self.volunteer)
        client.get(f"/api/families/{self.family.id}/")
        self.assertEqual(AuditLog.objects.filter(action="record_viewed").count(), 1)
        self.assertEqual(
            AuditLog.objects.filter(action="safety_info_revealed").count(), 0
        )
        self._reveal(self.volunteer, self.family, self.child.id)
        self.assertEqual(
            AuditLog.objects.filter(action="safety_info_revealed").count(), 1
        )

    def test_each_reveal_is_its_own_row(self):
        self._reveal(self.volunteer, self.family, self.child.id)
        self._reveal(self.volunteer, self.family, self.child.id)
        self.assertEqual(
            AuditLog.objects.filter(action="safety_info_revealed").count(), 2
        )

    # -- the edges ----------------------------------------------------------

    def test_attendee_from_another_family_is_not_reachable(self):
        response = self._reveal(self.volunteer, self.family, self.other_child.id)
        self.assertEqual(response.status_code, 404)
        self.assertFalse(
            AuditLog.objects.filter(action="safety_info_revealed").exists()
        )

    def test_missing_attendee_id_is_a_bad_request(self):
        response = self._client(self.volunteer).post(
            f"/api/families/{self.family.id}/reveal-safety-info/", {}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_anonymous_cannot_reveal(self):
        response = APIClient().post(
            f"/api/families/{self.family.id}/reveal-safety-info/",
            {"attendee_id": str(self.child.id)},
            format="json",
        )
        self.assertIn(response.status_code, (401, 403))
        self.assertFalse(
            AuditLog.objects.filter(action="safety_info_revealed").exists()
        )

    def test_a_user_without_family_read_cannot_reveal(self):
        nobody = User.objects.create_user("ingen", "pw-12345678")
        response = self._reveal(nobody, self.family, self.child.id)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(
            AuditLog.objects.filter(action="safety_info_revealed").exists()
        )
