"""Event spec REST API and manage.py command: permissions, happy paths, error shapes."""

import copy
import json
import os
import tempfile
from datetime import UTC, date, datetime
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import AdminUser
from events.event_spec import example_spec, export
from events.models import Event, EventTicket, Session, TicketType
from events.services import COPY_PERMISSIONS
from families.models import Child, Family

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)


def at_now():
    return patch("events.models.timezone.now", return_value=NOW)


def add_ticket(event):
    child = Child.objects.create(
        family=Family.objects.create(),
        first_name="T",
        last_name="C",
        birthdate=date(2020, 1, 1),
    )
    EventTicket.objects.create(attendee=child, event=event)


def make_event(spec=None):
    from events.event_spec import apply

    with at_now():
        return apply(spec or example_spec())[0]


class ApiTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = AdminUser.objects.create_superuser("specstaff", "pw12345")
        cls.plain = AdminUser.objects.create_user("specplain", "pw12345")
        cls.partial = AdminUser.objects.create_user("specpartial", "pw12345")
        cls.partial.user_permissions.add(
            Permission.objects.get(
                content_type__app_label="events", codename="add_event"
            )
        )

    def client_for(self, user=None):
        client = APIClient()
        if user:
            client.force_login(user)
        return client

    def as_staff(self):
        return self.client_for(self.staff)

    def post(self, client, url, body):
        with at_now():
            return client.post(url, body, format="json")


ENDPOINTS = [
    ("get", "event-spec-schema", False),
    ("post", "event-spec-validate", False),
    ("post", "event-spec-create", False),
    ("get", "event-spec", True),
    ("post", "event-spec-diff", True),
    ("put", "event-spec", True),
]


class PermissionTests(ApiTestCase):
    def test_copy_permissions_are_the_five_add_perms(self):
        self.assertEqual(len(COPY_PERMISSIONS), 5)

    def test_nobody_below_the_copy_rule_gets_in(self):
        event = make_event()
        for user, expected in ((None, 403), (self.plain, 403), (self.partial, 403)):
            client = self.client_for(user)
            for method, name, with_id in ENDPOINTS:
                url = reverse(name, args=[event.pk] if with_id else [])
                response = getattr(client, method)(
                    url, {"spec": example_spec()}, format="json"
                )
                self.assertEqual(response.status_code, expected, (user, method, name))

    def test_staff_gets_in_everywhere(self):
        event = make_event()
        client = self.as_staff()
        for method, name, with_id in ENDPOINTS:
            url = reverse(name, args=[event.pk] if with_id else [])
            response = getattr(client, method)(
                url, {"spec": example_spec()}, format="json"
            )
            self.assertNotIn(response.status_code, (401, 403), (method, name))


class SchemaAndValidateTests(ApiTestCase):
    def test_schema(self):
        response = self.as_staff().get(reverse("event-spec-schema"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"schema", "capabilities", "example"})
        self.assertEqual(response.json()["example"], example_spec())

    def test_validate_valid(self):
        response = self.post(
            self.as_staff(), reverse("event-spec-validate"), {"spec": example_spec()}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["valid"], True)
        self.assertEqual(response.json()["errors"], [])

    def test_validate_invalid_spec_is_still_200(self):
        spec = example_spec()
        spec["event"]["end_date"] = "2000-01-01"
        response = self.post(
            self.as_staff(), reverse("event-spec-validate"), {"spec": spec}
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertFalse(body["valid"])
        self.assertEqual(set(body["errors"][0]), {"path", "code", "message"})

    def test_validate_against_event(self):
        event = make_event()
        add_ticket(event)
        response = self.post(
            self.as_staff(),
            reverse("event-spec-validate"),
            {"spec": example_spec(), "event_id": str(event.pk)},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["errors"][0]["code"], "event_not_empty")
        self.assertFalse(response.json()["valid"])

    def test_validate_unknown_and_malformed_event_id(self):
        client = self.as_staff()
        url = reverse("event-spec-validate")
        missing = self.post(
            client,
            url,
            {
                "spec": example_spec(),
                "event_id": "00000000-0000-0000-0000-000000000000",
            },
        )
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["errors"][0]["code"], "event_not_found")
        bad = self.post(client, url, {"spec": example_spec(), "event_id": "nope"})
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(bad.json()["errors"][0]["code"], "invalid_event_id")


class MalformedBodyTests(ApiTestCase):
    def assert_shape(self, response, code):
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(body["warnings"], [])
        self.assertEqual(set(body["errors"][0]), {"path", "code", "message"})
        self.assertEqual(body["errors"][0]["code"], code)

    def test_every_body_endpoint(self):
        event = make_event()
        client = self.as_staff()
        targets = [
            ("post", reverse("event-spec-validate")),
            ("post", reverse("event-spec-create")),
            ("post", reverse("event-spec-diff", args=[event.pk])),
            ("put", reverse("event-spec", args=[event.pk])),
        ]
        for method, url in targets:
            call = getattr(client, method)
            self.assert_shape(
                call(url, "{not json", content_type="application/json"),
                "malformed_body",
            )
            self.assert_shape(
                call(url, "text", content_type="text/plain"), "malformed_body"
            )
            self.assert_shape(
                call(url, "[1]", content_type="application/json"), "malformed_body"
            )
            self.assert_shape(call(url, {}, format="json"), "spec_missing")
            self.assert_shape(call(url, {"spec": "x"}, format="json"), "spec_missing")


