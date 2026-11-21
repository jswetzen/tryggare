import copy
import json
from datetime import UTC, datetime

from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from asgiref.sync import async_to_sync
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import FunctionModel

from accounts.models import AdminUser
from events import event_spec
from events.models import Event
from events.services import REPLACE_PERMISSIONS, VIEW_PERMISSIONS
from events.spec_test_support import add_ticket, at_now

from .agent import build_agent, run_assistant
from .models import LLMProvider
from .tools import (
    TOOL_NAMES,
    EventTools,
    ToolFailure,
    build_toolset,
    find_personal_data,
    strings_in,
)

SPEC_KEYS = {
    "event_spec_version",
    "event",
    "sessions",
    "ticket_types",
    "extras",
    "promo_codes",
}


def call(tools, name, **args):
    with at_now():
        return getattr(tools, name)(**args)


def user_with(name, labels):
    user = AdminUser.objects.create_user(name, "pw12345")
    for label in labels:
        app, codename = label.split(".")
        user.user_permissions.add(
            Permission.objects.get(content_type__app_label=app, codename=codename)
        )
    return user


class ToolsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff = AdminUser.objects.create_superuser("toolstaff", "pw12345")
        with at_now():
            cls.event = event_spec.apply(event_spec.example_spec())[0]
        cls.other = Event.objects.create(
            name="Other", start_date="2027-01-01", end_date="2027-01-02"
        )

    def tools(self):
        return EventTools(self.event, self.staff)

    def changed_spec(self):
        spec = copy.deepcopy(event_spec.export(self.event))
        spec["ticket_types"][0]["price"] = 999
        return spec


class PermissionTests(ToolsTestCase):
    def test_non_staff_refused(self):
        plain = AdminUser.objects.create_user("plain", "pw12345")
        with self.assertRaises(PermissionDenied):
            EventTools(self.event, plain)

    def test_view_only_refused(self):
        viewer = user_with("viewer", VIEW_PERMISSIONS)
        with self.assertRaises(PermissionDenied):
            EventTools(self.event, viewer)

    def test_replace_permissions_suffice(self):
        editor = user_with("editor", set(VIEW_PERMISSIONS + REPLACE_PERMISSIONS))
        toolset, _ = build_toolset(self.event, editor)
        self.assertEqual(set(toolset.tools), set(TOOL_NAMES))

    def test_scoped_to_bound_event(self):
        tools = EventTools(self.other, self.staff)
        self.assertEqual(call(tools, "get_current_spec")["event"]["name"], "Other")
        self.assertEqual(
            call(self.tools(), "get_current_spec"), event_spec.export(self.event)
        )

    def test_export_refuses_other_events_rows(self):
        from events.models import TicketType
        from events.spec_test_support import foreign_session

        target = Event.objects.create(
            name="T", start_date="2027-05-01", end_date="2027-05-02"
        )
        ticket_type = TicketType.objects.create(
            event=target, name="T", price=0, kind="session_bundle"
        )
        ticket_type.sessions.add(foreign_session())
        # An export that would leak another event's rows is a tool error, not a 500.
        with self.assertRaises(ToolFailure):
            call(EventTools(target, self.staff), "get_current_spec")

    def test_no_apply_tool(self):
        self.assertEqual(
            set(build_toolset(self.event, self.staff)[0].tools), set(TOOL_NAMES)
        )
        self.assertFalse(any("apply" in n for n in TOOL_NAMES))


class ApplyGuardTests(ToolsTestCase):
    def test_event_in_use_refused(self):
        add_ticket(self.event)
        with self.assertRaises(PermissionDenied) as caught:
            self.tools()
        self.assertIn("event_not_empty", str(caught.exception))

    def test_open_registration_refused(self):
        with at_now(datetime(2027, 4, 1, tzinfo=UTC)):
            with self.assertRaises(PermissionDenied) as caught:
                EventTools(self.event, self.staff)
        self.assertIn("registration_open_on_target", str(caught.exception))


