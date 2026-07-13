"""
create_family_with_members's consent_attestor_email matching — which of a
public registration's newly-created parents is recorded as having attested
to a child's (or an adult's own) health-data consent decision.
"""

from django.test import TestCase

from .models import Child, Family, Parent
from .services import create_family_with_members, update_family_with_members


class ConsentAttestorMatchTests(TestCase):
    def _parents_data(self):
        return [
            {
                "first_name": "Bo",
                "relationship_type": "Father",
                "email": "bo@example.com",
            },
            {
                "first_name": "Anna",
                "relationship_type": "Mother",
                "email": "anna@example.com",
            },
        ]

    def _children_data(self):
        return [
            {
                "first_name": "Kim",
                "health_consent_status": Child.HealthConsentStatus.GRANTED,
            }
        ]

    def test_matches_attestor_by_exact_email(self):
        family, parents, children = create_family_with_members(
            parents_data=self._parents_data(),
            children_data=self._children_data(),
            consent_attestor_email="anna@example.com",
        )
        anna = next(p for p in parents if p.first_name == "Anna")
        self.assertEqual(children[0].health_consent_by_id, anna.id)

    def test_matches_attestor_case_insensitively(self):
        """A case-varied contact_email (mobile autocapitalize, or manual
        retyping) must still match the parent who actually verified — not
        silently fall back to created_parents[0] and record the wrong
        guardian as having attested to health-data consent."""
        family, parents, children = create_family_with_members(
            parents_data=self._parents_data(),
            children_data=self._children_data(),
            consent_attestor_email="Anna@Example.com",
        )
        anna = next(p for p in parents if p.first_name == "Anna")
        self.assertEqual(children[0].health_consent_by_id, anna.id)

    def test_falls_back_to_first_parent_when_no_match(self):
        family, parents, children = create_family_with_members(
            parents_data=self._parents_data(),
            children_data=self._children_data(),
            consent_attestor_email="someone-else@example.com",
        )
        self.assertEqual(children[0].health_consent_by_id, parents[0].id)


class AdultSelfConsentAttestorTests(TestCase):
    """A parent's own allergy/notes text is attested by the same
    ``consented_by`` resolution as a child's — whoever is present filling
    in the form on behalf of the whole party, not necessarily the adult
    themselves (no per-adult self-attestation link exists until Phase 4
    self-service edit is built)."""

    def _parents_data(self):
        return [
            {
                "first_name": "Bo",
                "relationship_type": "Father",
                "email": "bo@example.com",
                "allergies": "Peanuts",
                "health_consent_status": Parent.HealthConsentStatus.GRANTED,
            },
            {
                "first_name": "Anna",
                "relationship_type": "Mother",
                "email": "anna@example.com",
            },
        ]

    def test_another_parents_consent_is_attested_by_the_form_submitter(self):
        family, parents, children = create_family_with_members(
            parents_data=self._parents_data(),
            children_data=[],
            consent_attestor_email="anna@example.com",
        )
        bo = next(p for p in parents if p.first_name == "Bo")
        anna = next(p for p in parents if p.first_name == "Anna")
        self.assertEqual(bo.health_consent_by_id, anna.id)
        self.assertIsNotNone(bo.health_consent_at)

    def test_no_health_status_is_left_unattested(self):
        family, parents, children = create_family_with_members(
            parents_data=self._parents_data(),
            children_data=[],
            consent_attestor_email="anna@example.com",
        )
        anna = next(p for p in parents if p.first_name == "Anna")
        self.assertIsNone(anna.health_consent_by_id)
        self.assertIsNone(anna.health_consent_at)


