"""Event spec: schema, example, export and the validation layers."""

import copy
from datetime import UTC, date, datetime
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase
from django.utils import translation

from events.event_spec import (
    EventSpec,
    capabilities,
    example_spec,
    export,
    json_schema,
    validate,
)
from events.event_spec._export import KeyAllocator, slugify_key
from events.models import (
    Event,
    EventTicket,
    Extra,
    PromoCode,
    Session,
    TicketType,
)
from families.models import Child, Family

# The example's registration window is in 2027; pin "now" before it opens.
NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)


def at_now(now=NOW):
    return patch("events.models.timezone.now", return_value=now)


def by_path(issues):
    return {i["path"]: i for i in issues}


def check(spec, event=None, now=NOW):
    with at_now(now):
        return validate(spec, event)


class SchemaTests(SimpleTestCase):
    def test_every_property_has_a_description(self):
        schema = json_schema()
        missing = []
        for name, definition in [("EventSpec", schema), *schema["$defs"].items()]:
            assert definition["additionalProperties"] is False, name
            for prop, body in definition["properties"].items():
                if "description" not in body:
                    missing.append(f"{name}.{prop}")
        self.assertEqual(missing, [])

    def test_schema_version_and_sections(self):
        props = json_schema()["properties"]
        self.assertEqual(props["event_spec_version"]["const"], 1)
        self.assertEqual(
            set(props),
            {
                "event_spec_version",
                "event",
                "sessions",
                "ticket_types",
                "extras",
                "promo_codes",
            },
        )

    def test_capabilities_name_the_unsupported_things(self):
        unsupported = {c["id"] for c in capabilities()["unsupported"]}
        self.assertTrue(
            {
                "sibling_discount",
                "multiple_promo_codes",
                "free_text_extras",
                "waitlists",
                "family_groups",
                "line_items",
            }
            <= unsupported
        )
        self.assertTrue(capabilities()["supported"])


class ExampleTests(SimpleTestCase):
    def test_example_validates_cleanly(self):
        errors, warnings = check(example_spec())
        self.assertEqual((errors, warnings), ([], []))

    def test_example_is_the_walkthrough_brief(self):
        spec = EventSpec.model_validate(example_spec())
        prices = {t.key: int(t.price) for t in spec.ticket_types}
        self.assertEqual(prices["adult-conference-pass"], 1200)
        self.assertEqual(prices["child-pass-0-12"], 300)
        self.assertEqual(prices["child-pass-13-17"], 600)
        self.assertEqual(spec.ticket_types[0].capacity, 150)
        self.assertEqual(
            [c.label for c in spec.extras[0].choices], ["S", "M", "L", "XL"]
        )
        self.assertEqual(spec.promo_codes[0].code, "TESTFAMILY")


class ShapeTests(SimpleTestCase):
    def test_missing_required_field(self):
        spec = example_spec()
        del spec["event"]["name"]
        errors, _ = check(spec)
        self.assertEqual(by_path(errors)["event.name"]["code"], "missing")

    def test_unknown_key_is_rejected_with_its_path(self):
        spec = example_spec()
        spec["ticket_types"][2]["colour"] = "red"
        errors, _ = check(spec)
        self.assertEqual(
            by_path(errors)["ticket_types[2].colour"]["code"], "extra_forbidden"
        )

    def test_bad_enum_and_version(self):
        spec = example_spec()
        spec["ticket_types"][0]["applies_to"] = "everyone"
        spec["event_spec_version"] = 2
        errors, _ = check(spec)
        issues = by_path(errors)
        self.assertEqual(issues["ticket_types[0].applies_to"]["code"], "literal_error")
        self.assertIn("parent", issues["ticket_types[0].applies_to"]["message"])
        self.assertIn("event_spec_version", issues)

    def test_bad_key_format(self):
        spec = example_spec()
        spec["sessions"][0]["key"] = "Saturday Workshop"
        errors, _ = check(spec)
        self.assertEqual(
            by_path(errors)["sessions[0].key"]["code"], "string_pattern_mismatch"
        )

    def test_negative_price_and_not_a_dict(self):
        spec = example_spec()
        spec["ticket_types"][0]["price"] = -1
        errors, _ = check(spec)
        self.assertIn("ticket_types[0].price", by_path(errors))
        errors, _ = check([])
        self.assertEqual(len(errors), 1)

    def test_shape_errors_stop_later_layers(self):
        spec = example_spec()
        del spec["event"]["name"]
        spec["ticket_types"][0]["requires_ticket_type"] = "nope"
        errors, warnings = check(spec)
        self.assertNotIn("ticket_types[0].requires_ticket_type", by_path(errors))
        self.assertEqual(warnings, [])


