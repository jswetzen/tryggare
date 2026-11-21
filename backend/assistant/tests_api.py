"""The assistant's REST endpoints and the draft-aware form spec."""

import copy
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from rest_framework.test import APIClient

from accounts.models import AdminUser
from events import event_spec
from events.event_spec._export import keyed_rows
from events.models import Event, Extra, ExtraChoice, PromoCode, Session, TicketType
from events.spec_test_support import add_ticket, at_now, example_with_bundle
from registrations.form_spec import build_form_spec, stable_id

from . import runner
from .models import AssistantConversation, LLMProvider
from .tools import _plain, base_hash, draft_token

MODELS = (Event, Session, TicketType, Extra, ExtraChoice, PromoCode)


def draft_spec(event):
    """A spec that adds a session, a bundle over both sessions, and an extra with
    choices on that session, and reprices an existing ticket type."""
    spec = example_with_bundle()
    spec["sessions"].append(
        {
            "key": "sunday-hike",
            "name": "Sunday hike",
            "start_time": "2027-06-20T10:00:00",
            "end_time": "2027-06-20T12:00:00",
            "ticket_rule": "children",
            "adults_not_checked_in": False,
        }
    )
    spec["ticket_types"][-1]["sessions"].append("sunday-hike")
    spec["ticket_types"][0]["price"] = 1300
    spec["extras"].append(
        {
            "key": "packed-lunch",
            "name": "Packed lunch",
            "price": 80,
            "per_attendee": True,
            "applies_to": "child",
            "session": "sunday-hike",
            "ticket_types": ["saturday-workshop-13-17"],
            "requires_choice": True,
            "choices": [
                {"key": "meat", "label": "Meat", "sort_order": 10},
                {"key": "veg", "label": "Vegetarian", "sort_order": 20},
            ],
            "sort_order": 40,
        }
    )
    return spec


class ApiCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = AdminUser.objects.create_superuser("apistaff", "pw12345")
        cls.other_staff = AdminUser.objects.create_superuser("apistaff2", "pw12345")
        cls.plain = AdminUser.objects.create_user("apiplain", "pw12345")
        with at_now():
            cls.event = event_spec.apply(event_spec.example_spec())[0]

    def setUp(self):
        cache.clear()  # the anonymous throttle counts per client address
        provider = LLMProvider.load()
        provider.enabled = True
        provider.save()
        self.client = APIClient()
        self.client.force_authenticate(self.staff)

    def url(self, name, event=None, **kw):
        return reverse(name, kwargs={"event_id": (event or self.event).pk, **kw})

    def conversation(self, user=None):
        conv, _ = AssistantConversation.objects.get_or_create(
            event=self.event, user=user or self.staff
        )
        return conv

    def store_draft(self, spec=None, user=None):
        """Store a draft the way the runner does, without a run."""
        spec = _plain(spec or draft_spec(self.event))
        base = base_hash(self.event)
        result = event_spec.check(spec, self.event)
        conv = self.conversation(user)
        token = draft_token(self.event.pk, base, spec)
        conv.draft_version += 1
        conv.draft = {
            "spec": spec,
            "base": base,
            "diff": _plain(result["diff"]),
            "warnings": _plain(result["warnings"]),
            "token": token,
            "version": conv.draft_version,
        }
        conv.save()
        return conv


