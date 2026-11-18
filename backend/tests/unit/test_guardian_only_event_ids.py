"""
``guardian_only_event_ids`` on the family payload: the check-in screen's only
way to know a ticketless adult is exempt from the ``all`` ticket rule.

It must agree with the server gate (checkins/eligibility.py), so it lists only
events where the adult is a stored guardian-only adult on a CONFIRMED
registration. ``ticket_details`` is unscoped display data and is untouched.
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.roles import VOLUNTEER, grant
from events.models import Event
from families.models import Family, Parent
from registrations.models import Registration
from registrations.tokens import generate_verification_token, hash_token

Status = Registration.Status


def _event(name):
    today = timezone.now().date()
    return Event.objects.create(
        name=name, start_date=today, end_date=today + timedelta(days=1)
    )


def _registration(event, family, status):
    return Registration.objects.create(
        event=event,
        family=family,
        contact_email="g@example.com",
        verification_token_hash=hash_token(generate_verification_token()),
        status=status,
    )


def _client():
    user = get_user_model().objects.create_user(username="door")
    client = APIClient()
    client.force_authenticate(user=grant(user, VOLUNTEER))
    return client


def _parents_of(client, family):
    response = client.get(reverse("family-detail", args=[family.id]))
    assert response.status_code == 200, response.data
    return {p["first_name"]: p for p in response.data["parents"]}


@pytest.mark.django_db
class TestGuardianOnlyEventIds:
    def test_lists_only_events_with_a_confirmed_guardian_registration(self):
        confirmed_event = _event("Confirmed")
        pending_event = _event("Pending")
        family = Family.objects.create(last_name="G")
        guardian = Parent.objects.create(first_name="Guardian", family=family)
        _registration(
            confirmed_event, family, Status.CONFIRMED
        ).guardian_only_parents.add(guardian)
        _registration(
            pending_event, family, Status.PENDING_PAYMENT
        ).guardian_only_parents.add(guardian)

        parents = _parents_of(_client(), family)

        assert parents["Guardian"]["guardian_only_event_ids"] == [
            str(confirmed_event.id)
        ]

    def test_an_ordinary_adult_and_a_ticketless_unmarked_adult_get_an_empty_list(self):
        event = _event("E")
        family = Family.objects.create(last_name="G")
        Parent.objects.create(first_name="Plain", family=family)
        # A confirmed registration exists, but this adult is not marked on it:
        # being ticketless is not the same as being a guardian-only adult.
        _registration(event, family, Status.CONFIRMED)

        parents = _parents_of(_client(), family)

        assert parents["Plain"]["guardian_only_event_ids"] == []

    def test_the_marker_is_per_adult(self):
        event = _event("E")
        family = Family.objects.create(last_name="G")
        guardian = Parent.objects.create(first_name="Guardian", family=family)
        Parent.objects.create(first_name="Other", family=family)
        _registration(event, family, Status.CONFIRMED).guardian_only_parents.add(
            guardian
        )

        parents = _parents_of(_client(), family)

        assert parents["Guardian"]["guardian_only_event_ids"] == [str(event.id)]
        assert parents["Other"]["guardian_only_event_ids"] == []

    def test_serializer_without_the_prefetch_gives_the_same_answer(self):
        """Parents reached outside the family viewset (no prefetch) fall back
        to a query and must agree."""
        from families.serializers import ParentSerializer

        event = _event("E")
        family = Family.objects.create(last_name="G")
        guardian = Parent.objects.create(first_name="Guardian", family=family)
        _registration(event, family, Status.CONFIRMED).guardian_only_parents.add(
            guardian
        )

        data = ParentSerializer(guardian).data

        assert data["guardian_only_event_ids"] == [str(event.id)]
