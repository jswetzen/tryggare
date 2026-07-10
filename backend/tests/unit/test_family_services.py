"""
Unit tests for families.services.create_family_with_members, in particular
the consent_attestor_email matching behavior needed for two-guardian public
registration submissions (the verified guardian may not be first in the form).
"""

import pytest

from families.models import Child, Family
from families.services import create_family_with_members


@pytest.mark.django_db
class TestCreateFamilyWithMembers:
    def test_defaults_to_first_created_parent_when_no_attestor_email(self):
        family, _, _ = create_family_with_members(
            last_name="Andersson",
            parents_data=[
                {"first_name": "Anna", "relationship_type": "MOTHER"},
                {"first_name": "Bo", "relationship_type": "FATHER"},
            ],
            children_data=[
                {
                    "first_name": "Kim",
                    "allergies": "Peanuts",
                    "health_consent_status": Child.HealthConsentStatus.GRANTED,
                }
            ],
        )
        child = family.children.first()
        assert child.health_consent_by.first_name == "Anna"

    def test_matches_attestor_by_email_even_when_not_first(self):
        family, _, _ = create_family_with_members(
            last_name="Andersson",
            parents_data=[
                {
                    "first_name": "Anna",
                    "relationship_type": "MOTHER",
                    "email": "anna@example.com",
                },
                {
                    "first_name": "Bo",
                    "relationship_type": "FATHER",
                    "email": "bo@example.com",
                },
            ],
            children_data=[
                {
                    "first_name": "Kim",
                    "allergies": "Peanuts",
                    "health_consent_status": Child.HealthConsentStatus.GRANTED,
                }
            ],
            consent_attestor_email="bo@example.com",
        )
        child = family.children.first()
        assert child.health_consent_by.first_name == "Bo"

    def test_falls_back_to_first_parent_when_attestor_email_matches_nobody(self):
        family, _, _ = create_family_with_members(
            last_name="Andersson",
            parents_data=[
                {
                    "first_name": "Anna",
                    "relationship_type": "MOTHER",
                    "email": "anna@example.com",
                },
            ],
            children_data=[
                {
                    "first_name": "Kim",
                    "allergies": "Peanuts",
                    "health_consent_status": Child.HealthConsentStatus.GRANTED,
                }
            ],
            consent_attestor_email="nonexistent@example.com",
        )
        child = family.children.first()
        assert child.health_consent_by.first_name == "Anna"

    def test_child_only_submission_has_no_attestor(self):
        family, _, _ = create_family_with_members(
            last_name="KidsOnly",
            parents_data=[],
            children_data=[{"first_name": "Kim"}],
        )
        assert family.children.first().health_consent_by is None

    def test_creates_a_new_family_each_call(self):
        family, _, _ = create_family_with_members(
            last_name="Andersson", parents_data=[], children_data=[]
        )
        assert Family.objects.filter(pk=family.pk).exists()
