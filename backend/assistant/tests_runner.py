import copy
import json
from datetime import timedelta
from unittest import mock

from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from accounts.models import AdminUser
from events import event_spec
from events.models import Event
from events.spec_test_support import at_now

from . import runner
from .agent import SYSTEM_PROMPT
from .models import AssistantConversation, AssistantRun
from .runner import RunFailed, run_conversation


def ask(event, user, text="hello", model=None):
    return async_to_sync(run_conversation)(
        event, user, text, model=model or TestModel(call_tools=[])
    )


# Admin pages need the hashed-static manifest otherwise; unrelated to what is tested.
PLAIN_STATICFILES = override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }
)


class RunnerTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = AdminUser.objects.create_superuser("runstaff", "pw12345")
        cls.other_staff = AdminUser.objects.create_superuser("runstaff2", "pw12345")
        with at_now():
            cls.event = event_spec.apply(event_spec.example_spec())[0]

    def conv(self, user=None, accepted=True):
        conv, _ = AssistantConversation.objects.get_or_create(
            event=self.event, user=user or self.staff
        )
        if accepted:
            conv.notice_accepted_at = timezone.now()
            conv.save()
        return conv

    def seen(self):
        """A FunctionModel that records the messages of each request."""
        calls = []

        def fn(messages, info: AgentInfo):
            calls.append((copy.deepcopy(messages), info.instructions))
            return ModelResponse(parts=[TextPart("ok")])

        return FunctionModel(fn), calls


class HistoryTests(RunnerTestCase):
    def test_round_trip_and_transcript(self):
        self.conv()
        ask(self.event, self.staff, "first")
        out = ask(self.event, self.staff, "second")
        conv = AssistantConversation.objects.get()
        prompts = [m["text"] for m in runner.transcript(conv) if m["role"] == "user"]
        self.assertEqual(prompts, ["first", "second"])
        self.assertEqual(out["text"], runner.transcript(conv)[-1]["text"])
        self.assertEqual(conv.status, "idle")
        self.assertIsNone(conv.run_started_at)

    def test_second_run_sees_first(self):
        self.conv()
        model, calls = self.seen()
        ask(self.event, self.staff, "first", model)
        ask(self.event, self.staff, "second", model)
        self.assertEqual(len(calls[1][0]), 3)  # request, response, new request

    def test_no_system_prompt_stored_and_instructions_nulled(self):
        self.conv()
        ask(self.event, self.staff)
        stored = json.dumps(AssistantConversation.objects.get().messages)
        self.assertNotIn("system-prompt", stored)
        self.assertNotIn(SYSTEM_PROMPT[:30], stored)
        for msg in AssistantConversation.objects.get().messages:
            if msg["kind"] == "request":
                self.assertIsNone(msg["instructions"])

    def test_changed_prompt_reaches_old_conversation(self):
        self.conv()
        ask(self.event, self.staff, "first")
        model, calls = self.seen()
        with mock.patch("assistant.agent.SYSTEM_PROMPT", "NEW RULES"):
            # build_agent reads the module global at call time
            ask(self.event, self.staff, "second", model)
        self.assertIn("NEW RULES", calls[0][1])

    def test_trim_stubs_old_read_tool_returns(self):
        big = {"schema": "x" * 5000}
        msgs = [
            ModelRequest(parts=[UserPromptPart("hi")]),
            ModelResponse(parts=[ToolCallPart("get_capabilities", {}, "c1")]),
            ModelRequest(parts=[ToolReturnPart("get_capabilities", big, "c1")]),
            ModelResponse(parts=[ToolCallPart("validate_spec", {}, "c2")]),
            ModelRequest(
                parts=[ToolReturnPart("validate_spec", {"valid": True}, "c2")]
            ),
        ]
        out = runner.trim_history(msgs)
        self.assertEqual(out[2].parts[0].content, runner.STUB)
        self.assertEqual(out[4].parts[0].content, {"valid": True})
        self.assertEqual(msgs[2].parts[0].content, big)  # input untouched

    def test_trim_keeps_last_turns_on_a_turn_boundary(self):
        msgs = []
        for i in range(5):
            msgs += [
                ModelRequest(parts=[UserPromptPart(f"q{i}")]),
                ModelResponse(parts=[ToolCallPart("validate_spec", {}, f"c{i}")]),
                ModelRequest(parts=[ToolReturnPart("validate_spec", {}, f"c{i}")]),
                ModelResponse(parts=[TextPart("a")]),
            ]
        out = runner.trim_history(msgs, max_turns=2)
        self.assertEqual(len(out), 8)
        self.assertEqual(out[0].parts[0].content, "q3")

    def test_trim_never_cuts_at_a_request_that_answers_a_tool_call(self):
        msgs = [
            ModelRequest(parts=[UserPromptPart("q0")]),
            ModelResponse(parts=[ToolCallPart("validate_spec", {}, "c0")]),
            ModelRequest(
                parts=[
                    ToolReturnPart("validate_spec", {}, "c0"),
                    UserPromptPart("q1"),
                ]
            ),
            ModelResponse(parts=[TextPart("a")]),
        ]
        out = runner.trim_history(msgs, max_turns=1)
        self.assertEqual(len(out), 4)

    def test_stored_history_is_trimmed_on_next_run(self):
        self.conv()
        calls_model = TestModel(call_tools=["get_capabilities", "get_current_spec"])
        ask(self.event, self.staff, "first", calls_model)
        model, calls = self.seen()
        ask(self.event, self.staff, "second", model)
        returns = [
            p
            for m in calls[0][0]
            if isinstance(m, ModelRequest)
            for p in m.parts
            if isinstance(p, ToolReturnPart) and p.tool_name == "get_capabilities"
        ]
        self.assertTrue(returns)
        self.assertTrue(all(p.content == runner.STUB for p in returns))