class ReferenceTests(SimpleTestCase):
    def test_duplicate_keys(self):
        spec = example_spec()
        spec["ticket_types"][1]["key"] = "adult-conference-pass"
        spec["extras"][0]["choices"][1]["key"] = "s"
        errors, _ = check(spec)
        issues = by_path(errors)
        self.assertEqual(issues["ticket_types[0].key"]["code"], "duplicate_key")
        self.assertEqual(issues["ticket_types[1].key"]["code"], "duplicate_key")
        self.assertEqual(issues["extras[0].choices[1].key"]["code"], "duplicate_key")

    def test_same_key_in_different_kinds_is_fine(self):
        errors, _ = check(example_spec())  # session and ticket type share a key
        self.assertEqual(errors, [])

    def test_unknown_references(self):
        spec = example_spec()
        spec["ticket_types"][3]["sessions"] = ["nope"]
        spec["ticket_types"][1]["requires_ticket_type"] = "nope"
        spec["extras"][0]["session"] = "nope"
        spec["promo_codes"][0]["unlocks_ticket_types"] = ["nope"]
        errors, _ = check(spec)
        issues = by_path(errors)
        for path in (
            "ticket_types[3].sessions[0]",
            "ticket_types[1].requires_ticket_type",
            "extras[0].session",
            "promo_codes[0].unlocks_ticket_types[0]",
        ):
            self.assertEqual(issues[path]["code"], "unknown_key", path)

    def test_reference_to_the_wrong_kind(self):
        spec = example_spec()
        spec["promo_codes"][0]["applies_to_ticket_types"] = ["t-shirt"]
        errors, _ = check(spec)
        self.assertEqual(
            by_path(errors)["promo_codes[0].applies_to_ticket_types[0]"]["code"],
            "wrong_kind_key",
        )

    def test_duplicate_reference(self):
        spec = example_spec()
        spec["ticket_types"][3]["sessions"] = ["saturday-workshop", "saturday-workshop"]
        errors, _ = check(spec)
        self.assertEqual(
            by_path(errors)["ticket_types[3].sessions[1]"]["code"],
            "duplicate_reference",
        )

    def test_noun_in_message_is_translated(self):
        spec = example_spec()
        spec["promo_codes"][0]["applies_to_ticket_types"] = ["nope"]
        with translation.override("sv"):
            errors, _ = check(spec)
        message = by_path(errors)["promo_codes[0].applies_to_ticket_types[0]"][
            "message"
        ]
        self.assertIn("biljettyp", message)
        self.assertNotIn("ticket type", message)


