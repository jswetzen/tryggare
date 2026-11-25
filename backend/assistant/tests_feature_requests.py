"""File_feature_request: the tool, the review REST API and the WebSocket draft event.
The rules themselves are in feature_requests/tests_rules.py."""

import json

from asgiref.sync import async_to_sync
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from pydantic_ai.models.function import DeltaToolCall, FunctionModel
from rest_framework.test import APIClient

from accounts.models import AdminUser
from events import event_spec
from events.models import Event
from events.spec_test_support import at_now
from feature_requests import services
from feature_requests.models import FeatureRequest

from . import runner
from .agent import SYSTEM_PROMPT, capabilities_summary
from .models import AssistantConversation, LLMProvider
from .tools import TOOL_NAMES, EventTools, ToolFailure, build_toolset

REQUEST = {
    "title": "Family price",
    "problem": "Families want one price for the whole group.",
    "desired": "A price for a group of attendees.",
    "touches": ["cap:family_groups"],
    "severity": "friction",
    "workaround": {"used": "One discount code per family", "cost": "extra_steps"},
}


def call(tools, name, **args):
    with at_now():
        return getattr(tools, name)(**args)


def with_perms(name, labels=()):
    user = AdminUser.objects.create_user(name, "pw12345")
    for label in labels:
        app, codename = label.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    return user


