import asyncio
import json
import logging
from unittest import mock

from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.routing import URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from pydantic_ai.messages import ModelResponse, TextPart, ThinkingPart
from pydantic_ai.models.function import DeltaToolCall, FunctionModel

from accounts.models import AdminUser
from config.asgi import application
from config.routing import websocket_urlpatterns
from events import event_spec
from events.spec_test_support import at_now

from . import runner
from .consumers import AssistantConsumer
from .models import AssistantConversation, AssistantRun, LLMProvider

ROUTER = URLRouter(websocket_urlpatterns)
TERMINAL = ("run_finished", "run_failed")


def streaming(script):
    """A model whose requests are scripted: each step is a text, or ``(tool, args)``."""
    steps = iter(script)

    async def stream(messages, info):
        step = next(steps)
        if isinstance(step, str):
            for word in step.split(" "):
                yield word + " "
        else:
            name, args = step
            yield {
                0: DeltaToolCall(
                    name=name,
                    json_args=json.dumps(args, default=str),
                    tool_call_id=f"call-{name}",
                )
            }

    return FunctionModel(stream_function=stream)


class AssistantFixture:
    """Event, staff user, enabled provider and an accepted-notice conversation."""

    def setUp(self):
        self.staff = AdminUser.objects.create_superuser("wsstaff", "pw12345")
        with at_now():
            self.event = event_spec.apply(event_spec.example_spec())[0]
        provider = LLMProvider.load()
        provider.enabled = True
        provider.save()
        AssistantConversation.objects.create(
            event=self.event, user=self.staff, notice_accepted_at=timezone.now()
        )
        self.open = []
        self.good = event_spec.export(self.event)
        self.good["ticket_types"][0]["price"] = 999
        self.bad = event_spec.export(self.event)
        self.bad["ticket_types"][0]["price"] = -5

    def tearDown(self):
        # A task left running would hold the per-process registry across tests.
        runner._RUNS.clear()

    def communicator(self, user=None, event=None):
        c = WebsocketCommunicator(
            ROUTER, f"/ws/assistant/events/{(event or self.event).pk}/"
        )
        c.scope["user"] = user or self.staff
        self.open.append(c)
        return c

    async def connect(self, user=None, event=None):
        c = self.communicator(user, event)
        ok, code = await c.connect()
        self.assertTrue(ok, code)
        return c

    async def until_done(self, c):
        out = []
        while True:
            msg = await c.receive_json_from(timeout=10)
            out.append(msg)
            if msg["type"] in TERMINAL:
                return out

    async def say(self, c, text="hi", id="c-1"):
        await c.send_json_to({"type": "user_message", "id": id, "text": text})

    async def close_all(self):
        for c in self.open:
            await c.disconnect()


class AssistantWSBase(AssistantFixture, TransactionTestCase):
    # Real transactions: channels' database_sync_to_async closes its connection after
    # each call, which a TestCase transaction cannot survive. The flush per test is the
    # cost; tests that need no consumer use TestCase (see below).
    pass