class ModelRuleTests(SimpleTestCase):
    def test_equal_session_times_are_allowed(self):
        spec = example_spec()
        spec["sessions"][0]["end_time"] = spec["sessions"][0]["start_time"]
        errors, _ = check(spec)
        self.assertEqual(errors, [])

    def test_rules_live_on_the_models(self):
        with self.assertRaises(ValidationError) as ctx:
            Event(
                name="x", start_date=date(2027, 2, 2), end_date=date(2027, 2, 1)
            ).clean()
        self.assertIn("end_date", ctx.exception.message_dict)
        with self.assertRaises(ValidationError) as ctx:
            PromoCode(discount_type="percent", discount_value=101).clean()
        self.assertIn("discount_value", ctx.exception.message_dict)

    def test_age_window_reuses_the_model_rule(self):
        spec = example_spec()
        spec["ticket_types"][2]["min_birthdate"] = "2009-07-01"
        spec["ticket_types"][2]["max_birthdate"] = "2014-01-01"
        errors, _ = check(spec)
        issues = by_path(errors)
        self.assertEqual(issues["ticket_types[2].min_birthdate"]["code"], "age_window")
        self.assertIn("2009-06-19", issues["ticket_types[2].min_birthdate"]["message"])
        self.assertEqual(issues["ticket_types[2].max_birthdate"]["code"], "age_window")

    def test_ticket_type_requiring_itself(self):
        spec = example_spec()
        spec["ticket_types"][1]["requires_ticket_type"] = "child-pass-0-12"
        errors, _ = check(spec)
        self.assertEqual(
            by_path(errors)["ticket_types[1].requires_ticket_type"]["code"],
            "invalid_requires",
        )

    def test_registration_window_order(self):
        spec = example_spec()
        spec["event"]["registration_closes_at"] = "2027-02-01T09:00:00"
        errors, _ = check(spec)
        self.assertEqual(
            by_path(errors)["event.registration_closes_at"]["code"], "window_order"
        )

    def test_field_validators_map_to_paths(self):
        spec = example_spec()
        spec["event"]["accent_color"] = "blue"
        spec["event"]["header_image_url"] = "not a url"
        errors, _ = check(spec)
        paths = by_path(errors)
        self.assertIn("event.accent_color", paths)
        self.assertIn("event.header_image_url", paths)

    def test_nested_choice_path(self):
        spec = example_spec()
        spec["extras"][0]["choices"][2]["label"] = ""
        errors, _ = check(spec)
        self.assertIn("extras[0].choices[2].label", by_path(errors))

    def test_duplicate_promo_code_ignores_case(self):
        spec = example_spec()
        other = copy.deepcopy(spec["promo_codes"][0])
        other.update(key="second", code="testfamily")
        spec["promo_codes"].append(other)
        errors, _ = check(spec)
        issues = by_path(errors)
        self.assertEqual(issues["promo_codes[0].code"]["code"], "duplicate_code")
        self.assertEqual(issues["promo_codes[1].code"]["code"], "duplicate_code")

    def test_order_rules(self):
        spec = example_spec()
        spec["event"]["end_date"] = "2027-06-01"
        spec["sessions"][0]["end_time"] = "2027-06-19T09:00:00"
        spec["promo_codes"][0]["discount_value"] = 110
        errors, _ = check(spec)
        issues = by_path(errors)
        self.assertEqual(issues["event.end_date"]["code"], "end_before_start")
        self.assertEqual(issues["sessions[0].end_time"]["code"], "end_before_start")
        self.assertEqual(
            issues["promo_codes[0].discount_value"]["code"], "percent_over_100"
        )

    def test_existing_event_is_accepted_as_target(self):
        event = Event(
            name="x", start_date=date(2027, 6, 18), end_date=date(2027, 6, 20)
        )
        errors, _ = check(example_spec(), event)
        self.assertEqual(errors, [])


class TargetEventTests(TestCase):
    def test_non_empty_target_is_an_error(self):
        event = Event.objects.create(
            name="Used", start_date=date(2027, 6, 18), end_date=date(2027, 6, 20)
        )
        errors, _ = check(example_spec(), event)
        self.assertEqual(errors, [])
        child = Child.objects.create(
            family=Family.objects.create(),
            first_name="Test",
            last_name="Child",
            birthdate=date(2020, 1, 1),
        )
        EventTicket.objects.create(attendee=child, event=event)
        errors, _ = check(example_spec(), event)
        self.assertEqual(by_path(errors)["event"]["code"], "event_not_empty")


