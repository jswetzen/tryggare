"""
PATCH /api/families/{id}/ — editing an existing family from the check-in UI
(FamilyUpdateSerializer / update_family_with_members). Mirrors the create-path
conventions in HealthConsentCreateAPITests (tests.py), but for the update path.
"""

from datetime import date

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Child, Family, Parent
from accounts.roles import COORDINATOR, grant

User = get_user_model()


class FamilyUpdateAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="deskstaff", password="pw")
        self.client = APIClient()
        grant(self.user, COORDINATOR)
        self.client.force_authenticate(user=self.user)

        self.family = Family.objects.create(last_name="Alvarez")
        self.parent = Parent.objects.create(
            family=self.family,
            first_name="Pat",
            last_name="Alvarez",
            relationship_type="MOM",
            email="pat@example.com",
        )
        self.child = Child.objects.create(
            family=self.family,
            first_name="Robin",
            last_name="Alvarez",
            birthdate=date(2019, 3, 1),
        )

    def test_updates_last_name(self):
        response = self.client.patch(
            f"/api/families/{self.family.id}/",
            {"last_name": "Renamed"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["last_name"], "Renamed")
        self.assertEqual(response.data["display_name"], "Renamed")

    def test_updates_an_existing_child_field(self):
        response = self.client.patch(
            f"/api/families/{self.family.id}/",
            {"children": [{"id": str(self.child.id), "first_name": "Robyn"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.child.refresh_from_db()
        self.assertEqual(self.child.first_name, "Robyn")
        self.assertEqual(Child.objects.filter(family=self.family).count(), 1)

    def test_adds_a_new_child(self):
        response = self.client.patch(
            f"/api/families/{self.family.id}/",
            {
                "children": [
                    {
                        "first_name": "Sibling",
                        "last_name": "Alvarez",
                        "birthdate": "2021-05-05",
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Child.objects.filter(family=self.family).count(), 2)
        # The pre-existing child is untouched, not removed.
        self.child.refresh_from_db()
        self.assertEqual(self.child.first_name, "Robin")

    def test_adds_a_new_parent(self):
        response = self.client.patch(
            f"/api/families/{self.family.id}/",
            {"parents": [{"first_name": "Sam", "relationship_type": "DAD"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Parent.objects.filter(family=self.family).count(), 2)

    def test_rejects_a_child_id_belonging_to_a_different_family(self):
        other_family = Family.objects.create(last_name="Other")
        other_child = Child.objects.create(
            family=other_family, first_name="NotYours", last_name="X"
        )
        response = self.client.patch(
            f"/api/families/{self.family.id}/",
            {"children": [{"id": str(other_child.id), "first_name": "Hijacked"}]},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        other_child.refresh_from_db()
        self.assertEqual(other_child.first_name, "NotYours")

    def test_response_includes_full_nested_ticket_and_checkin_fields(self):
        """The response must come back through FamilyDetailSerializer, not
        the thin write-only Upsert serializers — the check-in UI needs
        ticket_type/is_checked_in etc. to update its local state."""
        response = self.client.patch(
            f"/api/families/{self.family.id}/",
            {"last_name": "Alvarez"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        child_data = response.data["children"][0]
        self.assertIn("ticket_type", child_data)
        self.assertIn("is_checked_in", child_data)
        parent_data = response.data["parents"][0]
        self.assertIn("ticket_type", parent_data)
        self.assertIn("is_checked_in", parent_data)

    def test_granted_consent_on_update_stores_text_and_stamps_metadata(self):
        response = self.client.patch(
            f"/api/families/{self.family.id}/",
            {
                "children": [
                    {
                        "id": str(self.child.id),
                        "allergies": "Peanuts",
                        "health_consent_status": "granted",
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.child.refresh_from_db()
        self.assertEqual(self.child.allergies, "Peanuts")
        self.assertEqual(
            self.child.health_consent_status, Child.HealthConsentStatus.GRANTED
        )
        self.assertIsNotNone(self.child.health_consent_at)
        self.assertEqual(
            self.child.health_consent_notice_version,
            settings.HEALTH_CONSENT_NOTICE_VERSION,
        )

    def test_editing_unrelated_field_does_not_restamp_existing_consent(self):
        self.child.health_consent_status = Child.HealthConsentStatus.GRANTED
        self.child.allergies = "Peanuts"
        self.child.save()
        original_at = self.child.health_consent_at

        response = self.client.patch(
            f"/api/families/{self.family.id}/",
            {
                "children": [
                    {
                        "id": str(self.child.id),
                        "first_name": "Robyn",
                        "health_consent_status": "granted",
                        "allergies": "Peanuts",
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.child.refresh_from_db()
        self.assertEqual(self.child.health_consent_at, original_at)


class ParentSerializerHealthFieldsTests(TestCase):
    """The general ParentSerializer (used by ParentViewSet and nested in
    FamilySerializer/FamilyDetailSerializer) must expose allergies/notes/
    health-consent fields, same as ChildSerializer already does — otherwise
    there's no data to pre-fill an edit form with for a parent."""

    def setUp(self):
        self.user = User.objects.create_user(username="deskstaff", password="pw")
        self.client = APIClient()
        grant(self.user, COORDINATOR)
        self.client.force_authenticate(user=self.user)

        self.family = Family.objects.create(last_name="Nguyen")
        self.parent = Parent.objects.create(
            family=self.family,
            first_name="Lin",
            last_name="Nguyen",
            relationship_type="MOM",
            allergies="Shellfish",
            notes="Carries an EpiPen",
            health_consent_status=Parent.HealthConsentStatus.GRANTED,
        )

    def test_parent_detail_includes_health_fields(self):
        response = self.client.get(f"/api/parents/{self.parent.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["allergies"], "Shellfish")
        self.assertEqual(response.data["notes"], "Carries an EpiPen")
        self.assertEqual(response.data["health_consent_status"], "granted")

    def test_family_detail_nests_parent_health_fields(self):
        response = self.client.get(f"/api/families/{self.family.id}/")
        self.assertEqual(response.status_code, 200)
        parent_data = response.data["parents"][0]
        self.assertEqual(parent_data["allergies"], "Shellfish")
        self.assertEqual(parent_data["health_consent_status"], "granted")