class DraftTests(RunnerTestCase):
    def proposing_model(self):
        spec = event_spec.export(self.event)
        spec["ticket_types"][0]["price"] = 999

        def fn(messages, info):
            last = messages[-1]
            if any(
                isinstance(p, ToolReturnPart) and p.tool_name == "propose_spec"
                for p in last.parts
            ):
                return ModelResponse(parts=[TextPart("done")])
            return ModelResponse(
                parts=[ToolCallPart("propose_spec", {"spec": spec}, "p1")]
            )

        return FunctionModel(fn)

    def test_propose_persists_draft_with_versions(self):
        self.conv()
        out = ask(self.event, self.staff, "change", self.proposing_model())
        draft = AssistantConversation.objects.get().draft
        self.assertEqual(out["draft_version"], 1)
        self.assertEqual(
            set(draft), {"spec", "diff", "warnings", "base", "token", "version"}
        )
        ask(self.event, self.staff, "again", self.proposing_model())
        self.assertEqual(AssistantConversation.objects.get().draft["version"], 2)

    def test_run_that_proposes_nothing_leaves_draft(self):
        self.conv()
        ask(self.event, self.staff, "change", self.proposing_model())
        before = AssistantConversation.objects.get().draft
        ask(self.event, self.staff, "just chatting")
        self.assertEqual(AssistantConversation.objects.get().draft, before)

    def test_draft_survives_failed_run_but_messages_do_not(self):
        self.conv()
        spec = event_spec.export(self.event)
        spec["ticket_types"][0]["price"] = 5

        def fn(messages, info):
            if len(messages) == 1:
                return ModelResponse(
                    parts=[ToolCallPart("propose_spec", {"spec": spec}, "p1")]
                )
            raise RuntimeError("boom with secret body")

        with self.assertRaises(RunFailed) as cm:
            ask(self.event, self.staff, "x", FunctionModel(fn))
        self.assertEqual(cm.exception.code, "model_error")
        conv = AssistantConversation.objects.get()
        self.assertEqual(conv.draft["version"], 1)
        self.assertEqual(conv.messages, [])
        self.assertEqual(conv.status, "idle")

    def _run_with_mid_run_change(self, change):
        """Proposes, then lets ``change(conv_qs)`` touch the row before the run ends."""
        from asgiref.sync import sync_to_async

        self.conv()
        spec = event_spec.export(self.event)
        spec["ticket_types"][0]["price"] = 7
        qs = AssistantConversation.objects.all()

        async def fn(messages, info):
            if len(messages) == 1:
                await sync_to_async(change)(qs)
                return ModelResponse(
                    parts=[ToolCallPart("propose_spec", {"spec": spec}, "p1")]
                )
            return ModelResponse(parts=[TextPart("done")])

        # The tool guard sees the lock gone and ends the run before propose_spec runs.
        with self.assertRaises(RunFailed) as cm:
            ask(self.event, self.staff, "x", FunctionModel(fn))
        self.assertEqual(cm.exception.code, "cancelled")
        return AssistantConversation.objects.get()

    def test_clear_during_run_is_not_undone_by_the_run(self):
        conv = self._run_with_mid_run_change(
            lambda qs: qs.update(
                messages=[], draft=None, status="idle", run_started_at=None
            )
        )
        self.assertEqual(conv.messages, [])
        self.assertIsNone(conv.draft)

    def test_stale_run_does_not_release_a_newer_runs_lock(self):
        newer = timezone.now() + timedelta(seconds=1)
        conv = self._run_with_mid_run_change(lambda qs: qs.update(run_started_at=newer))
        self.assertEqual(conv.status, "running")
        self.assertEqual(conv.run_started_at, newer)
        self.assertEqual(conv.messages, [])
        self.assertIsNone(conv.draft)