class GoingLiveTests(SimpleTestCase):
    def test_open_window_is_an_error(self):
        errors, _ = check(example_spec(), now=datetime(2027, 4, 1, tzinfo=UTC))
        self.assertEqual(
            by_path(errors)["event.registration_opens_at"]["code"], "registration_open"
        )

    def test_open_ended_window_that_has_started_is_an_error(self):
        spec = example_spec()
        spec["event"]["registration_opens_at"] = "2026-01-01T09:00:00"
        spec["event"]["registration_closes_at"] = None
        errors, _ = check(spec)
        self.assertEqual(
            by_path(errors)["event.registration_opens_at"]["code"], "registration_open"
        )

    def test_no_window_is_allowed_with_a_warning(self):
        spec = example_spec()
        spec["event"]["registration_opens_at"] = None
        spec["event"]["registration_closes_at"] = None
        errors, warnings = check(spec)
        self.assertEqual(errors, [])
        self.assertEqual(
            by_path(warnings)["event.registration_opens_at"]["code"],
            "registration_not_configured",
        )

    def test_closed_window_warns(self):
        _, warnings = check(example_spec(), now=datetime(2027, 7, 1, tzinfo=UTC))
        self.assertEqual(
            by_path(warnings)["event.registration_closes_at"]["code"],
            "registration_closed",
        )


class WarningTests(SimpleTestCase):
    def test_requires_loop_is_only_a_warning(self):
        spec = example_spec()
        spec["ticket_types"][1]["requires_ticket_type"] = "child-pass-13-17"
        spec["ticket_types"][2]["requires_ticket_type"] = "child-pass-0-12"
        errors, warnings = check(spec)
        self.assertEqual(errors, [])
        w = by_path(warnings)
        self.assertEqual(
            w["ticket_types[1].requires_ticket_type"]["code"], "requires_cycle"
        )
        self.assertEqual(
            w["ticket_types[2].requires_ticket_type"]["code"], "requires_cycle"
        )

    def test_requires_inactive_ticket_type(self):
        spec = example_spec()
        spec["ticket_types"][1]["requires_ticket_type"] = "adult-conference-pass"
        spec["ticket_types"][0]["is_active"] = False
        self.assertIn(
            ("ticket_types[1].requires_ticket_type", "requires_inactive_ticket_type"),
            self.codes(spec),
        )

    def test_session_date_is_judged_in_stockholm(self):
        spec = example_spec()
        # 23:30 UTC on the 17th is 01:30 on the 18th in Stockholm: inside the event.
        spec["sessions"][0]["start_time"] = "2027-06-17T23:30:00+00:00"
        spec["sessions"][0]["end_time"] = "2027-06-18T08:00:00+00:00"
        self.assertNotIn(
            ("sessions[0].start_time", "session_outside_event"), self.codes(spec)
        )

    def codes(self, spec):
        errors, warnings = check(spec)
        self.assertEqual(errors, [])
        return {(w["path"], w["code"]) for w in warnings}

    def test_free_age_tier(self):
        spec = example_spec()
        spec["ticket_types"][1]["price"] = 0
        self.assertIn(("ticket_types[1].price", "age_tier_no_price"), self.codes(spec))

    def test_hidden_type_nobody_unlocks(self):
        spec = example_spec()
        spec["ticket_types"][0]["is_hidden"] = True
        self.assertIn(
            ("ticket_types[0].is_hidden", "hidden_not_unlocked"), self.codes(spec)
        )
        spec["promo_codes"][0]["unlocks_ticket_types"] = ["adult-conference-pass"]
        self.assertNotIn(
            ("ticket_types[0].is_hidden", "hidden_not_unlocked"), self.codes(spec)
        )
        spec["promo_codes"][0]["is_active"] = False
        self.assertIn(
            ("ticket_types[0].is_hidden", "hidden_not_unlocked"), self.codes(spec)
        )

    def test_promo_whose_ticket_types_are_all_inactive(self):
        spec = example_spec()
        spec["ticket_types"][0]["is_active"] = False
        self.assertIn(
            ("promo_codes[0]", "promo_ticket_types_inactive"), self.codes(spec)
        )

    def test_bundle_without_sessions_and_ignored_sessions(self):
        spec = example_spec()
        spec["ticket_types"][3]["sessions"] = []
        spec["ticket_types"][0]["sessions"] = ["saturday-workshop"]
        codes = self.codes(spec)
        self.assertIn(("ticket_types[3].sessions", "bundle_without_sessions"), codes)
        self.assertIn(("ticket_types[0].sessions", "sessions_ignored"), codes)

    def test_required_choice_without_active_choices(self):
        spec = example_spec()
        for c in spec["extras"][0]["choices"]:
            c["is_active"] = False
        self.assertIn(("extras[0].choices", "no_active_choices"), self.codes(spec))

    def test_choices_ignored_and_session_outside_event(self):
        spec = example_spec()
        spec["extras"][0]["requires_choice"] = False
        spec["sessions"][0]["start_time"] = "2027-07-19T10:00:00"
        spec["sessions"][0]["end_time"] = "2027-07-19T12:00:00"
        codes = self.codes(spec)
        self.assertIn(("extras[0].choices", "choices_ignored"), codes)
        self.assertIn(("sessions[0].start_time", "session_outside_event"), codes)


