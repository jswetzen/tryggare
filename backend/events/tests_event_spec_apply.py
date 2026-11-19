"""Event spec diff and apply: round trips, id stability, refusals without writes."""

import copy
from datetime import UTC, date, datetime
from unittest.mock import patch

from django.test import TestCase

from events.event_spec import SpecError, apply, diff, example_spec, export
import sys
from events.event_spec.diff import normalize
from events.models import (
    Event,
    EventTicket,
    Extra,
    ExtraChoice,
    PromoCode,
    Session,
    TicketType,
)
from families.models import Child, Family

apply_module = sys.modules["events.event_spec.apply"]
NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)


def at_now(now=NOW):
    return patch("events.models.timezone.now", return_value=now)


def do_apply(spec, event=None, now=NOW):
    with at_now(now):
        return apply(spec, event)


def row_counts():
    return tuple(
        m.objects.count()
        for m in (Event, Session, TicketType, Extra, ExtraChoice, PromoCode)
    )


def change_for(changes, kind, key):
    return next(c for c in changes if c["kind"] == kind and c["key"] == key)


class ApplyNewEventTests(TestCase):
    def test_example_round_trips(self):
        event, changes, warnings = do_apply(example_spec())
        self.assertEqual(export(event), normalize(example_spec()))
        self.assertEqual(warnings, [])
        self.assertTrue(all(c["change"] == "added" for c in changes))
        self.assertEqual([c["kind"] for c in changes][:2], ["event", "sessions"])
        self.assertEqual(event.registration_window_status, "not_open_yet")

    def test_example_applies_twice_to_separate_events(self):
        # The promo code constraint is per event, not global.
        a, _, _ = do_apply(example_spec())
        b, _, _ = do_apply(example_spec())
        self.assertEqual(PromoCode.objects.filter(code="TESTFAMILY").count(), 2)
        self.assertNotEqual(a.pk, b.pk)

    def test_forward_reference_and_references_are_set(self):
        spec = example_spec()
        spec["ticket_types"][0]["requires_ticket_type"] = "child-pass-0-12"
        event, _, _ = do_apply(spec)
        adult = event.ticket_types.get(name="Adult conference pass")
        self.assertEqual(adult.requires_ticket_type.name, "Child pass 0-12")
        bundle = event.ticket_types.get(kind="session_bundle")
        self.assertEqual([s.name for s in bundle.sessions.all()], ["Saturday workshop"])
        promo = event.promo_codes.get()
        self.assertEqual(
            [t.name for t in promo.applies_to_ticket_types.all()],
            ["Adult conference pass"],
        )
        self.assertEqual(event.extras.get().choice_rows.count(), 4)

    def test_export_applied_to_another_empty_event(self):
        first, _, _ = do_apply(example_spec())
        other = Event.objects.create(
            name="Other", start_date=date(2030, 1, 1), end_date=date(2030, 1, 1)
        )
        target, changes, _ = do_apply(export(first), other)
        self.assertEqual(target.pk, other.pk)
        self.assertEqual(export(target), export(first))
        self.assertFalse(
            set(first.ticket_types.values_list("id", flat=True))
            & set(target.ticket_types.values_list("id", flat=True))
        )


class ApplyExistingEventTests(TestCase):
    def setUp(self):
        self.event, _, _ = do_apply(example_spec())

    def ids(self):
        return {
            "types": set(self.event.ticket_types.values_list("id", flat=True)),
            "sessions": set(self.event.sessions.values_list("id", flat=True)),
            "extras": set(self.event.extras.values_list("id", flat=True)),
            "choices": set(
                ExtraChoice.objects.filter(extra__event=self.event).values_list(
                    "id", flat=True
                )
            ),
            "promos": set(self.event.promo_codes.values_list("id", flat=True)),
        }

    def test_unchanged_spec_gives_empty_diff_and_keeps_ids(self):
        before = self.ids()
        self.assertEqual(diff(self.event, example_spec()), [])
        _, changes, _ = do_apply(example_spec(), self.event)
        self.assertEqual(changes, [])
        self.assertEqual(self.ids(), before)

    def test_changed_field_is_field_by_field_and_keeps_the_id(self):
        spec = example_spec()
        spec["ticket_types"][0]["price"] = 1300
        spec["ticket_types"][0]["capacity"] = None
        spec["extras"][0]["choices"][1]["price_delta"] = 10
        before = self.ids()
        planned = diff(self.event, spec)
        _, changes, _ = do_apply(spec, self.event)
        self.assertEqual(planned, changes)
        c = change_for(changes, "ticket_types", "adult-conference-pass")
        self.assertEqual(c["change"], "changed")
        self.assertEqual(
            c["fields"],
            {
                "price": {"old": "1200.00", "new": "1300.00"},
                "capacity": {"old": 150, "new": None},
            },
        )
        choice = change_for(changes, "choices", "m")
        self.assertEqual(choice["parent"], "t-shirt")
        self.assertEqual(len(changes), 2)
        self.assertEqual(self.ids(), before)
        self.assertEqual(
            self.event.ticket_types.get(name="Adult conference pass").price, 1300
        )

    def test_rename_is_remove_plus_add(self):
        spec = example_spec()
        spec["ticket_types"][0]["name"] = "Grown-up pass"
        spec["ticket_types"][0]["key"] = "grown-up-pass"
        spec["promo_codes"][0]["applies_to_ticket_types"] = ["grown-up-pass"]
        old_id = self.event.ticket_types.get(name="Adult conference pass").id
        _, changes, _ = do_apply(spec, self.event)
        self.assertEqual(
            change_for(changes, "ticket_types", "adult-conference-pass")["change"],
            "removed",
        )
        self.assertEqual(
            change_for(changes, "ticket_types", "grown-up-pass")["change"], "added"
        )
        self.assertFalse(TicketType.objects.filter(id=old_id).exists())
        self.assertEqual(export(self.event), normalize(spec))

    def test_removals_and_reordered_reference_lists(self):
        spec = example_spec()
        spec["promo_codes"][0]["applies_to_ticket_types"] = [
            "adult-conference-pass",
            "child-pass-0-12",
        ]
        do_apply(spec, self.event)
        spec["promo_codes"][0]["applies_to_ticket_types"].reverse()
        self.assertEqual(diff(self.event, spec), [])

        spec["promo_codes"] = []
        spec["extras"][0]["choices"] = spec["extras"][0]["choices"][:2]
        spec["ticket_types"] = spec["ticket_types"][:3]
        spec["sessions"] = []
        _, changes, _ = do_apply(spec, self.event)
        self.assertEqual(
            sorted((c["kind"], c["key"]) for c in changes if c["change"] == "removed"),
            [
                ("choices", "l"),
                ("choices", "xl"),
                ("promo_codes", "testfamily"),
                ("sessions", "saturday-workshop"),
                ("ticket_types", "saturday-workshop-13-17"),
            ],
        )
        self.assertEqual(export(self.event), normalize(spec))

    def test_removed_session_does_not_delete_a_kept_extra(self):
        spec = example_spec()
        spec["extras"][0]["session"] = "saturday-workshop"
        do_apply(spec, self.event)
        extra_id = self.event.extras.get().id
        spec["extras"][0]["session"] = None
        spec["ticket_types"] = spec["ticket_types"][:3]
        spec["sessions"] = []
        do_apply(spec, self.event)
        self.assertEqual(self.event.extras.get().id, extra_id)

    def test_promo_code_can_move_to_a_new_key(self):
        spec = example_spec()
        spec["promo_codes"][0]["key"] = "family"
        do_apply(spec, self.event)
        self.assertEqual(self.event.promo_codes.get().code, "TESTFAMILY")