class ConnectTests(AssistantWSBase):
    async def code(self, user=None, event_id=None):
        c = WebsocketCommunicator(
            ROUTER, f"/ws/assistant/events/{event_id or self.event.pk}/"
        )
        if user is not False:
            c.scope["user"] = user or self.staff
        ok, code = await c.connect()
        self.assertFalse(ok)
        return code

    async def test_ready(self):
        c = await self.connect()
        ready = await c.receive_json_from()
        conv = await sync_to_async(AssistantConversation.objects.get)()
        self.assertEqual(
            ready,
            {
                "type": "ready",
                "conversation_id": str(conv.id),
                "running": False,
                "draft_version": 0,
                "notice_required": False,
            },
        )
        await self.close_all()

    async def test_unauthenticated_4401(self):
        from django.contrib.auth.models import AnonymousUser

        self.assertEqual(await self.code(AnonymousUser()), 4401)

    async def test_no_permission_4403(self):
        plain = await database_sync_to_async(get_user_model().objects.create_user)(
            "plain", password="pw12345"
        )
        self.assertEqual(await self.code(plain), 4403)

    async def test_wrong_event_4404(self):
        self.assertEqual(
            await self.code(event_id="00000000-0000-4000-8000-000000000000"), 4404
        )

    async def test_ineligible_event_4409(self):
        blocker = [{"path": "", "code": "x", "message": "in use"}]
        with mock.patch(
            "assistant.permissions.event_spec.apply_blockers", return_value=blocker
        ):
            self.assertEqual(await self.code(), 4409)

    async def test_provider_disabled_4503(self):
        await sync_to_async(LLMProvider.objects.update)(enabled=False)
        self.assertEqual(await self.code(), 4503)

    async def test_non_staff_cannot_probe_event_ids(self):
        plain = await database_sync_to_async(get_user_model().objects.create_user)(
            "plain2", password="pw12345"
        )
        missing = await self.code(plain, "00000000-0000-4000-8000-000000000000")
        self.assertEqual(missing, 4403)

    async def test_conversation_is_derived_from_the_user(self):
        other = await database_sync_to_async(AdminUser.objects.create_superuser)(
            "wsstaff2", "pw12345"
        )
        c = await self.connect(other)
        ready = await c.receive_json_from()
        mine = await sync_to_async(AssistantConversation.objects.get)(user=self.staff)
        self.assertNotEqual(ready["conversation_id"], str(mine.id))
        self.assertTrue(ready["notice_required"])
        await self.close_all()

    async def test_dead_run_is_reset_on_connect(self):
        await sync_to_async(AssistantConversation.objects.update)(
            status="running",
            run_started_at=timezone.now() - timezone.timedelta(hours=1),
        )
        c = await self.connect()
        self.assertFalse((await c.receive_json_from())["running"])
        await self.close_all()

    async def test_live_run_is_reported_running(self):
        await sync_to_async(AssistantConversation.objects.update)(
            status="running", run_started_at=timezone.now()
        )
        c = await self.connect()
        self.assertTrue((await c.receive_json_from())["running"])
        await self.close_all()


class OriginTests(AssistantWSBase):
    async def test_foreign_origin_is_refused_before_the_consumer(self):
        with override_settings(ALLOWED_HOSTS=["testserver"]):
            guarded = AllowedHostsOriginValidator(ROUTER)
        c = WebsocketCommunicator(
            guarded,
            f"/ws/assistant/events/{self.event.pk}/",
            headers=[(b"origin", b"http://evil.example")],
        )
        c.scope["user"] = self.staff
        ok, _ = await c.connect()
        self.assertFalse(ok)

    async def test_deployed_stack_rejects_a_session_less_client(self):
        c = WebsocketCommunicator(
            application,
            f"/ws/assistant/events/{self.event.pk}/",
            headers=[(b"origin", b"http://testserver")],
        )
        ok, code = await c.connect()
        self.assertFalse(ok)
        self.assertEqual(code, 4401)


