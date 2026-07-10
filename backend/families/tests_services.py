"""
create_family_with_members's consent_attestor_email matching — which of a
public registration's newly-created parents is recorded as having attested
to a child's (or an adult's own) health-data consent decision.
"""

from django.test import TestCase

from .models import Child, Parent
from .services import create_family_with_members


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
