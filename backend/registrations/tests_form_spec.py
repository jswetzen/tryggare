"""build_form_spec / GET /api/registrations/events/<id>/: spec extras, the
spec-vs-submit contract, and the frontend JSON fixture."""

import json
import os
import uuid
from datetime import date, datetime, timezone as dt_timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import (
    AppliesTo,
    Event,
    Extra,
    ExtraChoice,
    PromoCode,
    Session,
    TicketType,
)

from .form_spec import (
    CHILD_FIELDS,
    FORM_ONLY_REQUIRED,
    PARENT_FIELDS,
    build_form_spec,
)
from .serializers import RegistrationChildSerializer, RegistrationParentSerializer

# docker-compose.yml mounts the fixture dir into the web container at
# /frontend/...; on the host it is the repo's frontend/ directory.
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
    """The spec's required flags (= what the form requires) must agree with
    the server, except the declared FORM_ONLY_REQUIRED fields."""

    url = "/api/registrations/"
    # What the page posts for an empty field. health_consent_status is never
    # empty on the page (it maps to a status), so its "blank" is the default.
    BLANK = {"health_consent_status": "not_applicable", "birthdate": None}

    def setUp(self):
        self.client = APIClient()
        self.event = _open_event()
        self.spec = build_form_spec(self.event)
        self._n = 0

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

    def _post(self, kind, key=None, mode=None, value=None):
        """Post an otherwise valid registration with one field blanked
        (mode "blank"), omitted ("missing") or set to `value`."""
        persons = {k: self._person_full(k) for k in ("parent", "child")}
        if mode == "blank":
            persons[kind][key] = self.BLANK.get(key, "")
        elif mode == "missing":
            del persons[kind][key]
        elif mode == "value":
            persons[kind][key] = value
        # Unique per call: a repeat email is deduped to a 200 "already pending".
        self._n += 1
        with patch("registrations.views.send_verification_email", return_value=True):
            return self.client.post(
                self.url,
                {
                    "event": str(self.event.id),
                    "contact_email": f"guardian{self._n}@example.com",
                    "parents": [persons["parent"]],
                    "children": [persons["child"]],
                },
                format="json",
            )

    @staticmethod
    def _errors(response, kind):
        group = response.data["parents" if kind == "parent" else "children"]
        return group[0]

    def test_declared_fields_are_the_serializers_fields(self):
        extra = {"id", "ticket_type", "extras", "guardian_only"}
        for kind, declared, serializer in (
            ("parent", PARENT_FIELDS, RegistrationParentSerializer),
            ("child", CHILD_FIELDS, RegistrationChildSerializer),
        ):
            self.assertEqual(
                [f["key"] for f in declared],
                [f for f in serializer.Meta.fields if f not in extra],
                kind,
            )
        for kind in ("parent", "child"):
            self.assertEqual(
                list(self._person_full(kind)),
                [f["key"] for f in self.spec["fields"][kind]],
            )

    def test_required_flag_matches_server(self):
        self.assertEqual(self._post("parent").status_code, 201)
        for kind in ("parent", "child"):
            for field in self.spec["fields"][kind]:
                key = field["key"]
                form_only = (kind, key) in FORM_ONLY_REQUIRED
                for mode in ("blank", "missing"):
                    with self.subTest(kind=kind, field=key, mode=mode):
                        response = self._post(kind, key, mode)
                        if response.status_code == 400:
                            self.assertIn(key, self._errors(response, kind))
                            self.assertTrue(
                                field["required"] and not form_only,
                                f"server rejects {kind}.{key} but spec says "
                                "optional or form-only",
                            )
                        else:
                            self.assertEqual(response.status_code, 201)
                            self.assertTrue(
                                not field["required"] or form_only,
                                f"server accepts {kind}.{key} blank but it is "
                                "not in FORM_ONLY_REQUIRED",
                            )

    def test_form_only_fields_are_required_in_spec(self):
        for kind, key in FORM_ONLY_REQUIRED:
            field = next(f for f in self.spec["fields"][kind] if f["key"] == key)
            self.assertTrue(field["required"], (kind, key))

    def test_empty_string_birthdate_is_rejected_by_server(self):
        # The page currently posts "" for an empty date; the server wants null.
        response = self._post("child", "birthdate", "value", "")
        self.assertEqual(response.status_code, 400)
        self.assertIn("birthdate", self._errors(response, "child"))


class FormSpecFixtureTests(TestCase):
    def test_matches_frontend_fixture(self):
        self.assertTrue(
            FIXTURE_PATH.parent.is_dir(),
            f"{FIXTURE_PATH.parent} missing: recreate the dev stack so the "
            "web service picks up the docker-compose.yml fixture mount",
        )
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


class PromoUnlockedSessionsTests(TestCase):
    def test_unlocked_bundle_type_carries_session_ids_and_sessions(self):
        event = make_fixture_event()
        day1 = Session.objects.get(id=_uid(10))
        vip_day = TicketType.objects.create(
            event=event,
            name="VIP day",
            price=Decimal("0"),
            kind=TicketType.Kind.SESSION_BUNDLE,
            is_hidden=True,
        )
        vip_day.sessions.add(day1)
        promo = PromoCode.objects.create(
            event=event,
            code="VIPDAY",
            discount_type=PromoCode.DiscountType.FIXED,
            discount_value=Decimal("0"),
        )
        promo.unlocks_ticket_types.add(vip_day)

        # event, promo lookup, applies_to ids, unlocked types, 2 sold-count
        # aggregates, bundle session rows, sessions.
        with self.assertNumQueries(8):
            response = APIClient().post(
                "/api/registrations/validate-promo-code/",
                {"event": str(event.id), "code": "VIPDAY"},
                format="json",
            )

        self.assertEqual(response.status_code, 200, response.data)
        unlocked = response.data["unlocks_ticket_types"][0]
        self.assertEqual(unlocked["session_ids"], [str(day1.id)])
        self.assertEqual([s["id"] for s in response.data["sessions"]], [str(day1.id)])
