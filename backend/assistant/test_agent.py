import asyncio
import json
from unittest import mock

import httpx2
from django.test import SimpleTestCase, TestCase
from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

from events.event_spec import CAPABILITIES

from .agent import (
    SYSTEM_PROMPT,
    build_agent,
    build_model,
    capabilities_summary,
    guarded_http_client,
    run_assistant,
    strip_orphan_think,
)
from .agent_test_support import stand_in_toolset
from .models import LLMProvider
from .providers import ProviderError, check_address
from .tools import TOOL_NAMES

GETADDRINFO = "assistant.providers.openai_compatible.socket.getaddrinfo"
BASE = "http://ollama.example:11434/v1"


def public_dns():
    return mock.patch(GETADDRINFO, return_value=[(2, 1, 6, "", ("93.184.216.34", 0))])


def completion(text="hi"):
    return {
        "id": "x",
        "object": "chat.completion",
        "created": 0,
        "model": "m",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": text},
            }
        ],
    }


class Recorder:
    def __init__(self, handler):
        self.requests = []
        self.transport = httpx2.MockTransport(self._handle)
        self._handler = handler

    def _handle(self, request):
        self.requests.append(request)
        return self._handler(request)


def provider(base_url=BASE, key="sekret"):
    p = LLMProvider(base_url=base_url, model="m")
    p.set_api_key(key)
    p.save()  # build_model reads the key from the saved row
    return p


class HttpGuardTests(TestCase):
    def run_agent(self, rec, base_url=BASE):
        client = guarded_http_client(base_url, transport=rec.transport)
        agent = Agent(build_model(provider(base_url), http_client=client))
        return asyncio.run(agent.run("hello"))

    def test_key_sent_to_saved_origin(self):
        rec = Recorder(lambda r: httpx2.Response(200, json=completion("ok")))
        with public_dns():
            result = self.run_agent(rec)
        self.assertEqual(result.output, "ok")
        self.assertEqual(rec.requests[0].headers["authorization"], "Bearer sekret")
        self.assertEqual(rec.requests[0].url.path, "/v1/chat/completions")

    def test_link_local_base_url_refused_before_any_request(self):
        rec = Recorder(lambda r: httpx2.Response(200, json=completion()))
        with self.assertRaises(Exception):
            self.run_agent(rec, base_url="http://169.254.169.254/v1")
        self.assertEqual(rec.requests, [])

    def test_link_local_via_dns_refused(self):
        rec = Recorder(lambda r: httpx2.Response(200, json=completion()))
        with mock.patch(
            GETADDRINFO, return_value=[(2, 1, 6, "", ("169.254.169.254", 0))]
        ):
            with self.assertRaises(Exception):
                self.run_agent(rec)
        self.assertEqual(rec.requests, [])

    def test_redirect_not_followed_and_key_not_leaked(self):
        rec = Recorder(
            lambda r: httpx2.Response(
                302, headers={"Location": "http://evil.example/steal"}
            )
        )
        with public_dns(), self.assertRaises(Exception):
            self.run_agent(rec)
        self.assertEqual([r.url.host for r in rec.requests], ["ollama.example"])

    def test_other_origin_request_refused_with_key_header(self):
        rec = Recorder(lambda r: httpx2.Response(200))
        client = guarded_http_client(BASE, transport=rec.transport)
        with public_dns(), self.assertRaises(Exception):
            asyncio.run(
                client.get(
                    "http://evil.example/x", headers={"Authorization": "Bearer sekret"}
                )
            )
        self.assertEqual(rec.requests, [])

    def test_follow_redirects_off_and_timeouts(self):
        client = guarded_http_client(BASE)
        self.assertFalse(client.follow_redirects)
        self.assertFalse(client._trust_env)
        self.assertEqual(client.timeout.connect, 3)

    def test_key_not_returned_for_a_different_origin(self):
        provider()
        mutated = LLMProvider.load()
        mutated.base_url = "http://evil.example/v1"
        self.assertEqual(build_model(mutated).client.api_key, "none")
        mutated.base_url = BASE
        self.assertEqual(build_model(mutated).client.api_key, "sekret")

    def test_unicode_and_punycode_hosts_are_one_origin(self):
        provider(base_url="http://bücher.example/v1")
        mutated = LLMProvider.load()
        mutated.base_url = "http://xn--bcher-kva.example/v1"
        self.assertEqual(build_model(mutated).client.api_key, "sekret")

    def test_sdk_retries_capped(self):
        self.assertEqual(build_model(provider()).client.max_retries, 1)

    def test_oversized_response_refused(self):
        rec = Recorder(lambda r: httpx2.Response(200, content=b"x" * 500))
        with (
            public_dns(),
            mock.patch("assistant.agent.MAX_RESPONSE_BYTES", 100),
            self.assertRaises(Exception),
        ):
            self.run_agent(rec)

    def test_no_key_uses_placeholder(self):
        rec = Recorder(lambda r: httpx2.Response(200, json=completion()))
        client = guarded_http_client(BASE, transport=rec.transport)
        with public_dns():
            asyncio.run(
                Agent(build_model(provider(key=""), http_client=client)).run("x")
            )
        self.assertEqual(rec.requests[0].headers["authorization"], "Bearer none")