class KeyTests(SimpleTestCase):
    def test_example_keys_are_the_ones_export_derives(self):
        spec = example_spec()
        for kind, text in (
            ("sessions", "name"),
            ("ticket_types", "name"),
            ("extras", "name"),
            ("promo_codes", "code"),
        ):
            allocator = KeyAllocator()
            self.assertEqual(
                [r["key"] for r in spec[kind]],
                [allocator.allocate(r[text]) for r in spec[kind]],
                kind,
            )

    def test_key_not_derived_warns(self):
        spec = example_spec()
        spec["ticket_types"][0]["key"] = "adult-pass"
        spec["extras"][0]["choices"][0]["key"] = "small"
        errors, warnings = check(spec)
        w = by_path(warnings)
        self.assertEqual(w["ticket_types[0].key"]["code"], "key_not_derived")
        self.assertIn("adult-conference-pass", w["ticket_types[0].key"]["message"])
        self.assertIn("extras[0].choices[0].key", w)

    def test_clash_suffix_is_accepted(self):
        spec = example_spec()
        spec["ticket_types"][1]["name"] = "Adult conference pass"
        spec["ticket_types"][1]["key"] = "adult-conference-pass-2"
        spec["promo_codes"][0]["applies_to_ticket_types"] = ["adult-conference-pass"]
        _, warnings = check(spec)
        self.assertNotIn("ticket_types[1].key", by_path(warnings))

    def test_promo_code_is_normalised(self):
        spec = example_spec()
        spec["promo_codes"][0]["code"] = "  testfamily "
        self.assertEqual(
            EventSpec.model_validate(spec).promo_codes[0].code, "TESTFAMILY"
        )
        spec["promo_codes"][0]["code"] = "   "
        errors, _ = check(spec)
        self.assertIn("promo_codes[0].code", by_path(errors))


class MessageLanguageTests(SimpleTestCase):
    def test_messages_follow_the_active_language(self):
        spec = example_spec()
        spec["ticket_types"][2]["min_birthdate"] = "2009-07-01"
        spec["promo_codes"][0]["discount_value"] = 110
        with translation.override("en"):
            en = by_path(check(spec)[0])
        with translation.override("sv"):
            sv = by_path(check(spec)[0])
        path = "promo_codes[0].discount_value"
        self.assertEqual(
            en[path]["message"], "A percent discount cannot be more than 100."
        )
        self.assertNotEqual(sv[path]["message"], en[path]["message"])
        self.assertNotEqual(
            sv["ticket_types[2].min_birthdate"]["message"],
            en["ticket_types[2].min_birthdate"]["message"],
        )
        self.assertEqual(sv[path]["code"], en[path]["code"])


class SlugTests(SimpleTestCase):
    def test_slugify(self):
        self.assertEqual(slugify_key("Child pass 0-12"), "child-pass-0-12")
        self.assertEqual(slugify_key("Förälder & Barn!"), "foralder-barn")
        self.assertEqual(slugify_key("???"), "item")
        self.assertLessEqual(len(slugify_key("x" * 200)), 64)


class ExportTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.event = Event.objects.create(
            name="Export Camp",
            start_date=date(2027, 8, 6),
            end_date=date(2027, 8, 8),
            price=None,
            ticket_rule_default="children",
            accent_color="#2563EB",
            registration_opens_at=datetime(2027, 3, 1, 8, 0, tzinfo=UTC),
            registration_closes_at=datetime(2027, 7, 20, 21, 59, tzinfo=UTC),
        )
        cls.day = Session.objects.create(
            event=cls.event,
            name="Lördag",
            start_time=datetime(2027, 8, 7, 8, 0, tzinfo=UTC),
            end_time=datetime(2027, 8, 7, 14, 0, tzinfo=UTC),
            is_active=True,
        )
        cls.adult = TicketType.objects.create(
            event=cls.event, name="Adult", price=500, applies_to="parent", capacity=40
        )
        cls.adult2 = TicketType.objects.create(
            event=cls.event,
            name="Adult",
            price=400,
            applies_to="parent",
            requires_ticket_type=cls.adult,
            max_per_required=2,
            sort_order=5,
        )
        cls.bundle = TicketType.objects.create(
            event=cls.event,
            name="Saturday",
            price=100,
            kind="session_bundle",
            is_hidden=True,
            sort_order=9,
        )
        cls.bundle.sessions.set([cls.day])
        cls.extra = Extra.objects.create(
            event=cls.event,
            name="Lunch",
            price=50,
            session=cls.day,
            requires_choice=True,
            per_attendee=False,
        )
        cls.extra.choice_rows.create(label="Veg", price_delta=0, sort_order=1)
        cls.extra.choice_rows.create(
            label="Veg", price_delta=5, sort_order=2, is_active=False
        )
        promo = PromoCode.objects.create(
            event=cls.event,
            code="vip 2027",
            discount_type="percent",
            discount_value=15,
            max_uses=3,
            uses_count=2,
        )
        promo.unlocks_ticket_types.set([cls.bundle])
        promo.applies_to_ticket_types.set([cls.adult])

    def test_export_shape_and_keys(self):
        spec = export(self.event)
        self.assertEqual(spec["event_spec_version"], 1)
        self.assertEqual(spec["event"]["name"], "Export Camp")
        self.assertEqual(spec["event"]["ticket_rule_default"], "children")
        self.assertEqual(
            spec["event"]["registration_opens_at"], "2027-03-01T09:00:00+01:00"
        )
        self.assertEqual([s["key"] for s in spec["sessions"]], ["lordag"])
        self.assertEqual(
            [t["key"] for t in spec["ticket_types"]], ["adult", "adult-2", "saturday"]
        )
        self.assertEqual(spec["ticket_types"][0]["price"], "500.00")
        self.assertEqual(spec["ticket_types"][1]["price"], "400.00")
        self.assertEqual(
            [c["key"] for c in spec["extras"][0]["choices"]], ["veg", "veg-2"]
        )
        self.assertEqual(spec["promo_codes"][0]["key"], "vip-2027")
        self.assertEqual(spec["promo_codes"][0]["code"], "VIP 2027")

    def test_export_resolves_references_to_keys(self):
        spec = export(self.event)
        first, second, bundle = spec["ticket_types"]
        self.assertIsNone(first["requires_ticket_type"])
        self.assertEqual(second["requires_ticket_type"], "adult")
        self.assertEqual(bundle["sessions"], ["lordag"])
        self.assertEqual(spec["extras"][0]["session"], "lordag")
        promo = spec["promo_codes"][0]
        self.assertEqual(promo["applies_to_ticket_types"], ["adult"])
        self.assertEqual(promo["unlocks_ticket_types"], ["saturday"])

    def test_export_leaves_out_derived_and_live_state(self):
        spec = export(self.event)
        flat = repr(spec)
        for leaked in (
            "uses_count",
            "created_at",
            "is_active': True, 'ticket_rule'",
            str(self.event.id),
        ):
            self.assertNotIn(leaked, flat)
        self.assertNotIn("is_active", spec["sessions"][0])
        self.assertNotIn("id", spec["event"])

    def test_exported_spec_is_valid(self):
        spec = export(self.event)
        parsed = EventSpec.model_validate(spec)
        self.assertEqual(parsed.model_dump(mode="json"), spec)
        errors, warnings = check(spec)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_export_is_stable(self):
        self.assertEqual(export(self.event), export(self.event))

    def test_ties_break_on_id(self):
        event = Event.objects.create(
            name="Ties", start_date=date(2027, 1, 1), end_date=date(2027, 1, 1)
        )
        a = TicketType.objects.create(event=event, name="Same", price=1)
        b = TicketType.objects.create(event=event, name="Same", price=2)
        first, second = sorted([a, b], key=lambda t: t.id)
        spec = export(event)
        self.assertEqual(
            [(t["key"], t["price"]) for t in spec["ticket_types"]],
            [("same", f"{first.price:.2f}"), ("same-2", f"{second.price:.2f}")],
        )

    def test_export_survives_data_validation_rejects(self):
        event = Event.objects.create(
            name="Odd", start_date=date(2027, 1, 1), end_date=date(2027, 1, 1)
        )
        TicketType.objects.create(event=event, name="Refund", price=-5)
        spec = export(event)
        self.assertEqual(spec["ticket_types"][0]["price"], "-5.00")
        errors, _ = check(spec)
        self.assertIn("ticket_types[0].price", by_path(errors))

    def test_export_refuses_cross_event_references(self):
        other = Event.objects.create(
            name="Other", start_date=date(2027, 1, 1), end_date=date(2027, 1, 1)
        )
        foreign = Session.objects.create(
            event=other,
            name="Elsewhere",
            start_time=datetime(2027, 1, 1, 8, tzinfo=UTC),
            end_time=datetime(2027, 1, 1, 9, tzinfo=UTC),
        )
        self.bundle.sessions.add(foreign)
        with self.assertRaises(ValueError):
            export(self.event)

    def test_export_of_empty_event(self):
        event = Event.objects.create(
            name="Empty", start_date=date(2027, 1, 1), end_date=date(2027, 1, 1)
        )
        spec = export(event)
        self.assertEqual(spec["ticket_types"], [])
        errors, warnings = check(spec)
        self.assertEqual(errors, [])
        self.assertEqual([w["code"] for w in warnings], ["registration_not_configured"])


