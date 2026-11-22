from django.test import SimpleTestCase

from .rules import (
    FeatureRequestError,
    REACH_THRESHOLDS,
    clean_input,
    derive,
    dedupe_key,
    spec_path_exists,
)
from .services import _reach_for_count

BASE = {
    "title": "Family price",
    "problem": "Families want one price for the group.",
    "desired": "A price for a group of attendees.",
    "touches": ["cap:family_groups"],
    "severity": "friction",
}


def errors_for(**changes):
    data = {**BASE, **changes}
    with_none = {k: v for k, v in data.items() if v is not None}
    try:
        clean_input(with_none)
    except FeatureRequestError as exc:
        return exc.errors
    return []


def codes(errors):
    return {e["code"] for e in errors}


class VocabularyTests(SimpleTestCase):
    def test_known_capability_and_new_id_pass(self):
        self.assertEqual(errors_for(touches=["cap:family_groups"]), [])
        self.assertEqual(errors_for(touches=["new:extra_eligibility"]), [])

    def test_unknown_capability_is_an_error(self):
        self.assertIn("unknown_term", codes(errors_for(touches=["cap:made_up"])))

    def test_validator_code_must_exist(self):
        self.assertEqual(errors_for(touches=["code:registration_open"]), [])
        self.assertIn("unknown_term", codes(errors_for(touches=["code:not_a_code"])))

    def test_field_must_exist_on_a_model(self):
        self.assertEqual(errors_for(touches=["field:Extra.applies_to"]), [])
        self.assertIn("unknown_term", codes(errors_for(touches=["field:Extra.nope"])))
        self.assertIn("unknown_term", codes(errors_for(touches=["field:Ghost.name"])))

    def test_spec_path_uses_brackets_for_lists(self):
        self.assertTrue(spec_path_exists("ticket_types[].requires_ticket_type"))
        self.assertTrue(spec_path_exists("event.name"))
        self.assertFalse(spec_path_exists("ticket_types[].no_such_field"))
        self.assertFalse(spec_path_exists("event[].name"))

    def test_prefix_is_required(self):
        self.assertIn("unknown_term", codes(errors_for(touches=["family groups"])))
        self.assertEqual(errors_for(touches=["admin:copy_event"]), [])

    def test_unknown_term_error_does_not_echo_the_term(self):
        errs = errors_for(touches=["cap:Anna-Lindqvist"])
        self.assertNotIn("Anna", " ".join(e["message"] for e in errs))

    def test_too_many_or_empty_touches(self):
        self.assertIn("invalid", codes(errors_for(touches=[])))


class PersonalDataTests(SimpleTestCase):
    def assert_refused(self, value, kind):
        errs = errors_for(problem=value)
        self.assertEqual(codes(errs), {"personal_data"}, value)
        self.assertIn(kind, errs[0]["message"])
        self.assertNotIn(value, errs[0]["message"])

    def test_email_phone_and_personnummer(self):
        self.assert_refused("Mail anna@example.com about it", "email")
        self.assert_refused("Call +46 70 123 45 67 for it", "phone")
        self.assert_refused("Child 120302-1234 needs a ticket", "personnummer")

    def test_iso_date_uuid_and_reference_code(self):
        self.assert_refused("Starts on 2027-06-20", "a date")
        self.assert_refused("Id 3f2504e0-4f89-41d3-9a0c-0305e82c3301 here", "UUID")
        self.assert_refused("Booking ABC23456 was moved", "registration-reference")

    def test_obfuscated_or_loose_forms_are_refused(self):
        for value, kind in [
            ("Starts on 2027\u200b-06-20", "a date"),
            ("Starts on 2027/6/20", "a date"),
            ("Starts on 20.06.2027", "a date"),
            ("Booking abc23456 was moved", "registration-reference"),
            ("Booking ABC2\u200b3456 was moved", "registration-reference"),
            ("See https://example.org/120302-1234", "personnummer"),
            ("See https://example.org/?to=anna@example.com", "email"),
        ]:
            with self.subTest(value=value):
                self.assert_refused(value, kind)

    def test_age_bands_and_ranges_pass(self):
        self.assertEqual(errors_for(problem="Ages 13-17, 3-5 days, 2 of 4."), [])

    def test_free_form_touch_terms_are_checked(self):
        errs = errors_for(touches=["new:extra_eligibility", "new:p1203021234"])
        self.assertEqual(codes(errs), {"personal_data"})
        self.assertEqual(errs[0]["path"], "touches[1]")
        self.assertNotIn("1203021234", errs[0]["message"])

    def test_ordinary_capitalised_words_pass(self):
        self.assertEqual(errors_for(problem="CHILDREN aged 13-17 need a ticket."), [])

    def test_free_text_fields_are_all_checked(self):
        for field in ("title", "desired", "brief_fragment"):
            with self.subTest(field=field):
                errs = errors_for(**{field: "anna@example.com"})
                self.assertEqual(codes(errs), {"personal_data"})
        errs = errors_for(tried=["Ask anna@example.com"])
        self.assertEqual(errs[0]["path"], "tried[0]")
        errs = errors_for(workaround={"used": "Filed on 2027-06-20", "cost": "none"})
        self.assertEqual(errs[0]["path"], "workaround.used")


