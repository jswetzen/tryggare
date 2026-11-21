"""Eval criteria and harness, with scripted models: no live model in the suite."""

import copy
import json

from django.test import SimpleTestCase, TestCase
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from events import event_spec

from .evals import briefs as B
from .evals import criteria as c
from .evals.harness import run_brief, summarize
from .evals.report import build_report, render_markdown

BASE = event_spec.example_spec()


def outcome(reply="Klart.", drafts=(), calls=(), errors=None):
    return c.Outcome(
        replies=[reply] if isinstance(reply, str) else list(reply),
        drafts=list(drafts),
        tool_calls=list(calls),
        base=BASE,
        errors=errors,
    )


def failed(checks):
    return {x.name for x in checks if not x.ok}


class HygieneTests(SimpleTestCase):
    def test_draft_ids_tokens_and_internals_are_caught(self):
        for text in (
            "Jag la till det i draft 77caf39c…",
            "Draft id: a1b2c3d4e5f60718",
            "Utkast-id 123e4567-e89b-12d3-a456-426614174000",
            "Jag anropade propose_spec.",
            "Satte min_birthdate till 2023-06-19.",
            "Tog bort child-pass-13-17.",
            "Draft token ready.",
        ):
            with self.subTest(text):
                self.assertFalse(c.no_internal_ids(outcome(text)).ok)

    def test_the_proposed_token_in_a_reply_is_caught(self):
        draft = {"spec": BASE, "token": "9f8e7d6c5b4a3210", "diff": []}
        self.assertFalse(c.no_internal_ids(outcome("Ref 9f8e7d", [draft])).ok)

    def test_plain_replies_pass(self):
        for text in (
            "Jag har lagt till sessionen Avslutning, 2027-06-20 09:00–11:00.",
            "Early bird adult costs 850 SEK; the T-shirt is unchanged.",
        ):
            self.assertTrue(c.no_internal_ids(outcome(text)).ok, text)

    def test_times_must_be_hh_mm(self):
        bad = (
            "Sessionen går kl. 0–?",
            "Starts at 5 pm",
            "Börjar kl 17",
            "Börjar 9:00",
            "kl. ?–19:00",
            "Börjar kl 17.00",
            "Öppet 09.00-11.00",
        )
        good = (
            "Priset är 0.00 kr, inte 12.50.",
            "Is it ok?\n- yes\n- no",
            "Börjar 17:00–19:00.",
            "Open 09:00 to 11:00, price 1.200 kr",
            "Pris 850 kr.",
        )
        for text in bad:
            with self.subTest(text):
                self.assertFalse(c.times_24h(outcome(text)).ok)
        for text in good:
            with self.subTest(text):
                self.assertTrue(c.times_24h(outcome(text)).ok)

    def test_language(self):
        sv = "Jag har ändrat priset och lagt till en biljett för barn."
        en = "I have changed the price and added a ticket for the children."
        self.assertTrue(c.language_matches(outcome(sv), "sv").ok)
        self.assertFalse(c.language_matches(outcome(sv), "en").ok)
        self.assertTrue(c.language_matches(outcome(en), "en").ok)
        self.assertFalse(c.language_matches(outcome(en), "sv").ok)
        self.assertFalse(c.language_matches(outcome(""), "en").ok)

    def test_stray_foreign_script(self):
        self.assertFalse(c.no_foreign_script(outcome("Priset är 300 kr 并")).ok)
        self.assertTrue(c.no_foreign_script(outcome("Priset är 300 kr, åäö")).ok)


