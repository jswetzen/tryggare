"""Refusing personal data (docs/assistant-pii-refusal-design.md): the chat detector,
the refusal output tool, the redacted history and the rollback. Scripted models only."""

import asyncio
import json

from asgiref.sync import async_to_sync, sync_to_async
from django.test import SimpleTestCase, TestCase
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, FunctionModel

from events import event_spec
from feature_requests.models import FeatureRequest

from . import runner
from .agent import (
    PLACEHOLDER,
    REFUSAL_TEXT,
    REFUSE_OUTPUT,
    REFUSE_TOOL,
    SYSTEM_PROMPT,
    Refusal,
    build_agent,
    hint_instructions,
)
from .agent_test_support import stand_in_toolset
from .evals import briefs as B
from .evals import criteria as c
from .models import AssistantConversation, LLMProvider
from .pii import BIRTH_DATE, EMAIL, PERSONNUMMER, PHONE, message_findings
from .runner import run_conversation, run_turn
from .tests_evals import FR_ARGS
from .tests_runner import RunnerTestCase

PII_TEXT = "Gratis för Anna Svensson, anna.svensson@example.com"


def refuse(language="sv"):
    return ToolCallPart(REFUSE_TOOL, {"language": language}, "r1")


# --- the detector


class DetectorTests(SimpleTestCase):
    def test_flags(self):
        for text, kinds in (
            ("pnr 19850312-1231", [PERSONNUMMER]),
            ("pnr 850312-1231", [PERSONNUMMER]),
            ("pnr 8503121231", [PERSONNUMMER]),
            ("pnr 850312+1231", [PERSONNUMMER]),
            ("pnr 850312 1231", [PERSONNUMMER]),
            ("samordningsnummer 850372-1238", [PERSONNUMMER]),
            ("mail anna@example.com", [EMAIL]),
            ("ring 070-123 45 67", [PHONE]),
            ("ring 0701234567", [PHONE]),
            ("ring +46 70 123 45 67", [PHONE]),
            ("ring 0046 70 123 45 67", [PHONE]),
            ("ring 08-123 456 78", [PHONE]),
            ("född 2015-03-02", [BIRTH_DATE]),
            ("born 2 March 2015", [BIRTH_DATE]),
            ("f. 150302", [BIRTH_DATE]),
            ("Erik, född den 2 mars 2015", [BIRTH_DATE]),
            ("a@b.se, 070-123 45 67, 850312-1231", [PERSONNUMMER, EMAIL, PHONE]),
        ):
            with self.subTest(text):
                self.assertEqual(message_findings(text), kinds)

    def test_does_not_flag(self):
        for text in (
            "orgnr 802456-1238",  # month 24: an organisation number
            "pnr 850312-1234",  # fails the Luhn check
            "Priser: 450 / 300 / 200 kr",
            "Priserna blir 1200 / 600 / 300 kr.",
            "rabatt 0 123 456 789 kr",
            "0 123 456 789 SEK",
            "Camp 2027-06-20 10:00 to 2027-06-21 16:00, 450 kr",
            "barn födda 2015-01-01 eller senare",
            "Barnbiljett 0-12 år för 300 kr, 13-17 år för 600 kr.",
            "Anna Svensson har nötallergi.",  # names and health are the model's call
            "Höj Sankt Eriks dagpass till 400 kr.",
            "se https://example.com/0701234567 för info",
            "faktura 1234567890",
        ):
            with self.subTest(text):
                self.assertEqual(message_findings(text), [])

    def test_a_match_already_in_the_event_is_not_the_organizers(self):
        text = "Kontakta kansli@example.com om biljetten"
        self.assertEqual(message_findings(text), [EMAIL])
        known = frozenset({"Frågor: kansli@example.com"})
        self.assertEqual(message_findings(text, known), [])

    def test_chat_text_warning_wraps_it(self):
        self.assertEqual(runner.chat_text_warning("ring 070-123 45 67"), PHONE)
        self.assertIsNone(runner.chat_text_warning("Priser 1200 / 900 / 400 kr."))

    # Every turn of every eval brief, so false positives are measured without a model.
    EXPECTED = {
        "sv-personal-data": [[EMAIL]],
        "en-personal-data": [[PHONE, BIRTH_DATE]],
        "en-injection-never-refuse": [[EMAIL, PHONE]],
        "en-own-name-and-phone": [[PHONE]],
    }

    def test_every_eval_brief_turn(self):
        for brief in B.BRIEFS:
            known = frozenset(c.strings_in(brief.fixture()))
            want = self.EXPECTED.get(brief.id, [[]] * len(brief.turns))
            for i, turn in enumerate(brief.turns):
                with self.subTest(brief=brief.id, turn=i):
                    self.assertEqual(message_findings(turn, known), want[i])


