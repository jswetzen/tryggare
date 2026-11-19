"""build_form_spec / GET /api/registrations/events/<id>/: spec extras, the
spec-vs-submit contract, and the frontend JSON fixture."""

import json
import os
import uuid
from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal
from pathlib import Path
from unittest import skipUnless
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import AppliesTo, Event, Extra, ExtraChoice, Session, TicketType

from .form_spec import CHILD_FIELDS, PARENT_FIELDS, build_form_spec

# Not visible from the backend container (it only mounts ./backend); the
# fixture test runs on the host, see test_matches_frontend_fixture.
FIXTURE_PATH = (
    Path(settings.BASE_DIR).parent
    / "frontend/src/lib/registration/__fixtures__/form-spec.v1.json"
)


def _uid(n: int) -> uuid.UUID:
    return uuid.UUID(int=n)


def _utc(y, m, d, h=0):
    return datetime(y, m, d, h, tzinfo=dt_timezone.utc)


def make_fixture_event() -> Event:
    event = Event.objects.create(
        id=_uid(1),
        name="Fixture Camp",
        start_date=date(2030, 7, 1),
        end_date=date(2030, 7, 3),
        price=None,
        accent_color="#336699",
        registration_opens_at=_utc(2020, 1, 1),
        registration_closes_at=_utc(2099, 1, 1),
    )
    day1 = Session.objects.create(
        id=_uid(10),
        event=event,
        name="Day 1",
        start_time=_utc(2030, 7, 1, 9),
        end_time=_utc(2030, 7, 1, 16),
    )
    Session.objects.create(
        id=_uid(11),
        event=event,
        name="Day 2 (unreferenced)",
        start_time=_utc(2030, 7, 2, 9),
        end_time=_utc(2030, 7, 2, 16),
    )
    adult = TicketType.objects.create(
        id=_uid(20),
        event=event,
        name="Adult",
        price=Decimal("200.00"),
        applies_to=AppliesTo.PARENT,
        sort_order=1,
    )
    TicketType.objects.create(
        id=_uid(21),
        event=event,
        name="Child 0-12",
        price=Decimal("100.00"),
        applies_to=AppliesTo.CHILD,
        min_birthdate=date(2018, 7, 1),
        max_birthdate=date(2030, 7, 1),
        capacity=50,
        requires_ticket_type=adult,
        max_per_required=3,
        sort_order=2,
    )
    bundle = TicketType.objects.create(
        id=_uid(22),
        event=event,
        name="Day 1 only",
        price=Decimal("80.00"),
        kind=TicketType.Kind.SESSION_BUNDLE,
        sort_order=3,
    )
    bundle.sessions.add(day1)
    TicketType.objects.create(
        id=_uid(23),
        event=event,
        name="VIP",
        price=Decimal("500.00"),
        is_hidden=True,
        sort_order=4,
    )
    lunch = Extra.objects.create(
        id=_uid(30),
        event=event,
        session=day1,
        name="Lunch",
        price=Decimal("50.00"),
        requires_choice=True,
        required=True,
        sort_order=1,
    )
    ExtraChoice.objects.create(id=_uid(31), extra=lunch, label="Meat", sort_order=1)
    ExtraChoice.objects.create(
        id=_uid(32),
        extra=lunch,
        label="Veg",
        price_delta=Decimal("5.00"),
        sort_order=2,
    )
    ExtraChoice.objects.create(
        id=_uid(33), extra=lunch, label="Retired", sort_order=3, is_active=False
    )
    return event


def _open_event():
    today = timezone.now().date()
    return Event.objects.create(
        name="Open Camp",
        start_date=today,
        end_date=today,
        registration_opens_at=timezone.now() - timezone.timedelta(days=1),
    )


class FormSpecEndpointTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_spec_has_version_sessions_and_fields(self):
        event = make_fixture_event()
        response = self.client.get(f"/api/registrations/events/{event.id}/")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["spec_version"], 1)
        # Only the session an extra / visible bundle refers to.
        self.assertEqual([s["name"] for s in response.data["sessions"]], ["Day 1"])
        self.assertEqual(
            set(response.data["sessions"][0]),
            {"id", "name", "start_time", "end_time"},
        )
        self.assertEqual(set(response.data["fields"]), {"parent", "child"})
        for fields in response.data["fields"].values():
            for f in fields:
                self.assertEqual(set(f), {"key", "visible", "required"})

    def test_response_is_not_cacheable(self):
        event = _open_event()
        response = self.client.get(f"/api/registrations/events/{event.id}/")
        self.assertEqual(response["Cache-Control"], "no-store")

    def test_sessions_empty_without_references(self):
        spec = build_form_spec(_open_event())
        self.assertEqual(spec["sessions"], [])


class FormSpecMatchesSubmitTests(TestCase):
    """The spec's required flags must agree with what submit enforces."""

    url = "/api/registrations/"

    def setUp(self):
        self.client = APIClient()
        self.event = _open_event()
        self.spec = build_form_spec(self.event)

    def _person_full(self, kind):
        if kind == "parent":
            return {
                "first_name": "Anna",
                "last_name": "Andersson",
                "phone": "070-123 45 67",
                "email": "anna@example.com",
                "relationship_type": "Mother",
                "allergies": "",
                "notes": "",
                "health_consent_status": "not_applicable",
            }
        return {
            "first_name": "Kim",
            "last_name": "Andersson",
            "birthdate": "2018-01-01",
            "allergies": "",
            "notes": "",
            "health_consent_status": "not_applicable",
        }

    def _payload(self, kind, drop=None):
        parent = self._person_full("parent")
        child = self._person_full("child")
        target = parent if kind == "parent" else child
        if drop:
            del target[drop]
        # Unique per call: a repeat email is deduped to a 200 "already pending".
        self._n = getattr(self, "_n", 0) + 1
        return {
            "event": str(self.event.id),
            "contact_email": f"guardian{self._n}@example.com",
            "parents": [parent],
            "children": [child],
        }

    def test_declared_fields_are_exactly_the_payload_fields(self):
        for kind, declared in (("parent", PARENT_FIELDS), ("child", CHILD_FIELDS)):
            self.assertEqual(
                [f["key"] for f in declared],
                list(self._person_full(kind)),
                kind,
            )

    @patch("registrations.views.send_verification_email", return_value=True)
    def test_required_flag_matches_server(self, _mock_send):
        self.assertEqual(
            self.client.post(
                self.url, self._payload("parent"), format="json"
            ).status_code,
            201,
        )
        for kind in ("parent", "child"):
            for field in self.spec["fields"][kind]:
                with self.subTest(kind=kind, field=field["key"]):
                    # Otherwise-valid payload: only `field` can matter.
                    response = self.client.post(
                        self.url,
                        self._payload(kind, drop=field["key"]),
                        format="json",
                    )
                    expected = 400 if field["required"] else 201
                    self.assertEqual(response.status_code, expected, response.data)


@skipUnless(
    FIXTURE_PATH.parent.is_dir() or os.environ.get("UPDATE_FORM_SPEC_FIXTURE"),
    "frontend/ is not mounted here (backend container); run from the host: "
    "cd backend && uv run python manage.py test registrations.tests_form_spec",
)
class FormSpecFixtureTests(TestCase):
    def test_matches_frontend_fixture(self):
        spec = build_form_spec(make_fixture_event())
        # Round-trip so comparison is on JSON types, as the frontend sees it.
        spec = json.loads(json.dumps(spec))
        if os.environ.get("UPDATE_FORM_SPEC_FIXTURE") == "1":
            FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
            FIXTURE_PATH.write_text(
                json.dumps(spec, indent=2, ensure_ascii=False) + "\n"
            )
        expected = json.loads(FIXTURE_PATH.read_text())
        self.assertEqual(
            spec,
            expected,
            "form spec changed; regenerate with UPDATE_FORM_SPEC_FIXTURE=1 "
            "(see test docstring) and commit the fixture",
        )