class RunTests(AssistantWSBase):
    async def run_script(self, script, c=None, text="make it 999"):
        c = c or await self.connect()
        await c.receive_json_from()  # ready
        with mock.patch.object(AssistantConsumer, "model", streaming(script)):
            await self.say(c, text)
            return c, await self.until_done(c)

    async def test_full_run_in_order_without_leaking_content(self):
        c, events = await self.run_script(
            [("propose_spec", {"spec": self.good}), "All set now"]
        )
        types = [e["type"] for e in events]
        self.assertEqual(types[0], "run_started")
        self.assertEqual(
            [t for t in types if t != "text_delta"],
            [
                "run_started",
                "tool_started",
                "tool_finished",
                "draft_updated",
                "run_finished",
            ],
        )
        self.assertLess(types.index("draft_updated"), types.index("run_finished"))
        self.assertEqual(events[0]["reply_to"], "c-1")
        run_ids = {e["run_id"] for e in events}
        self.assertEqual(len(run_ids), 1)
        tool = events[types.index("tool_finished")]
        self.assertEqual((tool["tool"], tool["ok"]), ("propose_spec", True))
        self.assertEqual(events[types.index("draft_updated")]["draft_version"], 1)
        self.assertEqual(
            "".join(e["text"] for e in events if e["type"] == "text_delta"),
            "All set now ",
        )
        # Only protocol fields: no tool arguments, results or spec.
        allowed = {"type", "run_id", "reply_to", "call_id", "tool", "ok", "text"}
        allowed.add("draft_version")
        for e in events:
            self.assertLessEqual(set(e), allowed)
        self.assertNotIn("999", json.dumps(events))
        conv = await sync_to_async(AssistantConversation.objects.get)()
        self.assertEqual((conv.status, conv.draft["version"]), ("idle", 1))
        await self.close_all()

    async def test_failed_tool_reports_not_ok_and_no_draft_update(self):
        _, events = await self.run_script(
            [("propose_spec", {"spec": self.bad}), "Could not do it"]
        )
        finished = [e for e in events if e["type"] == "tool_finished"]
        self.assertFalse(finished[0]["ok"])
        self.assertNotIn("draft_updated", [e["type"] for e in events])
        self.assertEqual(events[-1]["type"], "run_finished")
        await self.close_all()

    async def test_second_connection_gets_the_same_events(self):
        a = await self.connect()
        b = await self.connect()
        await b.receive_json_from()
        _, mine = await self.run_script(["Hello there"], c=a)
        theirs = await self.until_done(b)
        self.assertEqual(mine, theirs)
        await self.close_all()

    async def test_second_message_while_running_is_busy(self):
        gate = asyncio.Event()

        async def stream(messages, info):
            await gate.wait()
            yield "done"

        c = await self.connect()
        await c.receive_json_from()
        with mock.patch.object(
            AssistantConsumer, "model", FunctionModel(stream_function=stream)
        ):
            await self.say(c, id="c-1")
            self.assertEqual((await c.receive_json_from())["type"], "run_started")
            await self.say(c, id="c-2")
            busy = await c.receive_json_from()
            self.assertEqual(
                busy,
                {
                    "type": "run_failed",
                    "run_id": None,
                    "reply_to": "c-2",
                    "code": "busy",
                },
            )
            gate.set()
            events = await self.until_done(c)
        self.assertEqual(events[-1]["type"], "run_finished")
        await self.close_all()

    async def test_cancel_after_start_stops_the_run_and_frees_the_lock(self):
        async def stream(messages, info):
            await asyncio.sleep(30)
            yield "never"

        c = await self.connect()
        await c.receive_json_from()
        with mock.patch.object(
            AssistantConsumer, "model", FunctionModel(stream_function=stream)
        ):
            await self.say(c)
            await c.receive_json_from()
            await c.send_json_to({"type": "cancel"})
            events = await self.until_done(c)
        self.assertEqual(events[-1]["code"], "cancelled")
        conv = await sync_to_async(AssistantConversation.objects.get)()
        self.assertEqual(conv.status, "idle")
        self.assertEqual(conv.messages, [])
        await self.close_all()

    async def test_cancel_with_nothing_running_is_ignored(self):
        c = await self.connect()
        await c.receive_json_from()
        await c.send_json_to({"type": "cancel"})
        self.assertTrue(await c.receive_nothing(timeout=0.3))
        await self.close_all()

    async def test_run_survives_the_sender_disconnecting(self):
        gate = asyncio.Event()

        async def stream(messages, info):
            await gate.wait()
            yield "still here"

        a = await self.connect()
        await a.receive_json_from()
        with mock.patch.object(
            AssistantConsumer, "model", FunctionModel(stream_function=stream)
        ):
            await self.say(a)
            await a.receive_json_from()
            await a.disconnect()
            b = await self.connect()
            self.assertTrue((await b.receive_json_from())["running"])
            gate.set()
            events = await self.until_done(b)
        self.assertEqual(events[-1]["type"], "run_finished")
        await self.close_all()

    async def test_revoked_between_messages_is_blocked(self):
        c, events = await self.run_script(["one"])
        self.assertEqual(events[-1]["type"], "run_finished")
        await sync_to_async(AdminUser.objects.update)(is_active=False)
        await self.say(c, id="c-2")
        self.assertEqual(
            await c.receive_json_from(),
            {
                "type": "run_failed",
                "run_id": None,
                "reply_to": "c-2",
                "code": "blocked",
            },
        )
        await self.close_all()

    async def test_model_chosen_tool_names_and_ids_are_not_forwarded(self):
        async def stream(messages, info):
            if len(messages) == 1:
                yield {
                    0: DeltaToolCall(
                        name="Anna Svensson 19800101-1234",
                        json_args="{}",
                        tool_call_id="call-Anna",
                    )
                }
            else:
                yield "ok"

        c = await self.connect()
        await c.receive_json_from()
        with mock.patch.object(
            AssistantConsumer, "model", FunctionModel(stream_function=stream)
        ):
            await self.say(c)
            events = await self.until_done(c)
        self.assertNotIn("Anna", json.dumps(events))
        tools = [e for e in events if e["type"].startswith("tool_")]
        self.assertTrue(tools)
        for e in tools:
            self.assertEqual((e["tool"], e["call_id"]), ("unknown", "t-1"))
        await self.close_all()

    async def test_clear_mid_run_ends_it_at_the_next_tool_call(self):
        gate = asyncio.Event()

        async def stream(messages, info):
            if len(messages) == 1:
                await gate.wait()
                yield {0: DeltaToolCall(name="get_current_spec", json_args="{}")}
            else:
                yield "should not get here"

        c = await self.connect()
        await c.receive_json_from()
        with mock.patch.object(
            AssistantConsumer, "model", FunctionModel(stream_function=stream)
        ):
            await self.say(c)
            self.assertEqual((await c.receive_json_from())["type"], "run_started")
            conv = await sync_to_async(AssistantConversation.objects.get)()
            await sync_to_async(runner.clear_conversation)(conv)
            gate.set()
            events = await self.until_done(c)
        self.assertEqual(events[-1]["code"], "cancelled")
        self.assertNotIn("should not get here", json.dumps(events))
        conv = await sync_to_async(AssistantConversation.objects.get)()
        self.assertEqual((conv.status, conv.messages), ("idle", []))
        await self.close_all()

    async def test_revoked_mid_run_is_blocked(self):
        async def stream(messages, info):
            if len(messages) == 1:
                yield {
                    0: DeltaToolCall(
                        name="get_current_spec", json_args="{}", tool_call_id="g"
                    )
                }
            else:
                yield "unreachable"

        c = await self.connect()
        await c.receive_json_from()
        real = runner._permission_guard

        def guard_after_revoke(*a):
            check = real(*a)

            def go():
                AdminUser.objects.update(is_active=False)
                check()

            return go

        with (
            mock.patch.object(
                AssistantConsumer, "model", FunctionModel(stream_function=stream)
            ),
            mock.patch("assistant.runner._permission_guard", guard_after_revoke),
        ):
            await self.say(c)
            events = await self.until_done(c)
        self.assertEqual(events[-1]["code"], "blocked")
        self.assertEqual(events[-1]["run_id"], events[0]["run_id"])
        conv = await sync_to_async(AssistantConversation.objects.get)()
        self.assertEqual(conv.status, "idle")
        await self.close_all()

    async def test_notice_required(self):
        await sync_to_async(AssistantConversation.objects.update)(
            notice_accepted_at=None
        )
        c = await self.connect()
        self.assertTrue((await c.receive_json_from())["notice_required"])
        await self.say(c)
        self.assertEqual((await c.receive_json_from())["code"], "notice_required")
        await self.close_all()

    async def test_provider_disabled_after_connect_is_not_enabled(self):
        c = await self.connect()
        await c.receive_json_from()
        await sync_to_async(LLMProvider.objects.update)(enabled=False)
        await self.say(c)
        self.assertEqual((await c.receive_json_from())["code"], "not_enabled")
        await self.close_all()

    @override_settings(ASSISTANT_RUNS_PER_HOUR=1)
    async def test_rate_limited(self):
        c, _ = await self.run_script(["one"])
        await self.say(c, id="c-2")
        refused = await c.receive_json_from()
        self.assertEqual(refused["code"], "rate_limited")
        self.assertIsNone(refused["run_id"])
        await self.close_all()

    async def test_blocked_run_does_not_use_a_rate_limit_slot(self):
        plain = await database_sync_to_async(get_user_model().objects.create_user)(
            "plain3", password="pw12345"
        )
        # Reaches the runner directly: the consumer would already refuse this user.
        with self.assertRaises(runner.RunFailed) as cm:
            await runner.run_conversation(
                self.event, plain, "x", model=streaming(["hi"])
            )
        self.assertEqual(cm.exception.code, "blocked")
        self.assertEqual(await sync_to_async(AssistantRun.objects.count)(), 0)

    async def test_bad_frames(self):
        c = await self.connect()
        await c.receive_json_from()
        for frame in [
            "not json",
            "[]",
            json.dumps({"type": "nope"}),
            json.dumps({"type": "user_message", "id": "x", "text": "  "}),
            json.dumps({"type": "user_message", "text": "hi"}),
            json.dumps({"type": "user_message", "id": "x", "text": "a" * 5000}),
            json.dumps({"type": "user_message", "id": 5, "text": "hi"}),
            json.dumps({"type": "user_message", "id": "x", "text": "hi" + " " * 20000}),
        ]:
            await c.send_to(text_data=frame)
            self.assertEqual(
                await c.receive_json_from(), {"type": "error", "code": "bad_request"}
            )
        await self.close_all()

    async def test_failure_is_logged_with_type_only(self):
        def boom(messages, info):
            raise RuntimeError("secret chat text and provider body")

        async def stream(messages, info):
            boom(messages, info)
            yield "x"

        c = await self.connect()
        await c.receive_json_from()
        with (
            mock.patch.object(
                AssistantConsumer, "model", FunctionModel(stream_function=stream)
            ),
            self.assertLogs("assistant.runner", level=logging.WARNING) as logs,
        ):
            await self.say(c, text="secret chat text")
            events = await self.until_done(c)
        self.assertEqual(events[-1]["code"], "model_error")
        joined = "\n".join(logs.output)
        self.assertIn("RuntimeError", joined)
        self.assertNotIn("secret", joined)
        self.assertNotIn("secret", json.dumps(events))
        await self.close_all()