class ReadToolTests(ToolsTestCase):
    def test_capabilities(self):
        result = call(self.tools(), "get_capabilities")
        self.assertIn("unsupported", result["capabilities"])
        self.assertIn("properties", result["schema"])

    def test_sibling_discount_has_closest_workaround(self):
        entry = next(
            e
            for e in call(self.tools(), "get_capabilities")["capabilities"][
                "unsupported"
            ]
            if e["id"] == "sibling_discount"
        )
        self.assertIn("promo code", entry["closest"])

    def test_current_spec_has_no_personal_data_sections(self):
        spec = call(self.tools(), "get_current_spec")
        self.assertEqual(set(spec), SPEC_KEYS)


class ValidateDiffTests(ToolsTestCase):
    def test_validate_ok(self):
        result = call(self.tools(), "validate_spec", spec=self.changed_spec())
        self.assertTrue(result["valid"])

    def test_validate_surfaces_shape_errors(self):
        result = call(self.tools(), "validate_spec", spec={"bogus": 1})
        self.assertFalse(result["valid"])
        self.assertTrue(
            all({"path", "code", "message"} <= set(e) for e in result["errors"])
        )

    def test_unknown_field_error_lists_allowed_names(self):
        spec = self.changed_spec()
        spec["ticket_types"][0]["colour"] = "red"
        errors = call(self.tools(), "validate_spec", spec=spec)["errors"]
        message = next(e for e in errors if e["path"] == "ticket_types[0].colour")[
            "message"
        ]
        self.assertIn("Allowed here:", message)
        self.assertIn("price", message)
        self.assertNotIn("event_spec_version", message)

    def test_diff_shows_change(self):
        result = call(self.tools(), "diff_spec", spec=self.changed_spec())
        self.assertTrue(result["valid"])
        fields = [c for c in result["diff"] if c["change"] == "changed"]
        self.assertEqual(len(fields), 1)
        self.assertEqual(fields[0]["fields"]["price"]["new"], "999.00")

    def test_diff_of_invalid_spec_reports_errors(self):
        result = call(self.tools(), "diff_spec", spec={"bogus": 1})
        self.assertFalse(result["valid"])
        self.assertEqual(result["diff"], [])

    def test_stringified_spec_accepted(self):
        as_text = json.dumps(self.changed_spec())
        for tool in ("validate_spec", "diff_spec", "propose_spec"):
            with self.subTest(tool=tool):
                result = call(self.tools(), tool, spec=as_text)
                self.assertNotEqual(result.get("valid"), False)

    def test_bad_json_string_is_tool_failure(self):
        for bad in ("{nope", "[1, 2]"):
            with self.subTest(bad=bad), self.assertRaises(ToolFailure):
                call(self.tools(), "validate_spec", spec=bad)

    def test_spec_parameter_schema_describes_top_level_keys(self):
        toolset, _ = build_toolset(self.event, self.staff)
        schema = toolset.tools["propose_spec"].function_schema.json_schema
        self.assertIn("promo_codes", schema["properties"]["spec"]["description"])

    def test_discount_as_extra_warns(self):
        spec = self.changed_spec()
        spec["extras"].append(
            {"key": "syskonrabatt", "name": "Syskonrabatt", "price": 0}
        )
        warnings = call(self.tools(), "validate_spec", spec=spec)["warnings"]
        self.assertIn("discount_as_extra", [w["code"] for w in warnings])

    def test_priced_or_choice_extras_do_not_trigger_discount_warning(self):
        spec = self.changed_spec()
        spec["extras"].append({"key": "rabatt-mugg", "name": "Rabatt mug", "price": 20})
        warnings = call(self.tools(), "validate_spec", spec=spec)["warnings"]
        self.assertNotIn("discount_as_extra", [w["code"] for w in warnings])