class CreateTests(ApiTestCase):
    def test_create(self):
        before = Event.objects.count()
        response = self.post(
            self.as_staff(), reverse("event-spec-create"), {"spec": example_spec()}
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(set(body), {"event_id", "diff", "warnings"})
        self.assertEqual(Event.objects.count(), before + 1)
        self.assertEqual(
            export(Event.objects.get(pk=body["event_id"])).get("sessions"),
            export(make_event()).get("sessions"),
        )
        self.assertTrue(all(c["change"] == "added" for c in body["diff"]))

    def test_create_invalid_writes_nothing(self):
        spec = example_spec()
        spec["ticket_types"][0]["sessions"] = ["no-such-session"]
        response = self.post(
            self.as_staff(), reverse("event-spec-create"), {"spec": spec}
        )
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertEqual(set(body), {"errors", "warnings"})
        self.assertTrue(body["errors"])
        self.assertEqual(Event.objects.count(), 0)


class EventSpecTests(ApiTestCase):
    def test_export(self):
        event = make_event()
        response = self.as_staff().get(reverse("event-spec", args=[event.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), json.loads(json.dumps(export(event))))

    def test_export_unknown_event(self):
        response = self.as_staff().get(
            reverse("event-spec", args=["00000000-0000-0000-0000-000000000000"])
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["errors"][0]["code"], "event_not_found")

    def test_export_cross_event_reference_is_409(self):
        a = make_event()
        other = Event.objects.create(
            name="Other", start_date=date(2027, 1, 1), end_date=date(2027, 1, 2)
        )
        foreign = Session.objects.create(
            event=other,
            name="Foreign",
            start_time=datetime(2027, 1, 1, 9, tzinfo=UTC),
            end_time=datetime(2027, 1, 1, 10, tzinfo=UTC),
        )
        a.ticket_types.first().sessions.add(foreign)
        response = self.as_staff().get(reverse("event-spec", args=[a.pk]))
        self.assertEqual(response.status_code, 409)
        error = response.json()["errors"][0]
        self.assertEqual(error["code"], "cross_event_reference")
        self.assertIn("Foreign", error["message"])

    def test_diff_writes_nothing(self):
        event = make_event()
        spec = export(event)
        spec["event"]["name"] = "Renamed"
        before = Event.objects.get(pk=event.pk).name
        response = self.post(
            self.as_staff(),
            reverse("event-spec-diff", args=[event.pk]),
            {"spec": json.loads(json.dumps(spec))},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body), {"diff", "errors", "warnings"})
        self.assertEqual(
            [c["change"] for c in body["diff"] if c["kind"] == "event"], ["changed"]
        )
        self.assertEqual(Event.objects.get(pk=event.pk).name, before)

    def test_diff_wrong_shape_reports_errors(self):
        event = make_event()
        response = self.post(
            self.as_staff(),
            reverse("event-spec-diff", args=[event.pk]),
            {"spec": {"event": {}}},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["diff"], [])
        self.assertTrue(response.json()["errors"])

    def test_diff_dangling_reference_does_not_500(self):
        event = make_event()
        spec = copy.deepcopy(example_spec())
        spec["ticket_types"][0]["sessions"] = ["no-such-session"]
        response = self.post(
            self.as_staff(), reverse("event-spec-diff", args=[event.pk]), {"spec": spec}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["errors"])

    def test_diff_unknown_event(self):
        response = self.post(
            self.as_staff(),
            reverse("event-spec-diff", args=["00000000-0000-0000-0000-000000000000"]),
            {"spec": example_spec()},
        )
        self.assertEqual(response.status_code, 404)

    def test_put_onto_empty_event(self):
        target = Event.objects.create(
            name="Empty", start_date=date(2027, 5, 1), end_date=date(2027, 5, 2)
        )
        client = self.as_staff()
        with at_now():
            response = client.put(
                reverse("event-spec", args=[target.pk]),
                {"spec": example_spec()},
                format="json",
            )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["event_id"], str(target.pk))
        self.assertEqual(set(body), {"event_id", "diff", "warnings"})
        self.assertTrue(target.sessions.exists())

    def test_put_onto_event_with_tickets_is_409(self):
        event = make_event()
        add_ticket(event)
        client = self.as_staff()
        with at_now():
            response = client.put(
                reverse("event-spec", args=[event.pk]),
                {"spec": example_spec()},
                format="json",
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["errors"][0]["code"], "event_not_empty")

    def test_put_invalid_spec_is_400(self):
        target = Event.objects.create(
            name="Empty", start_date=date(2027, 5, 1), end_date=date(2027, 5, 2)
        )
        spec = example_spec()
        spec["event"]["end_date"] = "2000-01-01"
        client = self.as_staff()
        with at_now():
            response = client.put(
                reverse("event-spec", args=[target.pk]), {"spec": spec}, format="json"
            )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(target.sessions.exists())

    def test_put_unknown_event(self):
        response = self.as_staff().put(
            reverse("event-spec", args=["00000000-0000-0000-0000-000000000000"]),
            {"spec": example_spec()},
            format="json",
        )
        self.assertEqual(response.status_code, 404)