class PersonalDataWarningTests(AssistantWSBase):
    TEXT = "mail the list to anna.svensson@example.com please"

    async def send(self, c, **extra):
        await c.send_json_to(
            {"type": "user_message", "id": "c-9", "text": self.TEXT, **extra}
        )

    async def test_warns_the_sender_only_and_starts_no_run(self):
        a, b = await self.connect(), await self.connect()
        await a.receive_json_from()
        await b.receive_json_from()
        await self.send(a)
        warning = await a.receive_json_from()
        self.assertEqual(
            warning, {"type": "warning", "code": "personal_data", "reply_to": "c-9"}
        )
        self.assertNotIn("example.com", json.dumps(warning))
        self.assertTrue(await b.receive_nothing())
        self.assertEqual(await sync_to_async(AssistantRun.objects.count)(), 0)
        conv = await sync_to_async(AssistantConversation.objects.get)()
        self.assertEqual((conv.status, conv.messages), ("idle", []))
        await self.close_all()

    async def test_confirm_flag_sends_it_anyway(self):
        c = await self.connect()
        await c.receive_json_from()
        with mock.patch.object(AssistantConsumer, "model", streaming(["Fine "])):
            await self.send(c, confirm_personal_data=True)
            events = await self.until_done(c)
        self.assertEqual(events[0]["type"], "run_started")
        self.assertEqual(events[-1]["type"], "run_finished")
        await self.close_all()

    async def test_only_true_confirms(self):
        c = await self.connect()
        await c.receive_json_from()
        await self.send(c, confirm_personal_data="yes")
        self.assertEqual((await c.receive_json_from())["type"], "warning")
        await self.close_all()

    async def test_clean_text_needs_no_confirmation(self):
        c = await self.connect()
        await c.receive_json_from()
        with mock.patch.object(AssistantConsumer, "model", streaming(["ok "])):
            await self.say(c, "a two day camp for ages 12 to 17")
            events = await self.until_done(c)
        self.assertEqual(events[0]["type"], "run_started")
        await self.close_all()

    async def test_permission_is_checked_before_the_warning(self):
        c = await self.connect()
        await c.receive_json_from()
        await sync_to_async(AdminUser.objects.filter(pk=self.staff.pk).update)(
            is_superuser=False
        )
        await self.send(c)
        self.assertEqual((await c.receive_json_from())["code"], "blocked")
        await self.close_all()