class LimitsTests(SimpleTestCase):
    def test_lengths(self):
        self.assertEqual(codes(errors_for(title="x" * 101)), {"too_long"})
        self.assertEqual(codes(errors_for(problem="x" * 601)), {"too_long"})
        self.assertEqual(codes(errors_for(tried=["x"] * 6)), {"invalid"})

    def test_workaround_shape(self):
        ok = errors_for(workaround={"used": "A 0 SEK ticket", "cost": "extra_steps"})
        self.assertEqual(ok, [])
        self.assertEqual(
            codes(errors_for(workaround={"used": "x", "cost": "sometimes"})),
            {"invalid"},
        )
        self.assertEqual(
            codes(errors_for(workaround={"used": "x", "note": "y"})), {"invalid"}
        )

    def test_severity_and_unknown_keys(self):
        self.assertEqual(codes(errors_for(severity="huge")), {"invalid"})
        self.assertEqual(codes(errors_for(price=5)), {"extra_forbidden"})

    def test_input_is_stripped_and_optional_fields_default(self):
        out = clean_input({**BASE, "title": "  Family price  "})
        self.assertEqual(out["title"], "Family price")
        self.assertIsNone(out["brief_fragment"])
        self.assertEqual(out["tried"], [])
        self.assertIsNone(out["workaround"])


class DerivationTests(SimpleTestCase):
    def test_dedupe_key_takes_the_highest_priority_term(self):
        self.assertEqual(
            dedupe_key(
                ["spec:event.name", "cap:family_groups", "code:registration_open"]
            ),
            "cap:family_groups",
        )
        self.assertEqual(
            dedupe_key(["field:Extra.applies_to", "code:registration_open"]),
            "code:registration_open",
        )

    def test_validator_layers_and_evidence(self):
        cleaned = clean_input(
            {
                **BASE,
                "touches": ["code:registration_open", "spec:ticket_types[].sessions"],
            }
        )
        out = derive(cleaned)
        self.assertEqual(out["validator"], "existing")
        self.assertEqual(out["layers"], ["model", "validator"])
        self.assertEqual(
            out["evidence"],
            [
                {"kind": "validation_code", "ref": "code:registration_open"},
                {"kind": "spec_path", "ref": "spec:ticket_types[].sessions"},
            ],
        )
        self.assertEqual(derive(clean_input(BASE))["validator"], "no")

    def test_reach_thresholds(self):
        self.assertEqual(REACH_THRESHOLDS[0], (5, "most_events"))
        self.assertEqual(_reach_for_count(1), "few_events")
        self.assertEqual(_reach_for_count(2), "some_events")
        self.assertEqual(_reach_for_count(4), "some_events")
        self.assertEqual(_reach_for_count(5), "most_events")