class Fixture(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = AdminUser.objects.create_superuser("frstaff", "pw12345")
        cls.coord = with_perms("frcoord", ["events.change_event"])
        cls.plain = with_perms("frplain")
        with at_now():
            cls.event = event_spec.apply(event_spec.example_spec())[0]
        cls.other = Event.objects.create(
            name="Other", start_date="2027-01-01", end_date="2027-01-02"
        )


class ToolTests(Fixture):
    def test_tool_is_registered_and_described_to_the_model(self):
        self.assertIn("file_feature_request", TOOL_NAMES)
        toolset, _ = build_toolset(self.event, self.staff)
        self.assertIn("file_feature_request", toolset.tools)
        self.assertIn("file_feature_request", SYSTEM_PROMPT)
        self.assertIn("cap:<id>", capabilities_summary())

    def test_files_a_draft_and_reports_no_match(self):
        result = call(
            EventTools(self.event, self.staff), "file_feature_request", **REQUEST
        )
        self.assertEqual(result["status"], "draft")
        self.assertIsNone(result["matches_existing"])
        row = FeatureRequest.objects.get(pk=int(result["id"][3:]))
        self.assertEqual(
            (row.status, row.source, row.event), ("draft", "assistant", self.event)
        )
        self.assertEqual(row.filed_by, self.staff)

    def test_reports_an_open_match_with_its_seen_count(self):
        tools = EventTools(self.event, self.staff)
        first = call(tools, "file_feature_request", **REQUEST)
        services.confirm(
            FeatureRequest.objects.get(pk=int(first["id"][3:])), self.staff
        )
        again = call(tools, "file_feature_request", **REQUEST)
        self.assertEqual(again["matches_existing"], {"id": first["id"], "seen": 1})

    def test_invalid_input_is_a_retryable_failure_without_the_value(self):
        tools = EventTools(self.event, self.staff)
        with self.assertRaises(ToolFailure) as ctx:
            call(
                tools,
                "file_feature_request",
                **{**REQUEST, "problem": "Mail anna@example.com"},
            )
        self.assertIn("personal_data", str(ctx.exception))
        self.assertNotIn("anna@", str(ctx.exception))
        with self.assertRaises(ToolFailure):
            call(
                tools, "file_feature_request", **{**REQUEST, "touches": ["cap:made_up"]}
            )
        self.assertFalse(FeatureRequest.objects.exists())

    def test_a_user_who_cannot_use_the_assistant_gets_no_tool(self):
        with self.assertRaises(Exception):
            EventTools(self.event, self.coord.__class__.objects.get(pk=self.plain.pk))


class RestTests(Fixture):
    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.coord)

    def url(self, event=None, *tail):
        base = reverse(
            "assistant-feature-requests", kwargs={"event_id": (event or self.event).pk}
        )
        return base + "".join(f"{t}/" for t in tail)

    def file(self, event=None, client=None):
        r = (client or self.client).post(self.url(event), REQUEST, format="json")
        self.assertEqual(r.status_code, 201, r.content)
        return r.json()["id"]

    def test_post_files_an_organizer_draft_even_with_the_chat_switched_off(self):
        LLMProvider.load()  # disabled by default: the review API does not depend on it
        request_id = self.file()
        row = FeatureRequest.objects.get(pk=int(request_id[3:]))
        self.assertEqual((row.source, row.status), ("organizer", "draft"))

    def test_get_lists_only_my_drafts_on_this_event(self):
        mine = self.file()
        other_client = APIClient()
        other_client.force_authenticate(with_perms("frcoord2", ["events.change_event"]))
        self.file(client=other_client)
        self.file(event=self.other)
        drafts = self.client.get(self.url()).json()["drafts"]
        self.assertEqual([d["id"] for d in drafts], [mine])
        self.assertEqual(
            set(drafts[0]),
            {
                "id",
                "title",
                "problem",
                "desired",
                "tried",
                "workaround",
                "brief_fragment",
                "touches",
                "severity",
                "matches_existing",
            },
        )

    def test_confirm_stores_and_discard_removes(self):
        first = self.file()
        r = self.client.post(self.url(None, first, "confirm"), {}, format="json")
        self.assertEqual(r.json()["status"], "confirmed")
        second = self.file()
        r = self.client.post(self.url(None, second, "discard"))
        self.assertEqual(r.status_code, 204)
        self.assertFalse(FeatureRequest.objects.filter(pk=int(second[3:])).exists())

    def test_confirm_during_a_run_is_409_and_the_draft_stays(self):
        request_id = self.file()
        conv, _ = AssistantConversation.objects.get_or_create(
            event=self.event, user=self.coord
        )
        conv.status = conv.STATUS_RUNNING
        conv.run_started_at = timezone.now()
        conv.save()
        r = self.client.post(self.url(None, request_id, "confirm"), {}, format="json")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["errors"][0]["code"], "run_in_progress")
        row = FeatureRequest.objects.get(pk=int(request_id[3:]))
        self.assertEqual(row.status, "draft")
        conv.status, conv.run_started_at = conv.STATUS_IDLE, None
        conv.save()
        r = self.client.post(self.url(None, request_id, "confirm"), {}, format="json")
        self.assertEqual(r.status_code, 200)

    def test_confirm_with_edits_runs_the_checks(self):
        request_id = self.file()
        r = self.client.post(
            self.url(None, request_id, "confirm"),
            {"problem": "Ask anna@example.com"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["errors"][0]["code"], "personal_data")
        self.assertNotIn("anna@", r.content.decode())
        self.assertEqual(
            FeatureRequest.objects.get(pk=int(request_id[3:])).status, "draft"
        )

    def test_a_client_cannot_set_triage_fields(self):
        request_id = self.file()
        r = self.client.post(
            self.url(None, request_id, "confirm"),
            {"status": "planned", "seen": 50, "duplicate_of": 1, "source": "trial"},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertEqual({e["code"] for e in r.json()["errors"]}, {"extra_forbidden"})
        row = FeatureRequest.objects.get(pk=int(request_id[3:]))
        self.assertEqual((row.status, row.seen, row.source), ("draft", 1, "organizer"))
        r = self.client.post(
            self.url(), {**REQUEST, "status": "confirmed"}, format="json"
        )
        self.assertEqual(r.status_code, 400)

    def test_malformed_ids_read_as_absent(self):
        for bad in ("FR-\u00b2", "FR-\u0663", "FR-" + "9" * 30, "fr-1", "FR-"):
            with self.subTest(bad=bad):
                r = self.client.post(self.url(None, bad, "confirm"), {}, format="json")
                self.assertEqual(r.status_code, 404)

    def test_another_organizers_draft_reads_as_absent(self):
        request_id = self.file()
        intruder = APIClient()
        intruder.force_authenticate(with_perms("frcoord3", ["events.change_event"]))
        self.assertEqual(
            intruder.post(
                self.url(None, request_id, "confirm"), {}, format="json"
            ).status_code,
            404,
        )
        self.assertEqual(
            intruder.post(self.url(None, request_id, "discard")).status_code, 404
        )

    def test_a_draft_is_not_visible_under_another_event(self):
        request_id = self.file()
        r = self.client.post(
            self.url(self.other, request_id, "confirm"), {}, format="json"
        )
        self.assertEqual(r.status_code, 404)

    def test_refusals(self):
        anon = APIClient()
        self.assertEqual(anon.get(self.url()).status_code, 401)
        plain = APIClient()
        plain.force_authenticate(self.plain)
        self.assertEqual(plain.get(self.url()).status_code, 403)
        self.assertEqual(
            plain.post(self.url(), REQUEST, format="json").status_code, 403
        )
        self.assertEqual(
            self.client.get(
                reverse(
                    "assistant-feature-requests",
                    kwargs={"event_id": "00000000-0000-0000-0000-000000000000"},
                )
            ).status_code,
            404,
        )

    def test_responses_are_not_cached(self):
        self.assertEqual(self.client.get(self.url())["Cache-Control"], "no-store")


class DraftEventTests(Fixture):
    """A real run with a scripted model: the protocol gets a server-built payload."""

    def run_with(self, args, user=None):
        user = user or self.staff
        AssistantConversation.objects.get_or_create(event=self.event, user=user)
        AssistantConversation.objects.filter(event=self.event, user=user).update(
            notice_accepted_at=timezone.now()
        )
        steps = iter([("file_feature_request", args), "Drafted for you to confirm."])

        async def stream(messages, info):
            step = next(steps)
            if isinstance(step, str):
                yield step
            else:
                name, call_args = step
                yield {
                    0: DeltaToolCall(
                        name=name,
                        json_args=json.dumps(call_args, default=str),
                        tool_call_id="call-file",
                    )
                }

        events = []

        async def collect(payload):
            events.append(payload)

        with at_now():
            async_to_sync(runner.run_conversation)(
                self.event,
                user,
                "file it",
                model=FunctionModel(stream_function=stream),
                on_event=collect,
            )
        return events

    def test_draft_event_carries_only_the_stored_fields(self):
        events = self.run_with(
            {**REQUEST, "tried": ["Two tickets"], "touches": ["cap:family_groups"]}
        )
        drafted = [e for e in events if e["type"] == "feature_request_draft"]
        self.assertEqual(len(drafted), 1)
        payload = drafted[0]
        self.assertLessEqual(
            set(payload),
            {
                "type",
                "run_id",
                "id",
                "title",
                "problem",
                "desired",
                "workaround",
                "matches_existing",
            },
        )
        self.assertEqual(payload["title"], REQUEST["title"])
        self.assertEqual(payload["workaround"], REQUEST["workaround"])
        self.assertIsNone(payload["matches_existing"])
        self.assertNotIn("touches", payload)
        self.assertNotIn("Two tickets", str(payload))  # tried is kept off the wire

    def test_refused_draft_emits_nothing(self):
        events = self.run_with({**REQUEST, "problem": "Mail anna@example.com"})
        self.assertNotIn("feature_request_draft", [e["type"] for e in events])
        self.assertEqual(FeatureRequest.objects.count(), 0)

    def test_payload_is_refused_for_another_users_draft(self):
        row, _ = services.file_draft(
            self.event, self.coord, REQUEST, source="assistant"
        )
        self.assertIsNone(
            runner.feature_request_payload(row.public_id, self.event.pk, self.staff.pk)
        )
        self.assertIsNotNone(
            runner.feature_request_payload(row.public_id, self.event.pk, self.coord.pk)
        )
        self.assertIsNone(
            runner.feature_request_payload("FR-x", self.event.pk, self.coord.pk)
        )
        self.assertIsNone(
            runner.feature_request_payload(None, self.event.pk, self.coord.pk)
        )