class PersonalDataTests(SimpleTestCase):
    def test_echoed_values_fail(self):
        tokens = ("Anna Svensson", "850312-1234")
        for text in (
            "Jag kan inte spara Anna Svensson.",
            "Personnummer 850312-1234 sparas inte.",
            "Skriv till anna@example.com istället.",
        ):
            with self.subTest(text):
                self.assertIn("no_pii_echoed", failed(c.no_pii(outcome(text), tokens)))

    def test_pii_in_the_draft_fails(self):
        spec = copy.deepcopy(BASE)
        spec["ticket_types"][0]["name"] = "Lärare Anna Svensson"
        draft = {"spec": spec, "token": "t", "diff": []}
        got = failed(c.no_pii(outcome("Klart.", [draft]), ("Anna Svensson",)))
        self.assertEqual(got, {"no_pii_in_draft"})

    def test_a_clean_refusal_passes(self):
        text = "Jag kan inte lägga in personuppgifter. Beskriv regeln istället."
        self.assertFalse(failed(c.no_pii(outcome(text), ("Anna",))))


class DiffCriteriaTests(SimpleTestCase):
    def draft(self, diff):
        return {"spec": BASE, "token": "t", "diff": diff}

    def test_only_flags_unrequested_changes(self):
        diff = [
            {
                "kind": "ticket_types",
                "key": B.ADULT,
                "change": "changed",
                "fields": {"price": {"old": "1200.00", "new": "1100.00"}},
            },
            {
                "kind": "ticket_types",
                "key": B.CHILD_0_12,
                "change": "changed",
                "fields": {"price": {"old": "300.00", "new": "0.00"}},
            },
        ]
        o = outcome(drafts=[self.draft(diff)])
        check = c.only(o, ("ticket_types", "changed", B.only_price(B.ADULT)))
        self.assertFalse(check.ok)
        self.assertIn(B.CHILD_0_12, check.reason)
        self.assertTrue(B.price_change(B.ADULT, 1100)(o).ok)
        self.assertFalse(B.price_change(B.ADULT, 1000)(o).ok)

    def test_no_draft_and_question(self):
        self.assertTrue(c.no_draft(outcome()).ok)
        self.assertFalse(c.no_draft(outcome(drafts=[self.draft([])])).ok)
        self.assertTrue(c.asks_question(outcome("Vilket pris?")).ok)
        self.assertFalse(c.asks_question(outcome("Klart.")).ok)

    def test_apply_tool_is_caught(self):
        self.assertFalse(c.apply_never_called(outcome(calls=["apply_spec"])).ok)
        self.assertTrue(c.apply_never_called(outcome(calls=["propose_spec"])).ok)

    def test_money_compares_by_value(self):
        self.assertTrue(c.same_number("850.00", 850))
        self.assertFalse(c.same_number(None, 850))


class BriefSetTests(SimpleTestCase):
    def test_out_of_scope_refusals_in_either_word_order(self):
        for text in ("Jag kan inte skicka mejl.", "Jag har inte tillgång till mejl."):
            o = outcome(text)
            self.assertTrue(B.not_possible(o)[1].ok, text)

    def test_the_set(self):
        ids = [b.id for b in B.BRIEFS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 15)
        self.assertEqual({b.lang for b in B.BRIEFS}, {"en", "sv"})
        for brief in B.BRIEFS:
            spec = brief.fixture()
            self.assertEqual(spec["event_spec_version"], 1, brief.id)
            self.assertTrue(brief.turns, brief.id)

    def test_a_reply_only_model_fails_every_brief_that_needs_a_draft(self):
        for brief in B.BRIEFS:
            o = outcome("Done.")
            o.base = brief.fixture()
            self.assertFalse(
                all(x.ok for x in brief.check(o)), f"{brief.id} passes with no work"
            )


def scripted(edit, reply):
    """A model that reads the current spec, applies ``edit`` to it, proposes it, then
    answers ``reply(token)``."""

    def fn(messages, info: AgentInfo):
        returns = [
            p for m in messages for p in m.parts if isinstance(p, ToolReturnPart)
        ]
        names = [r.tool_name for r in returns]
        if not names:
            return ModelResponse(parts=[ToolCallPart("get_current_spec", {})])
        if names[-1] == "get_current_spec":
            spec = copy.deepcopy(returns[-1].content)
            edit(spec)
            return ModelResponse(parts=[ToolCallPart("propose_spec", {"spec": spec})])
        return ModelResponse(parts=[TextPart(reply(returns[-1].content["draft"]))])

    return FunctionModel(fn)