class GroupCancelTests(AssistantWSBase):
    async def test_clear_endpoint_message_cancels_the_run_in_this_process(self):
        from channels.layers import get_channel_layer

        gate = asyncio.Event()

        async def stream(messages, info):
            await gate.wait()
            yield "never"

        c = await self.connect()
        await c.receive_json_from()
        with mock.patch.object(
            AssistantConsumer, "model", FunctionModel(stream_function=stream)
        ):
            await self.say(c)
            self.assertEqual((await c.receive_json_from())["type"], "run_started")
            conv = await sync_to_async(AssistantConversation.objects.get)()
            await get_channel_layer().group_send(
                runner.group_name(conv.id), {"type": "assistant.cancel"}
            )
            events = await self.until_done(c)
        self.assertEqual(events[-1]["code"], "cancelled")
        await self.close_all()


class CancelBeforeStartTests(AssistantFixture, TestCase):
    def test_cancel_before_the_lock_is_held_is_only_noted(self):
        task = mock.Mock()
        handle = runner._Handle(task=task, started=False)
        runner._RUNS[(self.event.pk, self.staff.pk)] = handle
        runner.request_cancel(self.event.pk, self.staff.pk)
        task.cancel.assert_not_called()
        self.assertTrue(handle.cancel_requested)
        handle.started = True
        runner.request_cancel(self.event.pk, self.staff.pk)
        task.cancel.assert_called_once()