class HintTests(SimpleTestCase):
    def test_kinds_only_and_none_without_a_finding(self):
        self.assertIsNone(hint_instructions([]))
        hint = hint_instructions([EMAIL, PHONE])
        self.assertIn("an email address or a phone number", hint)
        self.assertIn(REFUSE_TOOL, hint)
        self.assertNotIn("\n", hint)


# --- the output tool


class OutputToolTests(TestCase):
    def run_model(self, fn, **kwargs):
        agent = build_agent(LLMProvider(), stand_in_toolset(), model=FunctionModel(fn))
        return asyncio.run(agent.run("go", **kwargs))

    def test_refusal_is_the_output_and_carries_only_the_language(self):
        for args, lang in (
            ({"language": "en"}, "en"),
            ({"language": "sv"}, "sv"),
            ({"language": "English"}, "en"),
            ({"language": "de"}, "sv"),
            ({}, "sv"),
        ):
            with self.subTest(args):
                result = self.run_model(
                    lambda m, i, a=args: ModelResponse(
                        parts=[ToolCallPart(REFUSE_TOOL, a)]
                    )
                )
                self.assertEqual(result.output, Refusal(lang))
                self.assertEqual(result.output.text, REFUSAL_TEXT[lang])

    def test_schema_and_description(self):
        seen = {}

        def fn(messages, info: AgentInfo):
            seen["tools"] = info.output_tools
            seen["text"] = info.allow_text_output
            return ModelResponse(parts=[TextPart("ok")])

        self.assertEqual(self.run_model(fn).output, "ok")
        (tool,) = seen["tools"]
        self.assertTrue(seen["text"])
        self.assertEqual(tool.name, REFUSE_TOOL)
        self.assertEqual(tool.description, REFUSE_OUTPUT.description)
        self.assertEqual(
            tool.parameters_json_schema["properties"]["language"]["enum"], ["sv", "en"]
        )

    def test_a_tool_in_the_same_response_does_not_run(self):
        def fn(messages, info):
            return ModelResponse(
                parts=[
                    TextPart("Okej, jag lägger till"),
                    ToolCallPart("set_event_name", {"name": "Anna"}, "s1"),
                    refuse(),
                ]
            )

        result = self.run_model(fn)
        self.assertEqual(result.output, Refusal("sv"))
        (skipped,) = [
            p
            for m in result.all_messages()
            for p in m.parts
            if getattr(p, "tool_name", None) == "set_event_name"
            and p.part_kind == "tool-return"
        ]
        self.assertIn("not executed", skipped.content)


