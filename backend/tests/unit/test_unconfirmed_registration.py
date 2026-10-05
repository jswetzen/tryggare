"""
``unconfirmed_registration`` on the family payload: per person, where the
server would refuse a check-in because a self-serve registration is not
confirmed -- ``{"event_ids": [...], "session_ids": [...]}``.

The screen rule is "blocked iff session.event in event_ids or session.id in
session_ids", so these tests pin two things:

* the lists themselves (the matrix of ticket kinds / statuses), and
* that they agree with the real gate, ``registration_checkin_gate_error``,
  session by session (``_assert_agrees_with_gate``), because the whole point
  of marking people is that the screen does not promise what the server
  refuses.

The exclusion rule against the family-level ``pending_payment`` marker is
covered separately: a person is left out of the lists ONLY when their
blocking registration is the one that marker actually surfaces.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.roles import VOLUNTEER, grant
from checkins.eligibility import registration_checkin_gate_error
from events.models import Event, EventTicket, Session, SessionTicket
from families.models import Child, Family, Parent
from registrations.models import Payment, Registration
from registrations.tokens import generate_verification_token, hash_token

Status = Registration.Status


def _event(name="Camp"):
    today = timezone.now().date()
    return Event.objects.create(
        name=name, start_date=today, end_date=today + timedelta(days=1)
    )


def _session(event, name):
    return Session.objects.create(
        event=event,
        name=name,
        start_time=timezone.now(),
        end_time=timezone.now() + timedelta(hours=2),
        is_active=True,
    )


def _registration(event, family, status, *, payment=False):
    registration = Registration.objects.create(
        event=event,
        family=family,
        contact_email="g@example.com",
        verification_token_hash=hash_token(generate_verification_token()),
        status=status,
    )
    if payment:
        Payment.objects.create(registration=registration, amount=Decimal("100.00"))
    return registration


_clients = iter(range(10_000))


def _client():
    user = get_user_model().objects.create_user(username=f"door{next(_clients)}")
    client = APIClient()
    client.force_authenticate(user=grant(user, VOLUNTEER))
    return client


def _family_payload(family):
    response = _client().get(reverse("family-detail", args=[family.id]))
    assert response.status_code == 200, response.data
    return response.data


def _marks(family):
    """first_name -> unconfirmed_registration for every member."""
    data = _family_payload(family)
    return {
        person["first_name"]: person["unconfirmed_registration"]
        for person in data["children"] + data["parents"]
    }


def _blocked_on_screen(marker, session):
    """The check-in screen's rule, verbatim."""
    return (
        str(session.event_id) in marker["event_ids"]
        or str(session.id) in (marker["session_ids"])
    )


def _assert_agrees_with_gate(person, marker, sessions):
    """Per session, the marker blocks exactly when the server gate does.

    Only meaningful for people that no ``pending_payment`` banner speaks for
    (those are excluded from the lists on purpose, while the gate still
    refuses them), so the callers use it on non-surfaced registrations.
    """
    for session in sessions:
        gate_refuses = registration_checkin_gate_error(person, session) is not None
        assert _blocked_on_screen(marker, session) == gate_refuses, (
            f"screen/server disagree for {person} on {session}"
        )


@pytest.fixture
def world():
    event = _event()
    family = Family.objects.create(last_name="Berg")
    return event, family


