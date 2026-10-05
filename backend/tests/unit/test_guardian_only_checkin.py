"""
Check-in gates for a guardian-only adult (owner decision d9245e21).

A stored guardian-only adult on a CONFIRMED registration for the session's
event satisfies the ``all`` ticket rule without a ticket; everyone else is gated
exactly as before, and an unconfirmed registration blocks them the same way
it blocks a ticketed attendee.
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.roles import VOLUNTEER, grant
from checkins.eligibility import (
    parent_checkin_gate_error,
    registration_checkin_gate_error,
)
from events.models import Event, Session
from families.models import Family, Parent
from registrations.models import Registration
from registrations.tokens import generate_verification_token, hash_token

CHECKIN_URL = reverse("checkin-check-in")
Status = Registration.Status


def _event(name="E"):
    today = timezone.now().date()
    return Event.objects.create(name=name, start_date=today, end_date=today)


def _session(event, rule=Session.TicketRule.ALL, adults_not_checked_in=False):
    now = timezone.now()
    return Session.objects.create(
        name="S",
        event=event,
        start_time=now,
        end_time=now + timedelta(hours=2),
        is_active=True,
        ticket_rule=rule,
        adults_not_checked_in=adults_not_checked_in,
    )


def _guardian(event, status=Status.CONFIRMED, marked=True, name="Gu"):
    family = Family.objects.create(last_name="G")
    parent = Parent.objects.create(first_name=name, family=family)
    registration = Registration.objects.create(
        event=event,
        family=family,
        contact_email="g@example.com",
        verification_token_hash=hash_token(generate_verification_token()),
        status=status,
    )
    if marked:
        registration.guardian_only_parents.add(parent)
    return parent, registration


def _client():
    user = get_user_model().objects.create_user(username="door")
    client = APIClient()
    client.force_authenticate(user=grant(user, VOLUNTEER))
    return client


def _check_in(client, parent, session):
    return client.post(
        CHECKIN_URL,
        {"child": str(parent.id), "session": str(session.id)},
        format="json",
    )


@pytest.mark.django_db
class TestGuardianOnlyGate:
    def test_marked_guardian_on_confirmed_registration_may_check_in(self):
        event = _event()
        session = _session(event)
        parent, _ = _guardian(event)
        assert not parent.has_ticket

        assert parent_checkin_gate_error(parent, session) is None
        assert registration_checkin_gate_error(parent, session) is None
        response = _check_in(_client(), parent, session)
        assert response.status_code == 201, response.data

    def test_ordinary_ticketless_adult_is_still_refused(self):
        """Same registration shape, same confirmed status, but no marker: the
        gate is not weakened for ordinary adults."""
        event = _event()
        session = _session(event)
        parent, _ = _guardian(event, marked=False)

        response = _check_in(_client(), parent, session)
        assert response.status_code == 400
        assert "ticket" in response.data["error"].lower()

    @pytest.mark.parametrize(
        "status",
        [Status.PENDING_VERIFICATION, Status.PENDING_PAYMENT, Status.CANCELLED],
    )
    def test_marked_guardian_on_an_unconfirmed_registration_is_blocked(self, status):
        event = _event()
        session = _session(event)
        parent, _ = _guardian(event, status=status)

        assert (
            registration_checkin_gate_error(parent, session)
            == "Registration is not yet confirmed"
        )
        response = _check_in(_client(), parent, session)
        assert response.status_code == 400
        assert "not yet confirmed" in response.data["error"]

    def test_adults_not_checked_in_still_excludes_a_confirmed_guardian(self):
        event = _event()
        session = _session(event, adults_not_checked_in=True)
        parent, _ = _guardian(event)

        assert parent_checkin_gate_error(parent, session) is not None
        assert _check_in(_client(), parent, session).status_code == 400

    def test_a_confirmed_registration_for_another_event_does_not_count(self):
        event = _event("E1")
        other = _event("E2")
        session = _session(other)
        parent, _ = _guardian(event)

        assert parent_checkin_gate_error(parent, session) is not None
        assert registration_checkin_gate_error(parent, session) is None

    def test_works_from_a_base_attendee_instance_too(self):
        """registration_checkin_gate_error receives whatever the caller has;
        the generic CheckInRecord serializer passes a base Attendee."""
        from families.models import Attendee

        event = _event()
        session = _session(event)
        parent, _ = _guardian(event, status=Status.PENDING_VERIFICATION)
        base = Attendee.objects.get(pk=parent.pk)

        assert registration_checkin_gate_error(base, session) is not None


@pytest.mark.django_db
def test_parent_admin_shows_the_guardian_only_marker_as_a_read_only_column():
    from django.contrib.admin.sites import site
    from django.test import RequestFactory

    event = _event()
    marked, _ = _guardian(event, name="Marked")
    plain, _ = _guardian(event, marked=False, name="Plain")

    model_admin = site._registry[Parent]
    assert "guardian_only" in model_admin.list_display
    request = RequestFactory().get("/")
    request.user = get_user_model().objects.create_superuser("root", "pw")
    assert "guardian_only" not in model_admin.get_fields(request)
    rows = {p.first_name: p for p in model_admin.get_queryset(request)}
    assert model_admin.guardian_only(rows["Marked"]) is True
    assert model_admin.guardian_only(rows["Plain"]) is False