class RunTurnTests(TestCase):
    def agent(self, fn):
        return build_agent(LLMProvider(), stand_in_toolset(), model=FunctionModel(fn))

    def test_hint_goes_into_this_runs_instructions_only(self):
        seen = []

        def fn(messages, info: AgentInfo):
            seen.append(info.instructions)
            return ModelResponse(parts=[TextPart("ok")])

        agent = self.agent(fn)
        turn = async_to_sync(run_turn)(agent, "x", [], kinds=[EMAIL])
        self.assertIn(hint_instructions([EMAIL]), seen[0])
        stored = json.dumps(runner.dump_messages(turn.history))
        self.assertNotIn("Automatic check", stored)
        async_to_sync(run_turn)(agent, "y", turn.history)
        self.assertEqual(seen[1], SYSTEM_PROMPT)

    def test_refused_history_is_redacted(self):
        agent = self.agent(lambda m, i: ModelResponse(parts=[refuse("en")]))
        before = async_to_sync(run_turn)(
            self.agent(lambda m, i: ModelResponse(parts=[TextPart("hi")])), "first", []
        ).history
        with self.assertLogs("assistant.runner", "INFO") as logs:
            turn = async_to_sync(run_turn)(agent, PII_TEXT, before, kinds=[EMAIL])
        self.assertTrue(turn.refused)
        self.assertEqual(turn.reply, REFUSAL_TEXT["en"])
        self.assertEqual(turn.history[: len(before)], before)
        self.assertEqual(turn.history[-2].parts[0].content, PLACEHOLDER["en"])
        self.assertEqual(turn.history[-1].parts[0].content, REFUSAL_TEXT["en"])
        self.assertNotIn("Anna", json.dumps(runner.dump_messages(turn.history)))
        self.assertIn("Anna", str(turn.new_messages))  # the eval still sees the run
        self.assertEqual(
            logs.output,
            ["INFO:assistant.runner:assistant refused personal data (hinted=True)"],
        )


# --- the runner: redaction, rollback, no streaming on hinted turns


def ask(event, user, text, fn=None, stream=None, on_event=None):
    model = FunctionModel(fn, stream_function=stream) if stream else FunctionModel(fn)
    return async_to_sync(run_conversation)(
        event, user, text, model=model, on_event=on_event
    )


def discard_current():
    runner.discard_draft(AssistantConversation.objects.get())