class GateTests(ApiCase):
    ENDPOINTS = (
        ("get", "assistant-conversation"),
        ("delete", "assistant-conversation"),
        ("post", "assistant-notice"),
        ("get", "assistant-draft"),
        ("delete", "assistant-draft"),
        ("get", "assistant-preview"),
    )

    def each(self, client, expected, event=None, **kw):
        for method, name in self.ENDPOINTS:
            with self.subTest(method=method, name=name):
                r = getattr(client, method)(self.url(name, event), **kw)
                self.assertEqual(r.status_code, expected, r.content)
                self.assertEqual(r["Cache-Control"], "no-store")
                # A refusal carries the reasons and nothing of the conversation or draft.
                self.assertEqual(set(r.json()), {"errors", "warnings"})

    def test_unauthenticated_401(self):
        self.each(APIClient(), 401)

    def test_no_permission_403(self):
        client = APIClient()
        client.force_authenticate(self.plain)
        self.each(client, 403)

    def test_403_comes_before_any_event_lookup(self):
        client = APIClient()
        client.force_authenticate(self.plain)
        missing = mock.Mock(pk="00000000-0000-4000-8000-000000000000")
        r = client.get(self.url("assistant-preview", missing))
        self.assertEqual(r.status_code, 403)

    def test_unknown_event_404(self):
        missing = mock.Mock(pk="00000000-0000-4000-8000-000000000000")
        self.each(self.client, 404, event=missing)

    def test_event_with_registrations_409_lists_blockers(self):
        add_ticket(self.event)
        self.each(self.client, 409)
        r = self.client.get(self.url("assistant-conversation"))
        self.assertEqual(
            [e["code"] for e in r.json()["errors"]],
            ["event_not_eligible", "event_not_empty"],
        )

    def test_provider_off_503(self):
        LLMProvider.objects.update(enabled=False)
        self.each(self.client, 503)

    def test_revoked_permission_is_seen_on_the_next_request(self):
        client = APIClient()
        client.force_authenticate(self.other_staff)
        self.assertEqual(
            client.get(self.url("assistant-conversation")).status_code, 200
        )
        AdminUser.objects.filter(pk=self.other_staff.pk).update(
            is_superuser=False, is_staff=False
        )
        self.assertEqual(
            client.get(self.url("assistant-conversation")).status_code, 403
        )