class ProposeTests(ToolsTestCase):
    def test_propose_stores_draft_without_applying(self):
        tools = self.tools()
        before = event_spec.export(self.event)
        result = call(tools, "propose_spec", spec=self.changed_spec())
        self.assertFalse(result["applied"])
        self.assertIn(result["draft"], tools.drafts.items)
        self.assertTrue(result["diff"])
        self.assertEqual(event_spec.export(self.event), before)

    def test_same_spec_same_token(self):
        tools = self.tools()
        spec = self.changed_spec()
        self.assertEqual(
            call(tools, "propose_spec", spec=spec)["draft"],
            call(tools, "propose_spec", spec=spec)["draft"],
        )

    def test_invalid_spec_is_failure_and_not_stored(self):
        tools = self.tools()
        with self.assertRaises(ToolFailure) as caught:
            call(tools, "propose_spec", spec={"bogus": 1})
        self.assertIn("invalid", str(caught.exception))
        self.assertEqual(tools.drafts.items, {})

    def test_semantic_error_is_failure(self):
        spec = self.changed_spec()
        spec["ticket_types"][0]["requires_ticket_type"] = "no-such-key"
        with self.assertRaises(ToolFailure) as caught:
            call(self.tools(), "propose_spec", spec=spec)
        self.assertIn("unknown_key", str(caught.exception))

    def test_event_used_after_server_built_fails_diff_and_propose(self):
        tools = self.tools()
        add_ticket(self.event)
        self.assertFalse(call(tools, "diff_spec", spec=self.changed_spec())["valid"])
        with self.assertRaises(ToolFailure) as caught:
            call(tools, "propose_spec", spec=self.changed_spec())
        self.assertIn("event_not_empty", str(caught.exception))
        self.assertEqual(tools.drafts.items, {})


class DraftStalenessTests(ToolsTestCase):
    def test_draft_fresh_then_stale_after_event_changes(self):
        tools = self.tools()
        token = call(tools, "propose_spec", spec=self.changed_spec())["draft"]
        self.assertFalse(tools.drafts.is_stale(token))
        Event.objects.filter(pk=self.event.pk).update(name="Renamed meanwhile")
        self.assertTrue(tools.drafts.is_stale(token))

    def test_token_depends_on_event_state_and_spec(self):
        tools = self.tools()
        first = call(tools, "propose_spec", spec=self.changed_spec())["draft"]
        other_spec = self.changed_spec()
        other_spec["ticket_types"][0]["price"] = 5
        second = call(tools, "propose_spec", spec=other_spec)["draft"]
        Event.objects.filter(pk=self.event.pk).update(name="Renamed meanwhile")
        third = call(tools, "propose_spec", spec=self.changed_spec())["draft"]
        self.assertEqual(len({first, second, third}), 3)
        self.assertEqual(
            tools.drafts.items[first]["base"], tools.drafts.items[second]["base"]
        )
        self.assertNotEqual(
            tools.drafts.items[first]["base"], tools.drafts.items[third]["base"]
        )


class PersonalDataTests(ToolsTestCase):
    def spec_with(self, text):
        spec = self.changed_spec()
        spec["ticket_types"][0]["name"] = text
        return spec

    def test_patterns_rejected_by_every_spec_tool(self):
        for text in (
            "Contact anna@example.com",
            "Ring 070-123 45 67",
            "Barn 20150312-1234",
            "150312+1234",
            "+46 70 123 45 67",
            "anna @ example.com",
            "anna​@example.com",
            "anna＠example.com",
            "０７０-123 45 67",
        ):
            for tool in ("validate_spec", "diff_spec", "propose_spec"):
                with self.subTest(text=text, tool=tool):
                    tools = self.tools()
                    with self.assertRaises(ToolFailure) as caught:
                        call(tools, tool, spec=self.spec_with(text))
                    self.assertIn("personal data", str(caught.exception))
                    self.assertIn("ticket_types[0].name", str(caught.exception))
                    self.assertEqual(tools.drafts.items, {})

    def test_key_field_personnummer_rejected(self):
        spec = self.changed_spec()
        spec["ticket_types"][0]["key"] = "20150312-1234"
        with self.assertRaises(ToolFailure) as caught:
            call(self.tools(), "validate_spec", spec=spec)
        self.assertIn("ticket_types[0].key", str(caught.exception))

    def test_ordinary_keys_and_text_pass(self):
        self.assertEqual(find_personal_data(event_spec.example_spec()), [])
        self.assertEqual(
            find_personal_data(
                {"key": "child-0-12", "name": "Ages 6-12, 2027-2028, max 150 seats"}
            ),
            [],
        )
        self.assertEqual(find_personal_data({"name": "2027-05-01 - 2027-05-03"}), [])

    def test_urls_are_not_matched(self):
        url = "https://res.cloudinary.com/demo/image/upload/v1700000000123/a_1234567890.jpg"
        self.assertEqual(find_personal_data({"header_image_url": url}), [])
        self.assertEqual(
            find_personal_data(
                {
                    "header_image_url": "https://images.unsplash.com/photo-1523050854058-8df90110c9f1?w=1600&q=80"
                }
            ),
            [],
        )

    def test_guard_passes_over_export_of_realistic_event(self):
        spec = self.changed_spec()
        spec["event"]["header_image_url"] = (
            "https://res.cloudinary.com/demo/image/upload/v1700000000123/a_1234567890.jpg"
        )
        spec["event"]["name"] = "Org 802409-3138 conference"
        Event.objects.filter(pk=self.event.pk).update(
            header_image_url=spec["event"]["header_image_url"],
            name=spec["event"]["name"],
        )
        exported = event_spec.export(Event.objects.get(pk=self.event.pk))
        known = strings_in(json.loads(json.dumps(exported, default=str)))
        self.assertEqual(find_personal_data(exported, known), [])
        # Unchanged text passes through the tools even though it looks like a number.
        result = call(self.tools(), "validate_spec", spec=exported)
        self.assertTrue(result["valid"])

    def test_text_the_model_introduces_is_still_checked(self):
        Event.objects.filter(pk=self.event.pk).update(name="Org 802409-3138")
        spec = event_spec.export(Event.objects.get(pk=self.event.pk))
        spec["event"]["name"] = "Org 802409-3139 call 070-123 45 67"
        with self.assertRaises(ToolFailure):
            call(self.tools(), "validate_spec", spec=spec)


