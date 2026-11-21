"""Event spec diff and apply: round trips, id stability, refusals without writes."""

import copy
from datetime import UTC, date, datetime
from unittest.mock import patch

from django.test import TestCase

from events.event_spec import SpecError, apply, diff, example_spec, export

from events.event_spec import _apply as apply_module
from events.spec_test_support import (
    NOW,
    add_ticket,
    at_now,
    validate_at_now,
    empty_event,
    make_child,
)
from events.event_spec._diff import normalize
from events.models import (
    Event,
    Extra,
    ExtraChoice,
    PromoCode,
    Session,
    TicketType,
)


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
        other = empty_event("Other")
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
        add_ticket(event)
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
        child = make_child()
        original = apply_module.validate

        def validate_then_ticket(spec, target):
            result = original(spec, target)
            add_ticket(event, child)
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
        self.assertNotIn("choices", changes[-6]["new"])


class EmptinessCoverageTests(TestCase):
    # Models that point at spec-owned rows but are not "event in use" signals.
    ALLOWED = {
        "events.TicketType",  # spec-owned
        "events.PromoCode",
        "events.Extra",
        "events.ExtraChoice",
        "registrations.RegistrationExtra",  # exists only inside a Registration
    }

    def test_every_model_pointing_at_spec_rows_is_checked_or_allowed(self):
        from events.event_spec._validate import EMPTINESS_CHECKS

        covered = {m._meta.label for m, _ in EMPTINESS_CHECKS}
        # Registration is checked through its event FK, and holds the promo code.
        covered |= {"registrations.Registration"}
        for model in (Session, TicketType, Extra, ExtraChoice, PromoCode):
            for rel in model._meta.related_objects:
                label = rel.related_model._meta.label
                self.assertIn(
                    label,
                    covered | self.ALLOWED,
                    f"{label} points at {model.__name__} but the emptiness check ignores it",
                )

    def test_legacy_session_ticket_makes_the_event_non_empty(self):
        from events.models import Ticket

        event, _, _ = do_apply(example_spec())
        child = make_child()
        Ticket.objects.create(attendee=child, session=event.sessions.get())
        with self.assertRaises(SpecError) as ctx:
            do_apply(example_spec(), event)
        self.assertEqual(ctx.exception.errors[0]["code"], "event_not_empty")
        self.assertEqual(event.sessions.count(), 1)