class ConversationTests(ApiCase):
    def test_no_conversation_yet_creates_nothing(self):
        r = self.client.get(self.url("assistant-conversation"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(
            r.json(),
            {
                "available": True,
                "conversation_id": None,
                "transcript": [],
                "running": False,
                "notice_accepted": False,
                "draft_version": 0,
            },
        )
        self.assertFalse(AssistantConversation.objects.exists())

    def test_transcript_notice_and_version(self):
        conv = self.conversation()
        conv.messages = runner.dump_messages(
            [
                ModelRequest(parts=[UserPromptPart("two day camp")]),
                ModelResponse(parts=[TextPart("Done.")]),
            ]
        )
        conv.notice_accepted_at = timezone.now()
        conv.draft_version = 3
        conv.save()
        body = self.client.get(self.url("assistant-conversation")).json()
        self.assertEqual(
            body["transcript"],
            [
                {"role": "user", "text": "two day camp"},
                {"role": "assistant", "text": "Done."},
            ],
        )
        self.assertEqual(
            (body["notice_accepted"], body["draft_version"], body["running"]),
            (True, 3, False),
        )
        self.assertEqual(body["conversation_id"], str(conv.id))

    def test_running_is_live_but_a_dead_run_is_reset(self):
        conv = self.conversation()
        conv.status, conv.run_started_at = "running", timezone.now()
        conv.save()
        self.assertTrue(
            self.client.get(self.url("assistant-conversation")).json()["running"]
        )
        AssistantConversation.objects.update(
            run_started_at=timezone.now() - timezone.timedelta(hours=1)
        )
        self.assertFalse(
            self.client.get(self.url("assistant-conversation")).json()["running"]
        )
        self.assertEqual(AssistantConversation.objects.get().status, "idle")

    def test_conversations_are_per_user(self):
        other = self.conversation(self.other_staff)
        other.messages = runner.dump_messages(
            [ModelRequest(parts=[UserPromptPart("secret plan")])]
        )
        other.save()
        body = self.client.get(self.url("assistant-conversation")).json()
        self.assertEqual(body["transcript"], [])
        self.assertNotIn("secret plan", str(body))

    def test_notice_accept_is_idempotent(self):
        r = self.client.post(self.url("assistant-notice"))
        self.assertEqual((r.status_code, r.json()), (200, {"notice_accepted": True}))
        first = AssistantConversation.objects.get().notice_accepted_at
        self.assertIsNotNone(first)
        self.client.post(self.url("assistant-notice"))
        self.assertEqual(AssistantConversation.objects.get().notice_accepted_at, first)

    def test_clear_resets_and_tells_consumers_to_cancel(self):
        conv = self.store_draft()
        conv.messages = [{"x": 1}]
        conv.status, conv.run_started_at = "running", timezone.now()
        conv.notice_accepted_at = timezone.now()
        conv.save()
        layer = mock.Mock(group_send=mock.AsyncMock())
        with mock.patch("assistant.views.get_channel_layer", return_value=layer):
            r = self.client.delete(self.url("assistant-conversation"))
        self.assertEqual(r.status_code, 204)
        layer.group_send.assert_awaited_once_with(
            runner.group_name(conv.id), {"type": "assistant.cancel"}
        )
        conv.refresh_from_db()
        self.assertEqual(
            (conv.messages, conv.draft, conv.status, conv.run_started_at),
            ([], None, "idle", None),
        )
        self.assertIsNotNone(conv.notice_accepted_at)

    def test_clear_still_succeeds_when_the_channel_layer_fails(self):
        conv = self.conversation()
        conv.status, conv.run_started_at = "running", timezone.now()
        conv.save()
        layer = mock.Mock(group_send=mock.AsyncMock(side_effect=OSError("down")))
        with mock.patch("assistant.views.get_channel_layer", return_value=layer):
            r = self.client.delete(self.url("assistant-conversation"))
        self.assertEqual(r.status_code, 204)
        layer.group_send.assert_awaited_once()

    def test_clear_of_an_idle_conversation_sends_no_cancel(self):
        # A late cancel would end the run the user starts right after the clear.
        self.store_draft()
        layer = mock.Mock(group_send=mock.AsyncMock())
        with mock.patch("assistant.views.get_channel_layer", return_value=layer):
            r = self.client.delete(self.url("assistant-conversation"))
        self.assertEqual(r.status_code, 204)
        layer.group_send.assert_not_awaited()
        self.assertIsNone(AssistantConversation.objects.get().draft)

    def test_clear_without_a_conversation_is_fine(self):
        self.assertEqual(
            self.client.delete(self.url("assistant-conversation")).status_code, 204
        )


class DraftTests(ApiCase):
    def test_no_draft_404(self):
        self.assertEqual(self.client.get(self.url("assistant-draft")).status_code, 404)
        self.conversation()
        self.assertEqual(self.client.get(self.url("assistant-draft")).status_code, 404)

    def test_get_draft_and_staleness(self):
        conv = self.store_draft()
        body = self.client.get(self.url("assistant-draft")).json()
        self.assertEqual(body["spec"], conv.draft["spec"])
        self.assertEqual((body["stale"], body["version"]), (False, 1))
        self.assertEqual(body["token"], conv.draft["token"])
        self.assertTrue(body["diff"])
        changed = copy.deepcopy(event_spec.export(self.event))
        changed["ticket_types"][0]["price"] = 5
        event_spec.apply(changed, self.event)
        self.assertTrue(self.client.get(self.url("assistant-draft")).json()["stale"])

    def test_warnings_follow_the_requested_language_not_the_proposal_time(self):
        conv = self.store_draft()
        # Stored the way propose_spec does: code and params, text from the language then.
        conv.draft["warnings"] = _plain(
            [
                event_spec.issue("event", "registration_closed"),
                event_spec.issue("ticket_types[0]", "age_band_gap", start=0, end=3),
            ]
        )
        conv.save()
        url = self.url("assistant-draft")
        en = self.client.get(url).json()["warnings"]
        sv = self.client.get(url + "?lang=sv").json()["warnings"]
        self.assertEqual(
            en[1]["message"], "No active ticket covers children aged 0 to 3."
        )
        self.assertEqual(
            sv[1]["message"], "Ingen aktiv biljett gäller barn i åldern 0 till 3."
        )
        self.assertEqual(sv[0]["message"], "Anmälningsfönstret har redan stängt.")
        self.assertEqual([w["code"] for w in sv], [w["code"] for w in en])
        # An unknown language falls back to the default; the language does not stick.
        self.assertEqual(self.client.get(url + "?lang=xx").json()["warnings"], en)
        self.assertEqual(self.client.get(url).json()["warnings"], en)

    def test_a_warning_without_params_keeps_its_stored_text(self):
        conv = self.store_draft()
        conv.draft["warnings"] = [
            {"path": "", "code": "registration_closed", "message": "Stored text"}
        ]
        conv.save()
        got = self.client.get(self.url("assistant-draft") + "?lang=sv").json()
        self.assertEqual(got["warnings"][0]["message"], "Stored text")

    def test_another_users_draft_is_invisible(self):
        self.store_draft(user=self.other_staff)
        self.assertEqual(self.client.get(self.url("assistant-draft")).status_code, 404)
        self.assertEqual(
            self.client.delete(self.url("assistant-draft") + "?version=1").status_code,
            404,
        )
        self.assertIsNotNone(
            AssistantConversation.objects.get(user=self.other_staff).draft
        )

    def test_discard(self):
        self.store_draft()
        url = self.url("assistant-draft") + "?version=1"
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertIsNone(AssistantConversation.objects.get().draft)
        self.assertEqual(self.client.delete(url).status_code, 404)

    def test_discard_after_apply_leaves_a_newer_draft(self):
        conv = self.store_draft()
        shown = self.client.get(self.url("assistant-draft")).json()
        # A run finishes between the apply and the discard and proposes again.
        conv.draft = {**conv.draft, "version": 2, "token": "newer"}
        conv.draft_version = 2
        conv.save()
        r = self.client.delete(
            self.url("assistant-draft")
            + f"?version={shown['version']}&token={shown['token']}"
        )
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.json()["errors"][0]["code"], "draft_changed")
        self.assertEqual(AssistantConversation.objects.get().draft["token"], "newer")
        r = self.client.delete(self.url("assistant-draft") + "?version=2")
        self.assertEqual(r.status_code, 204)
        self.assertIsNone(AssistantConversation.objects.get().draft)

    def test_discard_with_the_seen_token_and_version(self):
        self.store_draft()
        shown = self.client.get(self.url("assistant-draft")).json()
        r = self.client.delete(
            self.url("assistant-draft")
            + f"?version={shown['version']}&token={shown['token']}"
        )
        self.assertEqual(r.status_code, 204)

    def test_missing_version_400(self):
        self.store_draft()
        r = self.client.delete(self.url("assistant-draft"))
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["errors"][0]["code"], "version_required")
        self.assertIsNotNone(AssistantConversation.objects.get().draft)

    def test_invalid_version_400(self):
        self.store_draft()
        r = self.client.delete(self.url("assistant-draft") + "?version=x")
        self.assertEqual(r.status_code, 400)
        self.assertIsNotNone(AssistantConversation.objects.get().draft)