@pytest.mark.django_db
class TestTicketMatrix:
    def test_pending_session_ticket_blocks_that_session_only(self, world):
        event, family = world
        session_a = _session(event, "A")
        session_b = _session(event, "B")
        child = Child.objects.create(first_name="Kim", family=family)
        pending = _registration(event, family, Status.PENDING_VERIFICATION)
        confirmed = _registration(event, family, Status.CONFIRMED)
        SessionTicket.objects.create(
            attendee=child, session=session_a, registration=pending
        )
        SessionTicket.objects.create(
            attendee=child, session=session_b, registration=confirmed
        )

        marker = _marks(family)["Kim"]

        assert marker == {"event_ids": [], "session_ids": [str(session_a.id)]}
        assert _blocked_on_screen(marker, session_a)
        assert not _blocked_on_screen(marker, session_b)
        _assert_agrees_with_gate(child, marker, [session_a, session_b])

    def test_pending_event_ticket_blocks_every_session_of_the_event(self, world):
        event, family = world
        sessions = [_session(event, "A"), _session(event, "B")]
        other_event_session = _session(_event("Other"), "Elsewhere")
        child = Child.objects.create(first_name="Kim", family=family)
        EventTicket.objects.create(
            attendee=child,
            event=event,
            registration=_registration(event, family, Status.PENDING_VERIFICATION),
        )

        marker = _marks(family)["Kim"]

        assert marker == {"event_ids": [str(event.id)], "session_ids": []}
        _assert_agrees_with_gate(child, marker, [*sessions, other_event_session])

    def test_guardian_only_adult_on_an_unconfirmed_registration(self, world):
        event, family = world
        session = _session(event, "A")
        guardian = Parent.objects.create(first_name="Bengt", family=family)
        _registration(
            event, family, Status.PENDING_VERIFICATION
        ).guardian_only_parents.add(guardian)

        marker = _marks(family)["Bengt"]

        assert marker == {"event_ids": [str(event.id)], "session_ids": []}
        _assert_agrees_with_gate(guardian, marker, [session])

    def test_guardian_only_adult_with_one_confirmed_registration_is_not_marked(
        self, world
    ):
        """The gate lets a guardian through when ANY of their registrations
        for the event is confirmed, so the marker must not list them."""
        event, family = world
        session = _session(event, "A")
        guardian = Parent.objects.create(first_name="Bengt", family=family)
        _registration(
            event, family, Status.PENDING_VERIFICATION
        ).guardian_only_parents.add(guardian)
        _registration(event, family, Status.CONFIRMED).guardian_only_parents.add(
            guardian
        )

        marker = _marks(family)["Bengt"]

        assert marker == {"event_ids": [], "session_ids": []}
        _assert_agrees_with_gate(guardian, marker, [session])

    def test_staff_created_and_confirmed_tickets_are_never_marked(self, world):
        event, family = world
        session = _session(event, "A")
        staff = Child.objects.create(first_name="Staff", family=family)
        confirmed = Child.objects.create(first_name="Done", family=family)
        Child.objects.create(first_name="Bare", family=family)
        EventTicket.objects.create(attendee=staff, event=event)  # registration=None
        EventTicket.objects.create(
            attendee=confirmed,
            event=event,
            registration=_registration(event, family, Status.CONFIRMED),
        )

        marks = _marks(family)

        for name in ("Staff", "Done", "Bare"):
            assert marks[name] == {"event_ids": [], "session_ids": []}
        _assert_agrees_with_gate(staff, marks["Staff"], [session])

    def test_the_marker_is_per_person(self, world):
        event, family = world
        session = _session(event, "A")
        blocked = Child.objects.create(first_name="Blocked", family=family)
        fine = Child.objects.create(first_name="Fine", family=family)
        EventTicket.objects.create(
            attendee=blocked,
            event=event,
            registration=_registration(event, family, Status.PENDING_VERIFICATION),
        )
        EventTicket.objects.create(attendee=fine, event=event)

        marks = _marks(family)

        assert marks["Blocked"]["event_ids"] == [str(event.id)]
        assert marks["Fine"] == {"event_ids": [], "session_ids": []}
        _assert_agrees_with_gate(blocked, marks["Blocked"], [session])
        _assert_agrees_with_gate(fine, marks["Fine"], [session])