class FailureCodeTests(RunnerTestCase):
    def fail_with(self, exc, **patches):
        self.conv()
        with mock.patch("assistant.runner.run_assistant", side_effect=exc):
            with self.assertRaises(RunFailed) as cm:
                ask(self.event, self.staff)
        self.assertEqual(AssistantConversation.objects.get().status, "idle")
        self.assertNotIn("secret", str(cm.exception))
        return cm.exception.code

    def test_codes(self):
        from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded

        from .providers import ProviderError

        self.assertEqual(self.fail_with(TimeoutError()), "timeout")
        self.assertEqual(self.fail_with(UsageLimitExceeded("secret")), "limit")
        self.assertEqual(
            self.fail_with(UnexpectedModelBehavior("secret")), "model_error"
        )
        self.assertEqual(
            self.fail_with(ProviderError("auth_failed", 401)), "auth_failed"
        )
        self.assertEqual(
            self.fail_with(ProviderError("unreachable")), "provider_unreachable"
        )

    def test_real_usage_limit(self):
        self.conv()
        looping = FunctionModel(
            lambda m, i: ModelResponse(parts=[ToolCallPart("get_current_spec", {})])
        )
        with mock.patch("assistant.agent.UsageLimits") as limits:
            from pydantic_ai import UsageLimits

            limits.side_effect = lambda **kw: UsageLimits(request_limit=3)
            with self.assertRaises(RunFailed) as cm:
                ask(self.event, self.staff, "x", looping)
        self.assertEqual(cm.exception.code, "limit")