def counts():
    return {m.__name__: m.objects.count() for m in MODELS}


def swap_ids(value, ids):
    if isinstance(value, str):
        return ids.get(value, value)
    if isinstance(value, list):
        return [swap_ids(v, ids) for v in value]
    if isinstance(value, dict):
        return {k: swap_ids(v, ids) for k, v in value.items()}
    return value


class PreviewTests(ApiCase):
    def preview(self):
        r = self.client.get(self.url("assistant-preview"))
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def test_no_draft_is_the_saved_public_spec(self):
        body = self.preview()
        public = APIClient().get(
            reverse("registration-event-info", kwargs={"event_id": self.event.pk})
        )
        self.assertEqual(public.status_code, 200)
        self.assertEqual(body["form_spec"], public.json())
        self.assertEqual(
            (body["source"], body["stale"], body["diff"], body["warnings"]),
            ("saved", False, [], []),
        )

    def test_draft_preview_equals_a_real_apply(self):
        self.store_draft()
        body = self.preview()
        self.assertEqual(body["source"], "draft")
        self.assertTrue(body["diff"])
        before_ids = {str(t.pk) for t in TicketType.objects.filter(event=self.event)}
        preview_ids = {t["id"] for t in body["form_spec"]["ticket_types"]}
        added = preview_ids - before_ids
        self.assertEqual(len(added), 1)  # the bundle
        self.assertFalse(TicketType.objects.filter(pk__in=added).exists())

        event_spec.apply(draft_spec(self.event), self.event)
        applied = Event.objects.get(pk=self.event.pk)
        real = _plain(build_form_spec(applied))
        # Each stable id maps to the real id the row got.
        ids = {
            stable_id(applied.id, kind, row.parent, row.key): str(row.obj.pk)
            for kind, rows in keyed_rows(applied).items()
            for row in rows
        }
        self.assertEqual(swap_ids(body["form_spec"], ids), real)

    def test_two_previews_are_identical(self):
        self.store_draft()
        self.assertEqual(self.preview(), self.preview())

    def test_preview_writes_nothing(self):
        self.store_draft()
        before = counts()
        exported = event_spec.export(self.event)
        self.preview()
        self.assertEqual(counts(), before)
        self.assertEqual(
            event_spec.export(Event.objects.get(pk=self.event.pk)), exported
        )
        self.assertEqual(Event.objects.get(pk=self.event.pk).name, self.event.name)

    def test_existing_rows_keep_their_real_ids(self):
        self.store_draft()
        real = {str(t.pk) for t in TicketType.objects.filter(event=self.event)}
        ids = {t["id"] for t in self.preview()["form_spec"]["ticket_types"]}
        self.assertTrue(real <= ids)

    def test_stale_draft_is_flagged_but_still_previewed(self):
        self.store_draft()
        changed = copy.deepcopy(event_spec.export(self.event))
        changed["ticket_types"][1]["price"] = 5
        event_spec.apply(changed, self.event)
        body = self.preview()
        self.assertEqual((body["source"], body["stale"]), ("draft", True))
        self.assertFalse(body["draft_unusable"])

    def test_a_draft_that_no_longer_applies_falls_back_to_saved(self):
        self.store_draft()
        broken = event_spec.SpecError([event_spec.issue("", "event_not_empty")])
        with mock.patch("registrations.form_spec.event_spec.apply", side_effect=broken):
            body = self.preview()
        self.assertEqual(
            (body["source"], body["stale"], body["draft_unusable"]),
            ("saved", True, True),
        )
        self.assertEqual(
            body["form_spec"],
            _plain(build_form_spec(Event.objects.get(pk=self.event.pk))),
        )

    def test_preview_is_per_user(self):
        self.store_draft(user=self.other_staff)
        self.assertEqual(self.preview()["source"], "saved")