class UpdateFamilyWithMembersTests(TestCase):
    """update_family_with_members — the check-in UI's edit-an-existing-
    family path. Mirrors create_family_with_members's consent-attestor
    resolution but must only ever create-or-update, never delete, and must
    only re-stamp consent when the decision is actually changing."""

    def setUp(self):
        self.family = Family.objects.create(last_name="Original")
        self.parent = Parent.objects.create(
            family=self.family,
            first_name="Bo",
            last_name="Original",
            relationship_type="Father",
            email="bo@example.com",
        )
        self.child = Child.objects.create(
            family=self.family,
            first_name="Kim",
            last_name="Original",
        )

    def test_updates_last_name(self):
        update_family_with_members(
            family=self.family, last_name="Renamed", parents_data=[], children_data=[]
        )
        self.family.refresh_from_db()
        self.assertEqual(self.family.last_name, "Renamed")

    def test_updates_existing_child_field(self):
        update_family_with_members(
            family=self.family,
            parents_data=[],
            children_data=[{"id": str(self.child.id), "first_name": "Kimberly"}],
        )
        self.child.refresh_from_db()
        self.assertEqual(self.child.first_name, "Kimberly")
        # Untouched fields survive the partial dict.
        self.assertEqual(self.child.last_name, "Original")

    def test_adds_a_new_child_without_touching_existing_ones(self):
        family, _parents, children = update_family_with_members(
            family=self.family,
            parents_data=[],
            children_data=[{"first_name": "Nyla", "last_name": "New"}],
        )
        self.assertEqual(len(children), 1)
        self.assertEqual(self.family.children.count(), 2)
        self.child.refresh_from_db()
        self.assertEqual(self.child.first_name, "Kim")

    def test_adds_a_new_parent(self):
        family, parents, _children = update_family_with_members(
            family=self.family,
            parents_data=[{"first_name": "Anna", "relationship_type": "Mother"}],
            children_data=[],
        )
        self.assertEqual(len(parents), 1)
        self.assertEqual(self.family.parents.count(), 2)

    def test_rejects_a_child_id_from_a_different_family(self):
        other_family = Family.objects.create(last_name="Other")
        other_child = Child.objects.create(
            family=other_family, first_name="NotYours", last_name="X"
        )
        with self.assertRaises(ValueError):
            update_family_with_members(
                family=self.family,
                parents_data=[],
                children_data=[{"id": str(other_child.id), "first_name": "Hijacked"}],
            )
        other_child.refresh_from_db()
        self.assertEqual(other_child.first_name, "NotYours")

    def test_rejects_a_parent_id_from_a_different_family(self):
        other_family = Family.objects.create(last_name="Other")
        other_parent = Parent.objects.create(
            family=other_family, first_name="NotYours", relationship_type="Father"
        )
        with self.assertRaises(ValueError):
            update_family_with_members(
                family=self.family,
                parents_data=[{"id": str(other_parent.id), "first_name": "Hijacked"}],
                children_data=[],
            )
        other_parent.refresh_from_db()
        self.assertEqual(other_parent.first_name, "NotYours")

    def test_editing_unrelated_field_does_not_restamp_existing_consent(self):
        self.child.health_consent_status = Child.HealthConsentStatus.GRANTED
        self.child.allergies = "Peanuts"
        self.child.save()
        original_at = self.child.health_consent_at
        original_by = self.child.health_consent_by

        update_family_with_members(
            family=self.family,
            parents_data=[],
            children_data=[
                {
                    "id": str(self.child.id),
                    "first_name": "Kim",
                    "health_consent_status": Child.HealthConsentStatus.GRANTED,
                    "allergies": "Peanuts and tree nuts",
                }
            ],
        )
        self.child.refresh_from_db()
        self.assertEqual(self.child.allergies, "Peanuts and tree nuts")
        self.assertEqual(self.child.health_consent_at, original_at)
        self.assertEqual(self.child.health_consent_by_id, original_by)

    def test_status_transition_stamps_consent(self):
        update_family_with_members(
            family=self.family,
            parents_data=[],
            children_data=[
                {
                    "id": str(self.child.id),
                    "health_consent_status": Child.HealthConsentStatus.GRANTED,
                    "allergies": "Peanuts",
                }
            ],
        )
        self.child.refresh_from_db()
        self.assertIsNotNone(self.child.health_consent_at)
        self.assertEqual(self.child.health_consent_by_id, self.parent.id)

    def test_consent_attestor_falls_back_to_existing_parent_not_in_payload(self):
        """Editing only a child, with no parents in this call's payload,
        must still resolve a plausible attestor from the family's existing
        parents rather than leaving health_consent_by unset."""
        update_family_with_members(
            family=self.family,
            parents_data=[],
            children_data=[
                {
                    "id": str(self.child.id),
                    "health_consent_status": Child.HealthConsentStatus.GRANTED,
                }
            ],
        )
        self.child.refresh_from_db()
        self.assertEqual(self.child.health_consent_by_id, self.parent.id)