class CommandTests(TestCase):
    def run_cmd(self, *args):
        out, err = StringIO(), StringIO()
        with at_now():
            call_command("event_spec", *args, stdout=out, stderr=err)
        return out.getvalue(), err.getvalue()

    def spec_file(self, spec):
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w") as f:
            json.dump(spec, f)
        self.addCleanup(os.unlink, path)
        return path

    def test_export_stdout_and_file(self):
        event = make_event()
        out, _ = self.run_cmd("export", "--event", str(event.pk))
        self.assertEqual(json.loads(out), json.loads(json.dumps(export(event))))
        path = self.spec_file({})
        self.run_cmd("export", "--event", str(event.pk), "-o", path)
        with open(path) as f:
            self.assertEqual(json.load(f), json.loads(out))

    def test_export_unknown_event(self):
        with self.assertRaises(CommandError):
            self.run_cmd("export", "--event", "00000000-0000-0000-0000-000000000000")
        with self.assertRaises(CommandError):
            self.run_cmd("export", "--event", "not-a-uuid")

    def test_validate_ok(self):
        out, err = self.run_cmd("validate", self.spec_file(example_spec()))
        self.assertTrue(json.loads(out)["valid"])
        self.assertEqual(err, "")

    def test_validate_errors_are_readable_and_fail(self):
        spec = example_spec()
        spec["event"]["end_date"] = "2000-01-01"
        out, err = StringIO(), StringIO()
        with self.assertRaises(CommandError):
            with at_now():
                call_command(
                    "event_spec",
                    "validate",
                    self.spec_file(spec),
                    stdout=out,
                    stderr=err,
                )
        self.assertIn("error: event", err.getvalue())
        self.assertIn("[end_before_start]", err.getvalue())
        self.assertFalse(json.loads(out.getvalue())["valid"])

    def test_validate_against_event(self):
        event = make_event()
        add_ticket(event)
        with self.assertRaises(CommandError):
            self.run_cmd(
                "validate", self.spec_file(example_spec()), "--event", str(event.pk)
            )

    def test_unreadable_and_non_json_file(self):
        with self.assertRaises(CommandError):
            self.run_cmd("validate", "/nonexistent/spec.json")
        path = self.spec_file({})
        with open(path, "w") as f:
            f.write("{nope")
        with self.assertRaises(CommandError):
            self.run_cmd("validate", path)

    def test_diff_writes_nothing(self):
        event = make_event()
        spec = json.loads(json.dumps(export(event)))
        spec["event"]["name"] = "Renamed"
        out, _ = self.run_cmd("diff", self.spec_file(spec), "--event", str(event.pk))
        self.assertEqual(
            [c["change"] for c in json.loads(out)["diff"] if c["kind"] == "event"],
            ["changed"],
        )
        self.assertNotEqual(Event.objects.get(pk=event.pk).name, "Renamed")

    def test_diff_requires_event(self):
        with self.assertRaises(CommandError):
            self.run_cmd("diff", self.spec_file(example_spec()))

    def test_apply_creates_event(self):
        out, _ = self.run_cmd("apply", self.spec_file(example_spec()))
        event = Event.objects.get(pk=json.loads(out)["event_id"])
        self.assertTrue(event.sessions.exists())

    def test_apply_dry_run_writes_nothing(self):
        out, _ = self.run_cmd("apply", self.spec_file(example_spec()), "--dry-run")
        body = json.loads(out)
        self.assertTrue(body["dry_run"])
        self.assertTrue(body["diff"])
        self.assertEqual(Event.objects.count(), 0)

    def test_apply_onto_empty_event(self):
        target = Event.objects.create(
            name="Empty", start_date=date(2027, 5, 1), end_date=date(2027, 5, 2)
        )
        out, _ = self.run_cmd(
            "apply", self.spec_file(example_spec()), "--event", str(target.pk)
        )
        self.assertEqual(json.loads(out)["event_id"], str(target.pk))
        self.assertTrue(target.sessions.exists())

    def test_apply_error_exits_nonzero_and_writes_nothing(self):
        spec = example_spec()
        spec["ticket_types"][0]["sessions"] = ["no-such-session"]
        path = self.spec_file(spec)
        for extra in ((), ("--dry-run",)):
            with self.assertRaises(CommandError):
                self.run_cmd("apply", path, *extra)
        self.assertEqual(Event.objects.count(), 0)
        self.assertEqual(TicketType.objects.count(), 0)