class PreviewRollbackTests(TransactionTestCase):
    """Real transactions: in a TestCase the preview's block is only a savepoint, so the
    autocommit path (production, no ATOMIC_REQUESTS) is checked here."""

    url = ApiCase.url
    conversation = ApiCase.conversation
    store_draft = ApiCase.store_draft

    def setUp(self):
        self.staff = AdminUser.objects.create_superuser("rbstaff", "pw12345")
        with at_now():
            self.event = event_spec.apply(event_spec.example_spec())[0]
        provider = LLMProvider.load()
        provider.enabled = True
        provider.save()
        self.client = APIClient()
        self.client.force_authenticate(self.staff)
        self.store_draft()
        self.before = (counts(), event_spec.export(self.event))

    def assertUnchanged(self):
        after = (counts(), event_spec.export(Event.objects.get(pk=self.event.pk)))
        self.assertEqual(after, self.before)

    def test_preview_outside_a_transaction_writes_nothing(self):
        r = self.client.get(self.url("assistant-preview"))
        self.assertEqual(r.json()["source"], "draft")
        self.assertUnchanged()

    def test_a_failure_after_the_writes_leaves_nothing(self):
        with mock.patch(
            "registrations.form_spec.build_form_spec", side_effect=RuntimeError
        ):
            with self.assertRaises(RuntimeError):
                self.client.get(self.url("assistant-preview"))
        self.assertUnchanged()