class AgentWiringTests(TestCase):
    def test_testmodel_calls_every_tool_over_mcp(self):
        agent = build_agent(
            provider(),
            stand_in_toolset(),
            model=TestModel(call_tools=["get_capabilities", "set_event_name"]),
        )
        result = asyncio.run(agent.run("go"))
        names = {
            p.tool_name
            for m in result.all_messages()
            for p in m.parts
            if isinstance(p, ToolCallPart)
        }
        self.assertEqual(names, {"get_capabilities", "set_event_name"})

    def test_tool_error_reaches_model_which_retries(self):
        seen = []

        def model_fn(messages, info: AgentInfo):
            seen.append(messages)
            calls = sum(isinstance(p, ToolCallPart) for m in messages for p in m.parts)
            if calls == 0:
                return ModelResponse(
                    parts=[ToolCallPart("set_event_name", json.dumps({"name": " "}))]
                )
            if calls == 1:
                return ModelResponse(
                    parts=[ToolCallPart("set_event_name", {"name": "Summer Camp"})]
                )
            return ModelResponse(parts=[TextPart("done")])

        agent = build_agent(
            provider(), stand_in_toolset(), model=FunctionModel(model_fn)
        )
        result = asyncio.run(agent.run("name it"))
        self.assertEqual(result.output, "done")
        # The second model call saw the validation error text from the tool.
        self.assertIn("name must not be empty", str(seen[1]))


def calls(result):
    return [
        p.tool_name
        for m in result.all_messages()
        for p in m.parts
        if isinstance(p, ToolCallPart)
    ]


class RunAssistantTests(TestCase):
    def agent(self, model_fn):
        return build_agent(
            provider(), stand_in_toolset(), model=FunctionModel(model_fn)
        )

    def run_it(self, model_fn, **kwargs):
        return asyncio.run(run_assistant(self.agent(model_fn), "go", **kwargs))

    def test_retry_exhaustion_carries_transcript(self):
        def always_blank(messages, info):
            return ModelResponse(parts=[ToolCallPart("set_event_name", {"name": " "})])

        with self.assertRaises(UnexpectedModelBehavior) as caught:
            self.run_it(always_blank)
        self.assertIn("name must not be empty", str(caught.exception.transcript))

    def test_tool_call_limit(self):
        def forever(messages, info):
            return ModelResponse(parts=[ToolCallPart("get_capabilities", {})])

        with self.assertRaises(UsageLimitExceeded) as caught:
            self.run_it(forever, tool_calls_limit=3)
        self.assertTrue(caught.exception.transcript)

    def test_request_limit(self):
        def forever(messages, info):
            return ModelResponse(parts=[ToolCallPart("get_capabilities", {})])

        with self.assertRaises(UsageLimitExceeded):
            self.run_it(forever, request_limit=2, tool_calls_limit=100)

    def test_deadline(self):
        async def slow(messages, info):
            await asyncio.sleep(5)

        with self.assertRaises(TimeoutError) as caught:
            self.run_it(slow, deadline=0.05)
        self.assertEqual(caught.exception.transcript[0].parts[0].content, "go")

    def run_http(self, status):
        rec = Recorder(lambda r: httpx2.Response(status, text="secret body"))
        client = guarded_http_client(BASE, transport=rec.transport)
        agent = Agent(build_model(provider(), http_client=client))
        with public_dns():
            return asyncio.run(run_assistant(agent, "x"))

    def test_provider_errors_mapped_without_body(self):
        for status, code in ((401, "auth_failed"), (400, "http_error")):
            with self.subTest(status=status), self.assertRaises(ProviderError) as c:
                self.run_http(status)
            self.assertEqual(c.exception.code, code)
            self.assertNotIn("secret body", str(c.exception.as_dict()))

    def test_blocked_address_keeps_its_code(self):
        rec = Recorder(lambda r: httpx2.Response(200, json=completion()))
        base = "http://169.254.169.254/v1"
        client = guarded_http_client(base, transport=rec.transport)
        agent = Agent(build_model(provider(base_url=base), http_client=client))
        with self.assertRaises(ProviderError) as caught:
            asyncio.run(run_assistant(agent, "x"))
        self.assertEqual(caught.exception.code, "address_blocked")