class RuleTests(RunnerTestCase):
    def code(self, user=None, event=None):
        with self.assertRaises(RunFailed) as cm:
            ask(event or self.event, user or self.staff)
        return cm.exception.code

    def test_notice_required(self):
        self.conv(accepted=False)
        self.assertEqual(self.code(), "notice_required")

    def test_busy_when_running_and_dead_run_recovers(self):
        conv = self.conv()
        conv.status = "running"
        conv.run_started_at = timezone.now()
        conv.save()
        self.assertEqual(self.code(), "busy")
        conv.run_started_at = timezone.now() - timedelta(hours=1)
        conv.save()
        ask(self.event, self.staff)
        self.assertEqual(AssistantConversation.objects.get().status, "idle")

    def test_one_running_conversation_per_user_across_events(self):
        other = Event.objects.create(
            name="B", start_date="2027-01-01", end_date="2027-01-02"
        )
        busy, _ = AssistantConversation.objects.get_or_create(
            event=other, user=self.staff
        )
        busy.status, busy.run_started_at = "running", timezone.now()
        busy.save()
        self.conv()
        self.assertEqual(self.code(), "busy")

    @override_settings(ASSISTANT_RUNS_PER_HOUR=2)
    def test_rate_limit_per_user_per_hour(self):
        self.conv()
        ask(self.event, self.staff)
        ask(self.event, self.staff)
        self.assertEqual(self.code(), "rate_limited")
        self.conv(self.other_staff)
        ask(self.event, self.other_staff)  # another user is unaffected
        AssistantRun.objects.update(started_at=timezone.now() - timedelta(hours=2))
        ask(self.event, self.staff)

    def test_blocked_event_releases_lock(self):
        self.conv()
        with mock.patch(
            "assistant.runner.build_toolset", side_effect=PermissionDeniedStub()
        ):
            self.assertEqual(self.code(), "blocked")
        self.assertEqual(AssistantConversation.objects.get().status, "idle")

    def test_user_without_permission_blocked(self):
        user = get_user_model().objects.create_user("plain", password="pw12345")
        self.conv(user)
        self.assertEqual(self.code(user), "blocked")

    def test_provider_disabled_without_test_model(self):
        self.conv()
        with self.assertRaises(RunFailed) as cm:
            async_to_sync(run_conversation)(self.event, self.staff, "x")
        self.assertEqual(cm.exception.code, "not_enabled")

    def test_chat_text_warning(self):
        self.assertIsNone(runner.chat_text_warning("a camp for 12 to 17 year olds"))
        self.assertTrue(runner.chat_text_warning("mail anna@example.com"))
        self.assertTrue(runner.chat_text_warning("190101011234"))


def PermissionDeniedStub():
    from django.core.exceptions import PermissionDenied

    return PermissionDenied("no")


class RetentionAndDeletionTests(RunnerTestCase):
    def age(self, conv, days):
        AssistantConversation.objects.filter(pk=conv.pk).update(
            updated_at=timezone.now() - timedelta(days=days)
        )

    @override_settings(ASSISTANT_RETENTION_DAYS=30)
    def test_purge_deletes_only_idle_conversations(self):
        old = self.conv()
        fresh = self.conv(self.other_staff)
        self.age(old, 31)
        self.age(fresh, 29)
        self.assertEqual(runner.purge_idle(), 1)
        self.assertEqual(AssistantConversation.objects.get().pk, fresh.pk)

    def test_purge_command(self):
        from django.core.management import call_command

        self.age(self.conv(), 400)
        call_command("purge_assistant_conversations", verbosity=0)
        self.assertFalse(AssistantConversation.objects.exists())

    def test_cascade_on_event_and_user(self):
        self.conv()
        self.conv(self.other_staff)
        self.other_staff.delete()
        self.assertEqual(AssistantConversation.objects.count(), 1)
        self.event.delete()
        self.assertFalse(AssistantConversation.objects.exists())

    def test_one_conversation_per_event_and_user(self):
        from django.db import IntegrityError, transaction

        self.conv()
        with self.assertRaises(IntegrityError), transaction.atomic():
            AssistantConversation.objects.create(event=self.event, user=self.staff)

    @PLAIN_STATICFILES
    def test_admin_hides_message_text(self):
        from django.urls import reverse

        self.conv()
        ask(self.event, self.staff, "SECRET-CHAT-TEXT")
        self.client.force_login(self.staff)
        pk = AssistantConversation.objects.get().pk
        for url in (
            reverse("admin:assistant_assistantconversation_changelist"),
            reverse("admin:assistant_assistantconversation_change", args=[pk]),
        ):
            self.assertNotContains(self.client.get(url), "SECRET-CHAT-TEXT")