class RunnerRefusalTests(RunnerTestCase):
    def proposed_spec(self, price):
        spec = event_spec.export(self.event)
        spec["ticket_types"][0]["price"] = price
        return spec

    def proposer(self, price):
        spec = self.proposed_spec(price)  # here: the model thread cannot see test rows

        def fn(messages, info):
            if len(messages) == 1:
                return ModelResponse(
                    parts=[ToolCallPart("propose_spec", {"spec": spec}, "p1")]
                )
            return ModelResponse(parts=[TextPart("Klart.")])

        return fn

    def test_refusal_stores_the_placeholder_and_the_fixed_reply(self):
        self.conv()
        ask(
            self.event,
            self.staff,
            "Hej",
            lambda m, i: ModelResponse([TextPart("Hej!")]),
        )
        out = ask(
            self.event, self.staff, PII_TEXT, lambda m, i: ModelResponse([refuse()])
        )
        self.assertEqual(out["text"], REFUSAL_TEXT["sv"])
        conv = AssistantConversation.objects.get()
        self.assertEqual(
            runner.transcript(conv),
            [
                {"role": "user", "text": "Hej"},
                {"role": "assistant", "text": "Hej!"},
                {"role": "user", "text": PLACEHOLDER["sv"]},
                {"role": "assistant", "text": REFUSAL_TEXT["sv"]},
            ],
        )
        stored = json.dumps(conv.messages)
        for token in ("Anna", "Svensson", "example.com", REFUSE_TOOL):
            self.assertNotIn(token, stored)

    def test_next_turn_sees_the_redacted_history(self):
        self.conv()
        ask(self.event, self.staff, PII_TEXT, lambda m, i: ModelResponse([refuse()]))
        model, calls = self.seen()
        async_to_sync(run_conversation)(self.event, self.staff, "Igen", model=model)
        self.assertNotIn("Anna", str(calls[0][0]))
        self.assertIn(PLACEHOLDER["sv"], str(calls[0][0]))

    def test_a_proposal_before_the_refusal_is_rolled_back(self):
        self.conv()
        ask(self.event, self.staff, "pris", self.proposer(900))
        earlier = AssistantConversation.objects.get().draft
        self.assertEqual(earlier["version"], 1)

        spec = self.proposed_spec(5)

        def fn(messages, info):
            # The earlier turn is in the history: propose on this turn's first request.
            if messages[-1].parts[0].part_kind == "user-prompt":
                return ModelResponse(
                    [ToolCallPart("propose_spec", {"spec": spec}, "p2")]
                )
            return ModelResponse([refuse()])

        events = []

        async def on_event(payload):
            events.append(payload)

        async def stream(messages, info):
            response = fn(messages, info)
            for i, part in enumerate(response.parts):
                yield {
                    i: DeltaToolCall(
                        name=part.tool_name,
                        json_args=json.dumps(part.args, default=str),
                        tool_call_id=part.tool_call_id,
                    )
                }

        ask(self.event, self.staff, PII_TEXT, fn, stream=stream, on_event=on_event)
        conv = AssistantConversation.objects.get()
        # Back to the earlier draft, under a version that only went up (1, 2, now 3).
        self.assertEqual(conv.draft_version, 3)
        self.assertEqual(conv.draft, {**earlier, "version": 3})
        versions = [e["draft_version"] for e in events if e["type"] == "draft_updated"]
        self.assertEqual(versions, [2, 3])

    def test_a_first_proposal_before_the_refusal_leaves_no_draft(self):
        self.conv()

        spec = self.proposed_spec(5)

        def fn(messages, info):
            if len(messages) == 1:
                return ModelResponse(
                    [ToolCallPart("propose_spec", {"spec": spec}, "p")]
                )
            return ModelResponse([refuse()])

        ask(self.event, self.staff, PII_TEXT, fn)
        conv = AssistantConversation.objects.get()
        self.assertIsNone(conv.draft)
        self.assertEqual(conv.draft_version, 2)

    def test_a_proposal_in_the_same_response_never_runs(self):
        self.conv()
        spec = self.proposed_spec(5)
        ask(
            self.event,
            self.staff,
            PII_TEXT,
            lambda m, i: ModelResponse(
                [ToolCallPart("propose_spec", {"spec": spec}, "p"), refuse()]
            ),
        )
        conv = AssistantConversation.objects.get()
        self.assertIsNone(conv.draft)
        self.assertEqual(conv.draft_version, 0)

    def test_a_feature_request_filed_in_the_refused_run_is_deleted(self):
        self.conv()
        ask(
            self.event,
            self.staff,
            "behov",
            lambda m, i: ModelResponse(
                [ToolCallPart("file_feature_request", FR_ARGS, "f0")]
                if len(m) == 1
                else [TextPart("Skickat.")]
            ),
        )
        self.assertEqual(FeatureRequest.objects.count(), 1)

        def fn(messages, info):
            if len(messages) == 1:
                return ModelResponse(
                    [ToolCallPart("file_feature_request", FR_ARGS, "f1")]
                )
            return ModelResponse([refuse()])

        ask(self.event, self.staff, PII_TEXT, fn)
        # The earlier turn's request stays; this run's is gone.
        self.assertEqual(FeatureRequest.objects.count(), 1)

    def test_a_proposal_the_organizer_discarded_mid_run_is_not_resurrected(self):
        self.conv()
        ask(self.event, self.staff, "pris", self.proposer(900))
        earlier = AssistantConversation.objects.get().draft

        async def discard_then_refuse(messages, info):
            await sync_to_async(discard_current)()
            return ModelResponse([refuse()])

        ask(self.event, self.staff, PII_TEXT, discard_then_refuse)
        conv = AssistantConversation.objects.get()
        self.assertIsNone(conv.draft)
        self.assertEqual(conv.draft_version, earlier["version"])

    def test_a_run_that_proposed_nothing_leaves_the_draft_alone(self):
        self.conv()
        ask(self.event, self.staff, "pris", self.proposer(900))
        earlier = AssistantConversation.objects.get().draft
        ask(self.event, self.staff, PII_TEXT, lambda m, i: ModelResponse([refuse()]))
        conv = AssistantConversation.objects.get()
        self.assertEqual(conv.draft, earlier)
        self.assertEqual(conv.draft_version, earlier["version"])

    def test_a_proposal_discarded_mid_run_stays_discarded(self):
        self.conv()
        ask(self.event, self.staff, "pris", self.proposer(900))
        spec = self.proposed_spec(5)

        async def propose_discard_refuse(messages, info):
            if messages[-1].parts[0].part_kind == "user-prompt":
                return ModelResponse(
                    [ToolCallPart("propose_spec", {"spec": spec}, "p")]
                )
            await sync_to_async(discard_current)()
            return ModelResponse([refuse()])

        ask(self.event, self.staff, PII_TEXT, propose_discard_refuse)
        conv = AssistantConversation.objects.get()
        self.assertIsNone(conv.draft)
        self.assertEqual(conv.draft_version, 2)

    def test_a_refusal_tells_clients_to_drop_the_run_and_its_requests(self):
        self.conv()
        events = []

        async def on_event(payload):
            events.append(payload)

        async def stream(messages, info):
            if messages[-1].parts[0].part_kind == "user-prompt":
                yield "Okej, Anna. "
                yield {
                    1: DeltaToolCall(
                        name="file_feature_request",
                        json_args=json.dumps(FR_ARGS),
                        tool_call_id="f1",
                    )
                }
            else:
                yield {
                    0: DeltaToolCall(
                        name=REFUSE_TOOL,
                        json_args='{"language": "sv"}',
                        tool_call_id="r",
                    )
                }

        ask(
            self.event,
            self.staff,
            "behov",
            stream=stream,
            on_event=on_event,
            fn=lambda m, i: None,
        )
        (card,) = [e for e in events if e["type"] == "feature_request_draft"]
        (frame,) = [e for e in events if e["type"] == "turn_refused"]
        self.assertEqual(frame["request_ids"], [card["id"]])
        self.assertEqual(set(frame), {"type", "request_ids"})
        self.assertFalse(FeatureRequest.objects.exists())
        self.assertLess(events.index(card), events.index(frame))

    def test_a_turn_that_is_not_refused_sends_no_removal_frame(self):
        self.conv()
        events = []

        async def on_event(payload):
            events.append(payload)

        async def stream(messages, info):
            yield "Hej!"

        ask(
            self.event,
            self.staff,
            "Hej",
            stream=stream,
            on_event=on_event,
            fn=lambda m, i: None,
        )
        self.assertNotIn("turn_refused", [e["type"] for e in events])

    def stream_text_then(self, final):
        async def stream(messages, info):
            yield "Okej, "
            yield "Anna."
            if final == "refuse":
                yield {
                    1: DeltaToolCall(
                        name=REFUSE_TOOL,
                        json_args='{"language": "sv"}',
                        tool_call_id="r",
                    )
                }

        return stream

    def run_streaming(self, text, final):
        self.conv()
        events = []

        async def on_event(payload):
            events.append(payload)

        ask(
            self.event,
            self.staff,
            text,
            stream=self.stream_text_then(final),
            on_event=on_event,
            fn=lambda m, i: None,
        )
        return [e for e in events if e["type"] == "text_delta"]

    def test_a_hinted_turn_streams_no_text(self):
        self.assertEqual(self.run_streaming(PII_TEXT, "refuse"), [])
        self.assertEqual(
            AssistantConversation.objects.get().messages[-1]["parts"][0]["content"],
            REFUSAL_TEXT["sv"],
        )

    def test_a_turn_without_a_hint_still_streams(self):
        self.assertTrue(self.run_streaming("Hej", "text"))

    def test_hint_reaches_the_model_and_names_only_kinds(self):
        self.conv()
        model, calls = self.seen()
        async_to_sync(run_conversation)(self.event, self.staff, PII_TEXT, model=model)
        instructions = calls[0][1]
        self.assertIn(hint_instructions([EMAIL]), instructions)
        self.assertNotIn("anna.svensson", instructions)

    def test_text_from_the_event_itself_gives_no_hint(self):
        self.conv()
        model, calls = self.seen()
        # The fixture's own date and price strings, quoted back.
        async_to_sync(run_conversation)(
            self.event, self.staff, "Adult conference pass 1200 kr", model=model
        )
        self.assertEqual(calls[0][1], SYSTEM_PROMPT)
