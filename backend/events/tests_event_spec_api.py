"""Event spec REST API and manage.py command: permissions, happy paths, error shapes."""

import json
import os
import tempfile
from datetime import UTC, date, datetime
from io import StringIO

from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import AdminUser
from families.models import Family
from registrations.models import Registration, RegistrationExtra
from events.event_spec import apply, check_setup, example_spec, export
from events.spec_test_support import (
    add_ticket,
    example_with_bundle,
    at_now,
    empty_event,
    foreign_session,
    make_child,
)
from events.management.commands.event_spec import Command
from events.models import Event, EventTicket, Extra, PromoCode, TicketType
from accounts.roles import COORDINATOR, grant
from events.services import COPY_PERMISSIONS, VIEW_PERMISSIONS


def foreign_session_event():
    """An otherwise empty event whose ticket type includes another event's session."""
    target = empty_event("Target")
    ticket_type = TicketType.objects.create(
        event=target, name="T", price=0, kind="session_bundle"
    )
    ticket_type.sessions.add(foreign_session())
    return target


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
    def user_with(self, name, labels):
        user = AdminUser.objects.create_user(name, "pw12345")
        for label in labels:
            app, codename = label.split(".")
            user.user_permissions.add(
                Permission.objects.get(content_type__app_label=app, codename=codename)
            )
        return user

    def test_create_only_user_cannot_put(self):
        target = empty_event("Empty")
        client = self.client_for(self.user_with("creator", COPY_PERMISSIONS))
        created = self.post(
            client, reverse("event-spec-create"), {"spec": example_spec()}
        )
        self.assertEqual(created.status_code, 201)
        with at_now():
            response = client.put(
                reverse("event-spec", args=[target.pk]),
                {"spec": example_spec()},
                format="json",
            )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(target.sessions.exists())

    def test_export_needs_view_promocode(self):
        event = make_event()
        labels = [p for p in VIEW_PERMISSIONS if not p.endswith("promocode")]
        client = self.client_for(self.user_with("noview", labels))
        for method, name, with_id in ENDPOINTS[:3] + ENDPOINTS[3:5]:
            if method == "post" and name == "event-spec-create":
                continue
            url = reverse(name, args=[event.pk] if with_id else [])
            response = getattr(client, method)(
                url, {"spec": example_spec()}, format="json"
            )
            self.assertEqual(response.status_code, 403, name)

    def test_put_needs_csrf_with_session_auth(self):
        target = empty_event("Empty")
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.staff)
        response = client.put(
            reverse("event-spec", args=[target.pk]),
            {"spec": example_spec()},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(target.sessions.exists())

    def test_refusals_use_the_error_shape(self):
        response = self.client_for(self.plain).get(reverse("event-spec-schema"))
        self.assertEqual(response.status_code, 403)
        body = response.json()
        self.assertEqual(body["warnings"], [])
        self.assertEqual(set(body["errors"][0]), {"path", "code", "message"})
        self.assertEqual(body["errors"][0]["code"], "permission_denied")

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

    def test_staff_and_coordinators_get_in_everywhere(self):
        event = make_event()
        coordinator = grant(
            AdminUser.objects.create_user("coord", "pw12345"), COORDINATOR
        )
        for user in (self.staff, coordinator):
            client = self.client_for(user)
            for method, name, with_id in ENDPOINTS:
                url = reverse(name, args=[event.pk] if with_id else [])
                response = getattr(client, method)(
                    url, {"spec": example_spec()}, format="json"
                )
                self.assertNotIn(response.status_code, (401, 403), (user, method, name))


class SchemaAndValidateTests(ApiTestCase):
    def test_schema(self):
        response = self.as_staff().get(reverse("event-spec-schema"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"schema", "capabilities", "example"})
        self.assertEqual(response.json()["example"], example_spec())

    def test_validate_is_200_whether_or_not_the_spec_is_valid(self):
        invalid = example_spec()
        invalid["event"]["end_date"] = "2000-01-01"
        for spec, valid in ((example_spec(), True), (invalid, False)):
            response = self.post(
                self.as_staff(), reverse("event-spec-validate"), {"spec": spec}
            )
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body["valid"], valid)
            self.assertEqual(bool(body["errors"]), not valid)
            for error in body["errors"]:
                self.assertEqual(set(error), {"path", "code", "message"})

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

    def test_unknown_or_malformed_event_id_is_404_in_the_error_shape(self):
        client = self.as_staff()
        calls = (
            client.get,
            lambda url: client.put(url, {"spec": example_spec()}, format="json"),
            lambda url: client.post(url, {"spec": example_spec()}, format="json"),
        )
        urls = (
            "/api/events/%s/spec/",
            "/api/events/%s/spec/",
            "/api/events/%s/spec/diff/",
        )
        for call, template in zip(calls, urls):
            for event_id in ("00000000-0000-0000-0000-000000000000", "not-a-uuid"):
                response = call(template % event_id)
                self.assertEqual(response.status_code, 404, (template, event_id))
                self.assertEqual(
                    response.json()["errors"][0]["code"], "event_not_found"
                )

    def test_export_cross_event_reference_is_409(self):
        a = make_event()
        a.ticket_types.first().sessions.add(foreign_session())
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
        self.assertEqual(set(body), {"valid", "diff", "errors", "warnings"})
        self.assertEqual(
            [c["change"] for c in body["diff"] if c["kind"] == "event"], ["changed"]
        )
        self.assertEqual(Event.objects.get(pk=event.pk).name, before)

    def test_diff_reports_validity_and_never_500s(self):
        event = make_event()
        url = reverse("event-spec-diff", args=[event.pk])
        dangling = example_spec()
        dangling["ticket_types"][0]["sessions"] = ["no-such-session"]
        foreign = foreign_session_event()
        cases = (
            # url, spec, valid; a wrong shape has no diff, the errors say where.
            (url, json.loads(json.dumps(export(event))), True),
            (url, {"event": {}}, False),
            (url, dangling, False),
            (reverse("event-spec-diff", args=[foreign.pk]), example_spec(), False),
        )
        for case_url, spec, valid in cases:
            response = self.post(self.as_staff(), case_url, {"spec": spec})
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual(body["valid"], valid)
            self.assertEqual(bool(body["errors"]), not valid)
            if case_url != url:
                self.assertIn(
                    "cross_event_reference", [e["code"] for e in body["errors"]]
                )
            if spec == {"event": {}} or case_url != url:
                self.assertEqual(body["diff"], [])

    def test_put_onto_empty_event(self):
        target = empty_event("Empty")
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

    def test_put_invalid_spec_is_400(self):
        target = empty_event("Empty")
        spec = example_spec()
        spec["event"]["end_date"] = "2000-01-01"
        client = self.as_staff()
        with at_now():
            response = client.put(
                reverse("event-spec", args=[target.pk]), {"spec": spec}, format="json"
            )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(target.sessions.exists())

    def test_bare_spec_body_is_accepted(self):
        client = self.as_staff()
        created = self.post(client, reverse("event-spec-create"), example_spec())
        self.assertEqual(created.status_code, 201)
        target = empty_event("Empty")
        with at_now():
            response = client.put(
                reverse("event-spec", args=[target.pk]), example_spec(), format="json"
            )
        self.assertEqual(response.status_code, 200)

    def test_put_refusals_that_describe_the_target_are_409(self):
        def with_tickets():
            event = make_event()
            add_ticket(event)
            return event

        cases = (
            (with_tickets, "event_not_empty"),
            (
                lambda: empty_event(
                    "Open", registration_opens_at=datetime(2026, 11, 1, tzinfo=UTC)
                ),
                "registration_open_on_target",
            ),
            (foreign_session_event, "cross_event_reference"),
        )
        for make_target, code in cases:
            target = make_target()
            with self.subTest(code), at_now():
                response = self.as_staff().put(
                    reverse("event-spec", args=[target.pk]),
                    {"spec": example_spec()},
                    format="json",
                )
            self.assertEqual(response.status_code, 409, code)
            self.assertEqual(response.json()["errors"][0]["code"], code)

    def test_spec_size_is_capped(self):
        spec = example_spec()
        spec["sessions"] = [spec["sessions"][0]] * 301
        response = self.post(
            self.as_staff(), reverse("event-spec-validate"), {"spec": spec}
        )
        self.assertFalse(response.json()["valid"])


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

    def test_validate_ok(self):
        out, err = self.run_cmd("validate", self.spec_file(example_spec()))
        self.assertTrue(json.loads(out)["valid"])
        self.assertEqual(json.loads(out)["warnings"], [])

    def test_validate_against_event(self):
        event = make_event()
        add_ticket(event)
        with self.assertRaises(CommandError):
            self.run_cmd(
                "validate", self.spec_file(example_spec()), "--event", str(event.pk)
            )

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
        target = empty_event("Empty")
        out, _ = self.run_cmd(
            "apply", self.spec_file(example_spec()), "--event", str(target.pk)
        )
        self.assertEqual(json.loads(out)["event_id"], str(target.pk))
        self.assertTrue(target.sessions.exists())

    def test_cross_event_reference_is_a_command_error(self):
        target = foreign_session_event()
        path = self.spec_file(example_spec())
        for extra in ((), ("--dry-run",)):
            out, err = StringIO(), StringIO()
            with self.assertRaises(CommandError) as ctx:
                with at_now():
                    call_command(
                        "event_spec",
                        "apply",
                        path,
                        "--event",
                        str(target.pk),
                        *extra,
                        stdout=out,
                        stderr=err,
                    )
            self.assertEqual(ctx.exception.returncode, 1)
            codes = [e["code"] for e in json.loads(out.getvalue())["errors"]]
            self.assertIn("cross_event_reference", codes)

    def test_export_cross_event_reference_is_a_command_error(self):
        target = foreign_session_event()
        out, err = StringIO(), StringIO()
        with self.assertRaises(CommandError) as ctx:
            call_command(
                "event_spec",
                "export",
                "--event",
                str(target.pk),
                stdout=out,
                stderr=err,
            )
        self.assertEqual(ctx.exception.returncode, 1)
        self.assertIn("[cross_event_reference]", err.getvalue())
        self.assertEqual(out.getvalue(), "")
        self.assertNotIn("The spec was refused", str(ctx.exception))

    def test_exit_codes(self):
        # 1: the spec was refused; the issues are readable on stderr, JSON on stdout.
        spec = example_spec()
        spec["event"]["end_date"] = "2000-01-01"
        out, err = StringIO(), StringIO()
        with self.assertRaises(CommandError) as ctx:
            with at_now():
                call_command(
                    "event_spec",
                    "validate",
                    self.spec_file(spec),
                    stdout=out,
                    stderr=err,
                )
        self.assertEqual(ctx.exception.returncode, 1)
        self.assertIn("error: event", err.getvalue())
        self.assertIn("[end_before_start]", err.getvalue())
        self.assertFalse(json.loads(out.getvalue())["valid"])
        # 2: the input could not be read or the event does not exist.
        not_json = self.spec_file({})
        with open(not_json, "w") as f:
            f.write("{nope")
        for args in (
            ("validate", "/nonexistent/spec.json"),
            ("validate", not_json),
            ("export", "--event", "not-a-uuid"),
            ("export", "--event", "00000000-0000-0000-0000-000000000000"),
            ("export", "--event", str(make_event().pk), "-o", "/nonexistent/x.json"),
        ):
            with self.assertRaises(CommandError) as ctx:
                self.run_cmd(*args)
            self.assertEqual(ctx.exception.returncode, 2, args)

    def test_spec_from_stdin(self):
        command = Command()
        command.stdin = StringIO(json.dumps(example_spec()))
        out = StringIO()
        with at_now():
            call_command(command, "apply", "-", "--dry-run", stdout=out)
        self.assertTrue(json.loads(out.getvalue())["dry_run"])

    def test_apply_error_exits_nonzero_and_writes_nothing(self):
        spec = example_spec()
        spec["ticket_types"][0]["sessions"] = ["no-such-session"]
        path = self.spec_file(spec)
        for extra in ((), ("--dry-run",)):
            with self.assertRaises(CommandError):
                self.run_cmd("apply", path, *extra)
        self.assertEqual(Event.objects.count(), 0)
        self.assertEqual(TicketType.objects.count(), 0)


class SetupCheckTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        with at_now():
            cls.event, _, _ = apply(example_with_bundle())
        cls.user = AdminUser.objects.create_superuser("checker", "pw12345")
        cls.plain = AdminUser.objects.create_user("plain", "pw12345", is_staff=True)

    def check(self, event=None):
        with at_now():
            return check_setup(event or self.event)

    def run_check(self):
        out, err = StringIO(), StringIO()
        with at_now():
            call_command(
                "event_spec",
                "check",
                "--event",
                str(self.event.pk),
                stdout=out,
                stderr=err,
            )
        return out.getvalue(), err.getvalue()

    def test_command_labels_rows_and_skips_guards(self):
        add_ticket(self.event)  # event_not_empty is an apply guard, not a setup problem
        with at_now(), self.assertRaises(CommandError) as ctx:
            call_command("event_spec", "check", "--event", "nope", stdout=StringIO())
        self.assertEqual(ctx.exception.returncode, 2)
        out, err = self.run_check()
        result = json.loads(out)
        self.assertEqual(result["errors"], [])
        rows = {w["code"]: w["row"] for w in result["warnings"]}
        self.assertEqual(
            rows["bundle_replaces_pass"], "Ticket type 'Saturday workshop 13-17'"
        )
        self.assertIn("[bundle_replaces_pass]", err)

    def test_open_registration_is_not_an_error(self):
        # registration_open and registration_open_on_target are apply guards.
        self.event.registration_opens_at = datetime(2026, 1, 1, tzinfo=UTC)
        self.event.save()
        result = self.check()
        self.assertEqual(result["errors"], [])
        codes = {w["code"] for w in result["warnings"]}
        self.assertFalse(codes & {"registration_open", "registration_open_on_target"})

    def test_tied_ordering_is_a_warning(self):
        TicketType.objects.filter(event=self.event).update(sort_order=0, name="Same")
        result = self.check()
        self.assertEqual(result["errors"], [])
        self.assertIn("ambiguous_order", {w["code"] for w in result["warnings"]})

    def test_command_exits_non_zero_on_errors(self):
        TicketType.objects.filter(event=self.event).update(
            requires_ticket_type=None, min_birthdate=date(2014, 6, 1)
        )
        err = StringIO()
        with at_now(), self.assertRaises(CommandError):
            call_command(
                "event_spec",
                "check",
                "--event",
                str(self.event.pk),
                stdout=StringIO(),
                stderr=err,
            )
        self.assertIn("[age_window]", err.getvalue())

    def test_rows_with_history_are_not_called_deletable(self):
        retired = TicketType.objects.get(event=self.event, name="Child pass 0-12")
        unused = TicketType.objects.get(
            event=self.event, name="Saturday workshop 13-17"
        )
        TicketType.objects.filter(pk__in=[retired.pk, unused.pk]).update(
            is_active=False
        )
        flagged = lambda: {  # noqa: E731
            w["row"]
            for w in self.check()["warnings"]
            if w["code"] == "inactive_unreferenced"
        }
        self.assertEqual(
            flagged(),
            {"Ticket type 'Child pass 0-12'", "Ticket type 'Saturday workshop 13-17'"},
        )
        EventTicket.objects.create(
            attendee=make_child(), event=self.event, ticket_type=retired
        )
        self.assertEqual(flagged(), {"Ticket type 'Saturday workshop 13-17'"})

    def test_extras_and_choices_with_history_are_not_called_deletable(self):
        extra = Extra.objects.get(event=self.event, name="T-shirt")
        extra.choice_rows.update(is_active=False)
        extra.is_active = False
        extra.save()
        flagged = lambda: {  # noqa: E731
            w["row"]
            for w in self.check()["warnings"]
            if w["code"] == "inactive_unreferenced"
        }
        self.assertIn("Extra 'T-shirt'", flagged())
        self.assertIn("Choice 'XL'", flagged())
        family = Family.objects.create(last_name="T")
        registration = Registration.objects.create(
            event=self.event,
            family=family,
            contact_email="a@example.com",
            verification_token_hash="x",
        )
        RegistrationExtra.objects.create(
            registration=registration,
            extra=extra,
            choice=extra.choice_rows.get(label="XL"),
            price_at_registration=0,
        )
        rows = flagged()
        self.assertNotIn("Extra 'T-shirt'", rows)
        self.assertNotIn("Choice 'XL'", rows)
        self.assertIn("Choice 'S'", rows)

    def test_redeemed_promo_codes_are_not_called_deletable(self):
        promo = PromoCode.objects.create(
            event=self.event,
            code="SPENT",
            discount_type="percent",
            discount_value=10,
            is_active=False,
        )
        flagged = lambda: {  # noqa: E731
            w["row"]
            for w in self.check()["warnings"]
            if w["code"] == "inactive_unreferenced"
        }
        self.assertIn("Promo code 'SPENT'", flagged())
        Registration.objects.create(
            event=self.event,
            family=Family.objects.create(last_name="P"),
            contact_email="p@example.com",
            verification_token_hash="x",
            promo_code=promo,
        )
        self.assertNotIn("Promo code 'SPENT'", flagged())

    def test_admin_page_and_action(self):
        self.client.force_login(self.user)
        with at_now():
            page = self.client.get(
                reverse("admin:events_event_check_setup", args=[self.event.pk])
            )
            action = self.client.post(
                reverse("admin:events_event_changelist"),
                {
                    "action": "check_setup_action",
                    "_selected_action": [str(self.event.pk)],
                },
            )
            change = self.client.get(
                reverse("admin:events_event_change", args=[self.event.pk])
            )
        for response in (page, action):
            self.assertContains(
                response, "Ticket type &#x27;Saturday workshop 13-17&#x27;"
            )
            # Organizers see the row name, not the spec path.
            self.assertNotContains(response, "ticket_types[")
        self.assertContains(
            change, reverse("admin:events_event_check_setup", args=[self.event.pk])
        )

    def test_admin_page_and_action_need_view_permission(self):
        self.client.force_login(self.plain)
        with at_now():
            page = self.client.get(
                reverse("admin:events_event_check_setup", args=[self.event.pk])
            )
            action = self.client.post(
                reverse("admin:events_event_changelist"),
                {
                    "action": "check_setup_action",
                    "_selected_action": [str(self.event.pk)],
                },
            )
        self.assertEqual(page.status_code, 404)
        self.assertNotContains(action, "Saturday workshop", status_code=403)
