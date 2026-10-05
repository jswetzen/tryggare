"""
An adult's check-in is PER SESSION (owner decision 2026-10-01).

The server's check-in refuses a duplicate only in the SAME session, so an adult
who is in session B is still admissible to C. ``GET /api/families/?session=<id>``
therefore reports an adult's ``is_checked_in`` / ``active_checkin_id`` for that
session alone, and names the other sessions in ``checked_in_elsewhere``.
Without the parameter the payload is what it always was (open record in ANY
session), so no other caller changes.

Also pins the family list's query count flat in the number of families: the
``attendees`` Prefetch used ``to_attr="parents"``/``"children"``, which Django
treated as already fetched (``Family.parents`` makes ``hasattr`` true), so the
list ran ~24 queries per family until the to_attr was renamed.
"""

from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.roles import VOLUNTEER, grant
from checkins.models import CheckInRecord
from events.models import Event, Session
from families.models import Child, Family, Parent
from families.serializers import ParentSerializer

FAMILIES_URL = "/api/families/"


@pytest.fixture
def staff(db):
    return grant(get_user_model().objects.create_user(username="door"), VOLUNTEER)


@pytest.fixture
def client(staff):
    api = APIClient()
    api.force_authenticate(user=staff)
    return api


@pytest.fixture
def sessions(db):
    today = timezone.now().date()
    event = Event.objects.create(name="E", start_date=today, end_date=today)
    now = timezone.now()
    return {
        name: Session.objects.create(
            name=name,
            event=event,
            start_time=now,
            end_time=now + timedelta(hours=2),
            is_active=True,
        )
        for name in ("A", "B children", "C")
    }


def _family_with_adult(last_name="Lindgren"):
    family = Family.objects.create(last_name=last_name)
    adult = Parent.objects.create(first_name="Anna", family=family)
    return family, adult


def _check_in(attendee, session, staff, *, out=False):
    return CheckInRecord.objects.create(
        attendee=attendee,
        session=session,
        check_in_staff=staff,
        check_out_time=timezone.now() if out else None,
    )


def _adult(client, family, session=None):
    url = FAMILIES_URL + (f"?session={session.id}" if session else "")
    response = client.get(url)
    assert response.status_code == 200, response.data
    row = next(f for f in response.data if f["id"] == str(family.id))
    return row["parents"][0]


@pytest.mark.django_db
class TestAdultCheckInIsPerSession:
    def test_without_session_an_open_record_anywhere_counts(
        self, client, staff, sessions
    ):
        family, adult = _family_with_adult()
        record = _check_in(adult, sessions["B children"], staff)

        data = _adult(client, family)

        assert data["is_checked_in"] is True
        assert data["active_checkin_id"] == str(record.id)
        assert data["checked_in_elsewhere"] == []

    def test_in_the_session_where_they_are_checked_in(self, client, staff, sessions):
        family, adult = _family_with_adult()
        record = _check_in(adult, sessions["B children"], staff)

        data = _adult(client, family, sessions["B children"])

        assert data["is_checked_in"] is True
        assert data["active_checkin_id"] == str(record.id)
        assert data["checked_in_elsewhere"] == []

    def test_in_a_different_session_they_are_not_checked_in_and_it_says_where(
        self, client, staff, sessions
    ):
        family, adult = _family_with_adult()
        _check_in(adult, sessions["B children"], staff)

        data = _adult(client, family, sessions["C"])

        assert data["is_checked_in"] is False
        assert data["active_checkin_id"] is None
        assert data["checked_in_elsewhere"] == ["B children"]

    def test_checked_in_to_two_sessions_names_only_the_other_one(
        self, client, staff, sessions
    ):
        family, adult = _family_with_adult()
        here = _check_in(adult, sessions["A"], staff)
        _check_in(adult, sessions["B children"], staff)

        data = _adult(client, family, sessions["A"])

        assert data["active_checkin_id"] == str(here.id)
        assert data["checked_in_elsewhere"] == ["B children"]

    def test_a_checked_out_record_is_not_elsewhere(self, client, staff, sessions):
        family, adult = _family_with_adult()
        _check_in(adult, sessions["B children"], staff, out=True)

        data = _adult(client, family, sessions["C"])

        assert data["is_checked_in"] is False
        assert data["checked_in_elsewhere"] == []

    def test_another_adult_in_the_same_family_is_unaffected(
        self, client, staff, sessions
    ):
        family, adult = _family_with_adult()
        Parent.objects.create(first_name="Bo", family=family)
        _check_in(adult, sessions["B children"], staff)

        response = client.get(f"{FAMILIES_URL}?session={sessions['C'].id}")
        parents = {p["first_name"]: p for p in response.data[0]["parents"]}

        assert parents["Anna"]["checked_in_elsewhere"] == ["B children"]
        assert parents["Bo"]["checked_in_elsewhere"] == []

    def test_children_keep_their_any_session_answer(self, client, staff, sessions):
        family, _ = _family_with_adult()
        child = Child.objects.create(
            first_name="Kid", last_name="L", birthdate=date(2018, 1, 1), family=family
        )
        _check_in(child, sessions["B children"], staff)

        response = client.get(f"{FAMILIES_URL}?session={sessions['C'].id}")

        assert response.data[0]["children"][0]["is_checked_in"] is True

    def test_a_malformed_session_is_a_400_not_the_any_session_answer(self, client):
        response = client.get(f"{FAMILIES_URL}?session=not-a-uuid")

        assert response.status_code == 400

    def test_serializer_without_the_prefetch_gives_the_same_answer(
        self, staff, sessions
    ):
        """An adult reached outside the family viewset (no prefetch) falls back
        to a query and must agree."""
        _, adult = _family_with_adult()
        _check_in(adult, sessions["B children"], staff)

        here = ParentSerializer(
            adult, context={"session_id": sessions["B children"].id}
        )
        there = ParentSerializer(adult, context={"session_id": sessions["C"].id})
        anywhere = ParentSerializer(adult)

        assert here.data["is_checked_in"] is True
        assert there.data["is_checked_in"] is False
        assert there.data["checked_in_elsewhere"] == ["B children"]
        assert anywhere.data["is_checked_in"] is True


@pytest.mark.django_db
class TestFamilyListQueryCount:
    def _populate(self, n, staff, sessions):
        for i in range(n):
            family = Family.objects.create(last_name=f"F{i}")
            adult = Parent.objects.create(first_name="P", family=family)
            Parent.objects.create(first_name="Q", family=family)
            child = Child.objects.create(
                first_name="C", last_name="x", birthdate=date(2018, 1, 1), family=family
            )
            _check_in(adult, sessions["B children"], staff)
            _check_in(child, sessions["A"], staff)

    def _count(self, client, session):
        with CaptureQueriesContext(connection) as ctx:
            response = client.get(f"{FAMILIES_URL}?session={session.id}")
        assert response.status_code == 200
        return len(ctx)

    def test_query_count_does_not_grow_with_the_number_of_families(
        self, client, staff, sessions
    ):
        self._populate(1, staff, sessions)
        # Warm-up: the first request on a user also pays two permission queries
        # (memoised on the user object afterwards), which is not per-row cost.
        self._count(client, sessions["C"])
        one = self._count(client, sessions["C"])
        self._populate(5, staff, sessions)
        six = self._count(client, sessions["C"])

        assert six == one