class SpecParityTests(SimpleTestCase):
    """The spec carries every concrete model field except an explicit exclusion list."""

    def assert_parity(self, model, spec_model, excluded, extra=()):
        fields = {f.name for f in model._meta.concrete_fields} - excluded
        fields |= {f.name for f in model._meta.local_many_to_many}
        spec_fields = set(spec_model.model_fields) - {"key", *extra}
        self.assertEqual(spec_fields, fields, model.__name__)

    def test_parity(self):
        from events.event_spec.spec import (
            EventSection,
            ExtraChoiceSpec,
            ExtraSpec,
            PromoCodeSpec,
            SessionSpec,
            TicketTypeSpec,
        )
        from events.models import ExtraChoice

        self.assert_parity(Event, EventSection, {"id", "cloned_from"})
        self.assert_parity(Session, SessionSpec, {"id", "event", "is_active"})
        self.assert_parity(TicketType, TicketTypeSpec, {"id", "event"})
        self.assert_parity(
            Extra, ExtraSpec, {"id", "event", "cloned_from"}, extra=("choices",)
        )
        self.assert_parity(ExtraChoice, ExtraChoiceSpec, {"id", "extra"})
        self.assert_parity(
            PromoCode, PromoCodeSpec, {"id", "event", "uses_count", "created_at"}
        )


class CollectedModelErrorTests(SimpleTestCase):
    def test_ticket_type_errors_are_not_hidden_behind_each_other(self):
        spec = example_spec()
        spec["ticket_types"][2]["available_from"] = "2027-05-01T09:00:00"
        spec["ticket_types"][2]["available_until"] = "2027-04-01T09:00:00"
        spec["ticket_types"][2]["min_birthdate"] = "2009-07-01"
        errors, _ = check(spec)
        paths = {e["path"] for e in errors}
        self.assertTrue(
            {"ticket_types[2].available_until", "ticket_types[2].min_birthdate"}
            <= paths
        )