class RefusalTests(TestCase):
    def test_non_empty_event_is_refused_without_writes(self):
        event, _, _ = do_apply(example_spec())
        child = Child.objects.create(
            family=Family.objects.create(),
            first_name="T",
            last_name="C",
            birthdate=date(2020, 1, 1),
        )
        EventTicket.objects.create(attendee=child, event=event)
        before, snapshot = row_counts(), export(event)
        spec = example_spec()
        spec["ticket_types"][0]["price"] = 1
        with self.assertRaises(SpecError) as ctx:
            do_apply(spec, event)
        self.assertEqual(ctx.exception.errors[0]["code"], "event_not_empty")
        self.assertEqual(row_counts(), before)
        self.assertEqual(export(event), snapshot)

    def test_emptiness_is_rechecked_inside_the_transaction(self):
        event, _, _ = do_apply(example_spec())
        child = Child.objects.create(
            family=Family.objects.create(),
            first_name="T",
            last_name="C",
            birthdate=date(2020, 1, 1),
        )
        original = apply_module.validate

        def validate_then_ticket(spec, target):
            result = original(spec, target)
            EventTicket.objects.create(attendee=child, event=event)
            return result

        before = row_counts()
        with patch.object(apply_module, "validate", validate_then_ticket):
            with self.assertRaises(SpecError) as ctx:
                do_apply(example_spec(), event)
        self.assertEqual(ctx.exception.errors[0]["code"], "event_not_empty")
        self.assertEqual(row_counts(), before)

    def test_invalid_spec_is_refused_without_writes(self):
        before = row_counts()
        spec = example_spec()
        spec["ticket_types"][2]["min_birthdate"] = "2009-07-01"
        with self.assertRaises(SpecError) as ctx:
            do_apply(spec)
        self.assertEqual(
            ctx.exception.errors[0]["path"], "ticket_types[2].min_birthdate"
        )
        self.assertEqual(row_counts(), before)

    def test_open_registration_is_refused(self):
        with self.assertRaises(SpecError) as ctx:
            do_apply(example_spec(), now=datetime(2027, 4, 1, tzinfo=UTC))
        self.assertEqual(ctx.exception.errors[0]["code"], "registration_open")
        self.assertEqual(Event.objects.count(), 0)

    def test_failure_midway_rolls_everything_back(self):
        event, _, _ = do_apply(example_spec())
        before, snapshot = row_counts(), export(event)
        spec = example_spec()
        spec["ticket_types"][0]["price"] = 5
        spec["ticket_types"] = spec["ticket_types"][:3]
        original = apply_module._save

        def failing(obj, model, fields, **parents):
            if model is PromoCode:
                raise RuntimeError("boom")
            return original(obj, model, fields, **parents)

        with patch.object(apply_module, "_save", failing):
            with self.assertRaises(RuntimeError):
                do_apply(spec, event)
        self.assertEqual(row_counts(), before)
        self.assertEqual(export(event), snapshot)

    def test_new_event_failure_leaves_no_event(self):
        before = row_counts()
        with patch.object(apply_module, "_write", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                do_apply(example_spec())
        self.assertEqual(row_counts(), before)


class DiffTests(TestCase):
    def test_diff_against_no_event_is_all_added_and_ordered(self):
        changes = diff(None, example_spec())
        self.assertEqual(
            [c["kind"] for c in changes],
            ["event", "sessions"]
            + ["ticket_types"] * 4
            + ["extras"]
            + ["choices"] * 4
            + ["promo_codes"],
        )
        self.assertEqual(changes, diff(None, copy.deepcopy(example_spec())))
        self.assertNotIn("choices", changes[-6]["new"])