class CheckAddressTests(SimpleTestCase):
    def blocked(self, ip):
        with mock.patch(GETADDRINFO, return_value=[(10, 1, 6, "", (ip, 0))]):
            with self.assertRaises(ProviderError) as caught:
                check_address("http://x.example/v1")
        return caught.exception.code

    def test_blocked_forms(self):
        for ip in (
            "169.254.169.254",
            "100.100.100.200",
            "fd00:ec2::254",
            "::ffff:169.254.169.254",
            "2002:a9fe:a9fe::1",
            "64:ff9b::a9fe:a9fe",
            "::a9fe:a9fe",
            "fe80::1",
        ):
            with self.subTest(ip=ip):
                self.assertEqual(self.blocked(ip), "address_blocked")

    def test_private_and_loopback_allowed(self):
        for ip in ("10.0.0.5", "127.0.0.1", "::1", "2002:0a00:0005::1"):
            with mock.patch(GETADDRINFO, return_value=[(2, 1, 6, "", (ip, 0))]):
                check_address("http://x.example/v1")

    def test_garbage_is_unreachable_not_a_crash(self):
        self.assertEqual(self.blocked("not-an-ip"), "unreachable")
        with self.assertRaises(ProviderError):
            check_address("http:///v1")


class CapabilitiesPromptTests(TestCase):
    """The capabilities list is in the prompt, so the model does not need a first call.
    Checked on the instructions a real run sends, not on the constant alone."""

    def sent_instructions(self) -> str:
        seen = {}

        def model_fn(messages, info: AgentInfo):
            seen["instructions"] = info.instructions
            return ModelResponse(parts=[TextPart("ok")])

        agent = build_agent(
            provider(), stand_in_toolset(), model=FunctionModel(model_fn)
        )
        asyncio.run(agent.run("go"))
        return seen["instructions"]

    def test_every_capability_id_is_sent(self):
        sent = self.sent_instructions()
        for cap in CAPABILITIES["supported"] + CAPABILITIES["unsupported"]:
            with self.subTest(id=cap["id"]):
                self.assertIn(f"- {cap['id']}:", sent)

    def test_closest_workarounds_and_notes_are_sent(self):
        sent = self.sent_instructions()
        for cap in CAPABILITIES["unsupported"]:
            if cap.get("closest"):
                with self.subTest(id=cap["id"]):
                    self.assertIn(cap["closest"], sent)
        for note in CAPABILITIES["notes"]:
            with self.subTest(note=note[:40]):
                self.assertIn(note, sent)

    def test_summary_is_compact(self):
        # About 580 tokens today. The full get_capabilities result is about 5k and
        # resent on every request, so a jump here means the prompt grew on purpose.
        self.assertLess(len(capabilities_summary()), 3000)
        # 4600: the unsupported-ask rule is spelled out (4500 before it, about 4540 with it).
        self.assertLess(len(SYSTEM_PROMPT), 4600)

    def test_prompt_has_no_concrete_dates(self):
        # A date in every request can be copied into a spec; the rules say never invent one.
        self.assertNotRegex(SYSTEM_PROMPT, r"\d{4}-\d{2}-\d{2}")

    def test_get_capabilities_stays_available_for_fields_and_schema(self):
        self.assertIn("get_capabilities", TOOL_NAMES)


class OrphanThinkTests(SimpleTestCase):
    def test_reasoning_before_a_bare_closer_is_dropped_and_logged(self):
        # The shape bonsai printed on Ollama: reasoning, a closer, the reply (twice over).
        text = "Jag tänker.\n</think>\n\nUtkast ett.\n</think>\n\nUtkastet är klart."
        with self.assertLogs("assistant.agent", "WARNING"):
            self.assertEqual(strip_orphan_think(text), "Utkastet är klart.")

    def test_other_text_is_left_alone(self):
        for text in ("Klart.", "<think>a</think>b", "Taggen </think> och <think>."):
            with self.subTest(text):
                self.assertEqual(strip_orphan_think(text), text)

    def test_nothing_after_the_closer_keeps_the_text(self):
        with self.assertLogs("assistant.agent", "WARNING"):
            self.assertEqual(strip_orphan_think("Klart.\n</think>\n"), "Klart.")