class TargetGuardTests(TestCase):
    def test_open_registration_on_target_is_refused(self):
        event = empty_event(
            "Live", registration_opens_at=datetime(2026, 1, 1, tzinfo=UTC)
        )
        with self.assertRaises(SpecError) as ctx:
            do_apply(example_spec(), event)
        self.assertEqual(ctx.exception.errors[0]["code"], "registration_open_on_target")
        self.assertFalse(event.ticket_types.exists())

    def test_ticket_types_are_locked_in_pk_order(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        event, _, _ = do_apply(example_spec())
        with CaptureQueriesContext(connection) as ctx:
            do_apply(example_spec(), event)
        locks = [q["sql"] for q in ctx.captured_queries if "FOR UPDATE" in q["sql"]]
        # The event is locked first, then its ticket types in pk order.
        self.assertIn(f'FROM "{Event._meta.db_table}"', locks[0])
        ticket_table = TicketType._meta.db_table
        ticket_locks = [i for i, q in enumerate(locks) if f'"{ticket_table}"' in q]
        self.assertTrue(ticket_locks)
        self.assertGreater(min(ticket_locks), 0)
        for i in ticket_locks:
            self.assertIn(f'ORDER BY "{ticket_table}"."id"', locks[i])

    def test_unsaved_or_deleted_target_raises_spec_error(self):
        with self.assertRaises(SpecError) as ctx:
            do_apply(
                example_spec(),
                Event(name="x", start_date=date(2027, 1, 1), end_date=date(2027, 1, 1)),
            )
        self.assertEqual(ctx.exception.errors[0]["code"], "event_not_found")
        event, _, _ = do_apply(example_spec())
        stale = Event.objects.get(pk=event.pk)
        event.delete()
        with self.assertRaises(SpecError) as ctx:
            do_apply(example_spec(), stale)
        self.assertEqual(ctx.exception.errors[0]["code"], "event_not_found")

    def test_integrity_error_is_a_translated_spec_error_without_database_text(self):
        from django.db import IntegrityError

        boom = IntegrityError(
            'duplicate key value violates unique constraint "unique_promo_code_per_event"'
        )
        with patch.object(apply_module, "_write", side_effect=boom):
            with self.assertRaises(SpecError) as ctx:
                do_apply(example_spec())
        issue = ctx.exception.errors[0]
        self.assertEqual((issue["path"], issue["code"]), ("promo_codes", "integrity"))
        self.assertNotIn("duplicate key", issue["message"])
        self.assertEqual(Event.objects.count(), 0)


class SameNameRowsTests(TestCase):
    def spec(self):
        spec = example_spec()
        twin = copy.deepcopy(spec["ticket_types"][1])
        twin.update(key="child-pass-0-12-2", price=350, sort_order=25)
        spec["ticket_types"].insert(2, twin)
        spec["ticket_types"][3]["sort_order"] = 30
        return spec

    def test_same_names_round_trip_and_keep_contents(self):
        spec = self.spec()
        event, _, warnings = do_apply(spec)
        self.assertEqual(warnings, [])
        ids = {t.price: t.id for t in event.ticket_types.all()}
        _, changes, _ = do_apply(spec, event)
        self.assertEqual(changes, [])
        self.assertEqual({t.price: t.id for t in event.ticket_types.all()}, ids)
        self.assertEqual(export(event), normalize(spec))

    def test_swapped_keys_warn(self):
        spec = self.spec()
        spec["ticket_types"][1]["key"], spec["ticket_types"][2]["key"] = (
            "child-pass-0-12-2",
            "child-pass-0-12",
        )
        errors, warnings = validate_at_now(spec)
        self.assertEqual(errors, [])
        self.assertEqual(
            [w["path"] for w in warnings if w["code"] == "key_not_derived"],
            ["ticket_types[1].key", "ticket_types[2].key"],
        )

    def test_tie_on_ordering_is_a_warning_for_a_new_event(self):
        spec = self.spec()
        spec["ticket_types"][2]["sort_order"] = spec["ticket_types"][1]["sort_order"]
        errors, warnings = validate_at_now(spec)
        self.assertEqual(errors, [])
        self.assertIn(
            ("ticket_types[2].sort_order", "ambiguous_order"),
            {(w["path"], w["code"]) for w in warnings},
        )

    def test_tie_on_ordering_is_an_error_at_the_second_row_for_a_target(self):
        spec = self.spec()
        spec["ticket_types"][2]["sort_order"] = spec["ticket_types"][1]["sort_order"]
        target = empty_event("T")
        errors, _ = validate_at_now(spec, target)
        issues = {e["path"]: e["code"] for e in errors}
        self.assertEqual(issues, {"ticket_types[2].sort_order": "ambiguous_order"})

        spec = example_spec()
        spec["extras"][0]["choices"][1]["sort_order"] = spec["extras"][0]["choices"][0][
            "sort_order"
        ]
        spec["extras"][0]["choices"][1]["label"] = spec["extras"][0]["choices"][0][
            "label"
        ]
        errors, _ = validate_at_now(spec, target)
        self.assertIn("extras[0].choices[1].sort_order", {e["path"] for e in errors})


class PreservedFieldsTests(TestCase):
    def test_live_state_is_kept_on_update_and_default_on_create(self):
        event, _, _ = do_apply(example_spec())
        self.assertFalse(event.sessions.get().is_active)
        self.assertEqual(event.promo_codes.get().uses_count, 0)
        self.assertIsNone(event.cloned_from)
        self.assertIsNone(event.extras.get().cloned_from)

        source = empty_event("Src")
        source_extra = Extra.objects.create(event=source, name="Src extra")
        Session.objects.filter(pk=event.sessions.get().pk).update(is_active=True)
        PromoCode.objects.filter(pk=event.promo_codes.get().pk).update(uses_count=7)
        Event.objects.filter(pk=event.pk).update(cloned_from=source)
        Extra.objects.filter(pk=event.extras.get().pk).update(cloned_from=source_extra)

        spec = example_spec()
        spec["sessions"][0]["adults_not_checked_in"] = True
        spec["promo_codes"][0]["discount_value"] = 15
        spec["event"]["name"] = "Renamed"
        spec["extras"][0]["price"] = 250
        updated, changes, _ = do_apply(spec, event)
        self.assertEqual(len(changes), 4)
        self.assertTrue(updated.sessions.get().is_active)
        self.assertEqual(updated.promo_codes.get().uses_count, 7)
        self.assertEqual(updated.cloned_from, source)
        self.assertEqual(updated.extras.get().cloned_from, source_extra)