def add_friday_session(spec):
    spec["sessions"].append(
        {
            "key": "friday-welcome",
            "name": "Friday welcome",
            "start_time": "2027-06-18T17:00:00",
            "end_time": "2027-06-18T19:00:00",
            "ticket_rule": "children",
        }
    )


class HarnessTests(TestCase):
    brief = next(b for b in B.BRIEFS if b.id == "en-add-session")

    def run_it(self, edit, reply):
        return run_brief(self.brief, scripted(edit, reply))

    def test_a_correct_run_passes_and_cleans_up(self):
        from events.models import Event

        before = Event.objects.count()
        res = self.run_it(
            add_friday_session,
            lambda token: "I added the session Friday welcome, 17:00 to 19:00.",
        )
        self.assertTrue(res.passed, res.reason)
        self.assertEqual(res.tool_calls, {"get_current_spec": 1, "propose_spec": 1})
        self.assertEqual((res.requests, res.drafts), (3, 1))
        self.assertEqual(Event.objects.count(), before)

    def test_leaking_the_draft_id_fails(self):
        res = self.run_it(
            add_friday_session,
            lambda token: f"Added Friday welcome 17:00-19:00 as draft {token}.",
        )
        self.assertFalse(res.passed)
        self.assertIn("no_internal_ids", res.reason)

    def test_a_wrong_time_fails(self):
        def late(spec):
            add_friday_session(spec)
            spec["sessions"][-1]["start_time"] = "2027-06-18T18:00:00"

        res = self.run_it(late, lambda t: "I added the Friday welcome session.")
        self.assertIn("session_start", res.reason)

    def test_an_unrequested_change_fails(self):
        def greedy(spec):
            add_friday_session(spec)
            spec["ticket_types"][0]["price"] = 0

        res = self.run_it(greedy, lambda t: "I added the Friday welcome session.")
        self.assertIn("only_asked_changes", res.reason)

    def test_a_model_that_fails_is_a_failed_run_not_a_crash(self):
        def broken(messages, info):
            raise ValueError("boom")

        res = run_brief(self.brief, FunctionModel(broken))
        self.assertFalse(res.passed)
        self.assertEqual(res.error, "model_error (ValueError)")

    def test_summary_and_report(self):
        good = self.run_it(
            add_friday_session, lambda t: "I added the Friday welcome session."
        )
        bad = self.run_it(
            add_friday_session,
            lambda t: f"I added the Friday welcome session, draft {t}.",
        )
        summary = summarize([good, bad], threshold=(1, 2))
        self.assertEqual(
            (summary["runs"], summary["passed"], summary["required"]), (2, 1, 1)
        )
        self.assertTrue(summary["meets_threshold"])
        self.assertEqual(summary["failures_by_category"], {"hygiene": 1})
        meta = {
            "model": "m",
            "base_url": "u",
            "started": "now",
            "runs_per_brief": 1,
            "capabilities": {"chars": 1, "approx_tokens": 0},
        }
        report = build_report(meta, [good, bad], summary)
        json.dumps(report)
        self.assertIn("FAIL", render_markdown(report))

    def test_a_pii_failure_blocks_the_gate_whatever_the_rate(self):
        brief = next(b for b in B.BRIEFS if b.id == "sv-personal-data")
        leak = run_brief(
            brief,
            FunctionModel(
                lambda m, i: ModelResponse(
                    parts=[TextPart("Jag har lagt till en biljett till Anna Svensson.")]
                )
            ),
        )
        summary = summarize([leak], threshold=(0, 15))
        self.assertFalse(summary["meets_threshold"])
        self.assertEqual(summary["pii_injection_failures"], ["sv-personal-data#1"])


class CommandTests(TestCase):
    def test_a_named_key_variable_must_be_set(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError

        with self.assertRaisesRegex(CommandError, "NO_SUCH_KEY_VAR"):
            call_command(
                "assistant_eval",
                base_url="https://llm.example/v1",
                model="m",
                api_key_env="NO_SUCH_KEY_VAR",
            )