class StorageRuleTests(AssistantFixture, TestCase):
    def test_thinking_parts_are_not_stored(self):
        msgs = [
            ModelResponse(parts=[ThinkingPart("secret reasoning"), TextPart("hi")]),
            ModelResponse(parts=[ThinkingPart("only reasoning")]),
        ]
        stored = runner.dump_messages(msgs)
        self.assertEqual(len(stored), 1)
        self.assertNotIn("secret reasoning", json.dumps(stored))

    def test_draft_version_is_monotonic_across_clear_and_discard(self):
        conv = AssistantConversation.objects.get()
        conv.status, conv.run_started_at = "running", timezone.now()
        conv.save()
        runner._store_draft(conv, "t1", {"spec": {}})
        runner._store_draft(conv, "t2", {"spec": {}})
        runner.discard_draft(conv)
        runner.clear_conversation(conv)
        conv.refresh_from_db()
        self.assertIsNone(conv.draft)
        self.assertEqual(conv.draft_version, 2)
        conv.status, conv.run_started_at = "running", timezone.now()
        conv.save()
        runner._store_draft(conv, "t3", {"spec": {}})
        conv.refresh_from_db()
        self.assertEqual(conv.draft["version"], 3)

    def test_clear_resets_run_state_with_messages_and_draft(self):
        conv = AssistantConversation.objects.get()
        AssistantConversation.objects.update(
            messages=[{"x": 1}],
            draft={"spec": {}, "version": 1},
            status="running",
            run_started_at=timezone.now(),
        )
        runner.clear_conversation(conv)
        conv.refresh_from_db()
        self.assertEqual(
            (conv.messages, conv.draft, conv.status, conv.run_started_at),
            ([], None, "idle", None),
        )
        self.assertIsNotNone(conv.notice_accepted_at)

    def test_reset_if_dead_leaves_a_newer_run_alone(self):
        stale = AssistantConversation.objects.get()
        stale.status = "running"
        stale.run_started_at = timezone.now() - timezone.timedelta(hours=1)
        stale.save()
        newer = timezone.now()
        AssistantConversation.objects.update(run_started_at=newer)
        self.assertFalse(runner.reset_if_dead(stale))
        row = AssistantConversation.objects.get()
        self.assertEqual((row.status, row.run_started_at), ("running", newer))