class AgentOverRealToolsTests(ToolsTestCase):
    def run_model(self, model_fn, **kwargs):
        toolset, drafts = build_toolset(self.event, self.staff)
        provider = LLMProvider(base_url="http://x.example/v1", model="m")
        agent = build_agent(provider, toolset, model=FunctionModel(model_fn))

        async def go():
            return await run_assistant(agent, "raise the price", **kwargs)

        with at_now():
            return async_to_sync(go)(), drafts

    def test_invalid_then_valid_propose(self):
        bad = {"bogus": 1}
        good = self.changed_spec()
        seen = []

        def model_fn(messages, info):
            seen.append(messages)
            n = sum(isinstance(p, ToolCallPart) for m in messages for p in m.parts)
            if n == 0:
                return ModelResponse(
                    parts=[ToolCallPart("propose_spec", {"spec": bad})]
                )
            if n == 1:
                # Stringified: some models send the object as text.
                return ModelResponse(
                    parts=[
                        ToolCallPart(
                            "propose_spec", {"spec": json.dumps(good, default=str)}
                        )
                    ]
                )
            return ModelResponse(parts=[TextPart("proposed")])

        result, drafts = self.run_model(model_fn)
        self.assertEqual(result.output, "proposed")
        # The retry prompt carried the tool's error text back to the model.
        self.assertIn("invalid and was not stored", str(seen[1]))
        self.assertEqual(len(drafts.items), 1)

    def test_endless_invalid_proposals_stop_after_retries(self):
        from pydantic_ai.exceptions import UnexpectedModelBehavior

        def model_fn(messages, info):
            return ModelResponse(
                parts=[ToolCallPart("propose_spec", {"spec": {"bogus": 1}})]
            )

        with self.assertRaises(UnexpectedModelBehavior):
            self.run_model(model_fn)


class AssistantGuidanceTests(ToolsTestCase):
    def test_inverted_age_bounds_surface_as_a_fixable_error(self):
        spec = self.changed_spec()
        spec["ticket_types"][0]["min_birthdate"] = "2014-06-18"
        spec["ticket_types"][0]["max_birthdate"] = "2009-06-19"
        result = call(self.tools(), "validate_spec", spec=spec)
        self.assertFalse(result["valid"])
        err = next(e for e in result["errors"] if e["code"] == "age_bounds_inverted")
        self.assertEqual(err["path"], "ticket_types[0]")
        self.assertIn("earliest birth date", err["message"])

    def test_capabilities_state_the_age_rule(self):
        notes = " ".join(
            call(self.tools(), "get_capabilities")["capabilities"]["notes"]
        )
        self.assertIn("plus one day", notes)

    def test_system_prompt_forbids_inventing_values(self):
        from assistant.agent import SYSTEM_PROMPT

        self.assertIn("Never invent", SYSTEM_PROMPT)
        self.assertIn("ask one short question", SYSTEM_PROMPT)