@pytest.mark.django_db
class TestPendingPaymentExclusion:
    """The family-level ``pending_payment`` marker surfaces only the FIRST
    pending_payment registration, and only when it has a payment. A person is
    left out of the new lists only when THAT registration is what blocks them;
    otherwise they would be unmarked while the server still refuses them.
    """

    def test_the_surfaced_pending_payment_registration_is_left_to_the_banner(
        self, world
    ):
        event, family = world
        child = Child.objects.create(first_name="Kim", family=family)
        registration = _registration(
            event, family, Status.PENDING_PAYMENT, payment=True
        )
        EventTicket.objects.create(
            attendee=child, event=event, registration=registration
        )

        data = _family_payload(family)

        assert data["pending_payment"]["registration_id"] == str(registration.id)
        assert data["children"][0]["unconfirmed_registration"] == {
            "event_ids": [],
            "session_ids": [],
        }
        # ... and the server still refuses, which is why the banner exists.
        assert registration_checkin_gate_error(child, _session(event, "A"))

    def test_pending_payment_without_a_payment_stays_listed(self, world):
        event, family = world
        session = _session(event, "A")
        child = Child.objects.create(first_name="Kim", family=family)
        EventTicket.objects.create(
            attendee=child,
            event=event,
            registration=_registration(
                event, family, Status.PENDING_PAYMENT, payment=False
            ),
        )

        data = _family_payload(family)
        marker = data["children"][0]["unconfirmed_registration"]

        assert data["pending_payment"] is None  # the banner shows nothing
        assert marker == {"event_ids": [str(event.id)], "session_ids": []}
        _assert_agrees_with_gate(child, marker, [session])

    def test_a_second_pending_payment_registration_stays_listed(self, world):
        event, family = world
        other_event = _event("Other")
        first_child = Child.objects.create(first_name="One", family=family)
        second_child = Child.objects.create(first_name="Two", family=family)
        reg_one = _registration(event, family, Status.PENDING_PAYMENT, payment=True)
        reg_two = _registration(
            other_event, family, Status.PENDING_PAYMENT, payment=True
        )
        EventTicket.objects.create(
            attendee=first_child, event=event, registration=reg_one
        )
        EventTicket.objects.create(
            attendee=second_child, event=other_event, registration=reg_two
        )

        data = _family_payload(family)
        by_name = {c["first_name"]: c for c in data["children"]}
        surfaced = data["pending_payment"]["registration_id"]
        # Which of the two the banner shows is up to the queryset; whichever it
        # is, the OTHER child must be marked and this one must not.
        if surfaced == str(reg_one.id):
            covered, marked, marked_event = "One", "Two", other_event
        else:
            covered, marked, marked_event = "Two", "One", event

        assert by_name[covered]["unconfirmed_registration"] == {
            "event_ids": [],
            "session_ids": [],
        }
        assert by_name[marked]["unconfirmed_registration"] == {
            "event_ids": [str(marked_event.id)],
            "session_ids": [],
        }

    def test_blocked_by_the_surfaced_registration_and_another_stays_listed(self, world):
        """One person, one event, two blocking registrations: only one is
        covered by the banner, so the person must still be marked."""
        event, family = world
        guardian = Parent.objects.create(first_name="Bengt", family=family)
        paying = _registration(event, family, Status.PENDING_PAYMENT, payment=True)
        paying.guardian_only_parents.add(guardian)
        _registration(
            event, family, Status.PENDING_VERIFICATION
        ).guardian_only_parents.add(guardian)

        data = _family_payload(family)

        assert data["pending_payment"]["registration_id"] == str(paying.id)
        assert data["parents"][0]["unconfirmed_registration"] == {
            "event_ids": [str(event.id)],
            "session_ids": [],
        }

    def test_pending_session_ticket_on_the_surfaced_registration_is_excluded(
        self, world
    ):
        event, family = world
        session = _session(event, "A")
        child = Child.objects.create(first_name="Kim", family=family)
        SessionTicket.objects.create(
            attendee=child,
            session=session,
            registration=_registration(
                event, family, Status.PENDING_PAYMENT, payment=True
            ),
        )

        marker = _marks(family)["Kim"]

        assert marker == {"event_ids": [], "session_ids": []}


@pytest.mark.django_db
class TestQueryCount:
    def _build_family(self, event, sessions, last_name, members):
        family = Family.objects.create(last_name=last_name)
        pending = _registration(event, family, Status.PENDING_VERIFICATION)
        confirmed = _registration(event, family, Status.CONFIRMED)
        for i in range(members):
            child = Child.objects.create(first_name=f"C{i}", family=family)
            EventTicket.objects.create(
                attendee=child, event=event, registration=pending
            )
            SessionTicket.objects.create(
                attendee=child, session=sessions[0], registration=confirmed
            )
            parent = Parent.objects.create(first_name=f"P{i}", family=family)
            pending.guardian_only_parents.add(parent)
        return family

    def _queries_for_list(self):
        client = _client()
        with CaptureQueriesContext(connection) as ctx:
            response = client.get(reverse("family-list"))
        assert response.status_code == 200
        return len(ctx), response

    def test_query_count_does_not_grow_with_members_or_families(self):
        event = _event()
        sessions = [_session(event, "A"), _session(event, "B")]
        self._build_family(event, sessions, "Small", members=1)
        small, _ = self._queries_for_list()

        # Many more people, in more families: an N+1 on the marker (a lookup
        # per ticket registration, per guardian registration, per family
        # payment) would add queries here.
        for n in range(3):
            self._build_family(event, sessions, f"Big{n}", members=5)
        big, response = self._queries_for_list()

        assert big == small, f"queries grew from {small} to {big}"
        results = (
            response.data["results"] if "results" in response.data else response.data
        )
        marked = [
            person
            for family in results
            for person in family["children"] + family["parents"]
            if person["unconfirmed_registration"]["event_ids"]
        ]
        assert (
            len(marked) == 1 * 2 + 3 * 5 * 2
        )  # every child and parent in all 4 families


@pytest.mark.django_db
class TestOutsideTheFamilyPayload:
    """``/api/children/`` carries no family-level banner, so nothing there is
    "already covered": the person stays listed even when the family list would
    leave them out. The safe direction -- never an unmarked person the server
    refuses -- and no per-person query to find out."""

    def test_child_list_lists_a_person_the_family_banner_would_cover(self, world):
        event, family = world
        child = Child.objects.create(first_name="Kim", family=family)
        EventTicket.objects.create(
            attendee=child,
            event=event,
            registration=_registration(
                event, family, Status.PENDING_PAYMENT, payment=True
            ),
        )

        assert _marks(family)["Kim"] == {"event_ids": [], "session_ids": []}

        response = _client().get(reverse("child-list"))
        assert response.status_code == 200
        assert response.data[0]["unconfirmed_registration"] == {
            "event_ids": [str(event.id)],
            "session_ids": [],
        }
