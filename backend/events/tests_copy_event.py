"""Copying an event: events/services.py::copy_event and the admin action."""

from datetime import UTC, date, datetime
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from events.event_spec import SpecError
from events.spec_test_support import foreign_session
from events.models import (
    Event,
    Extra,
    ExtraChoice,
    PromoCode,
    EventTicket,
    Session,
    SessionTicket,
    TicketType,
)
from families.models import Child, Family
from accounts.models import AdminUser
from tests.support import NonManifestStaticfilesTestCase


class CopyEventTest(TestCase):
    """events/services.py::copy_event."""

    def setUp(self):
        # The source window (March 2027) must stay in the future of the test clock.
        patcher = patch(
            "django.utils.timezone.now",
            return_value=datetime(2026, 11, 19, 12, 0, tzinfo=UTC),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.tz = timezone.get_default_timezone()
        self.source = Event.objects.create(
            name="Spring Camp",
            start_date=date(2027, 3, 20),
            end_date=date(2027, 3, 22),
            ticket_rule_default="children",
            price=250,
            registration_opens_at=self._stockholm(2027, 3, 1, 8, 0),
            registration_closes_at=self._stockholm(2027, 3, 15, 23, 59),
            header_image_url="https://example.com/hero.png",
            accent_color="#2563EB",
        )
        self.sat = Session.objects.create(
            event=self.source,
            name="Saturday",
            start_time=self._stockholm(2027, 3, 20, 9, 0),
            end_time=self._stockholm(2027, 3, 20, 17, 0),
            is_active=True,
            ticket_rule="all",
            adults_not_checked_in=True,
        )
        self.sun = Session.objects.create(
            event=self.source,
            name="Sunday",
            start_time=self._stockholm(2027, 3, 21, 9, 0),
            end_time=self._stockholm(2027, 3, 21, 12, 0),
        )
        self.family_type = TicketType.objects.create(
            event=self.source, name="Family", price=400, sort_order=1
        )
        self.child_type = TicketType.objects.create(
            event=self.source,
            name="Child",
            price=100,
            applies_to="child",
            min_birthdate=date(2015, 3, 21),
            max_birthdate=date(2022, 3, 20),
            available_from=self._stockholm(2027, 3, 1, 8, 0),
            available_until=self._stockholm(2027, 3, 10, 12, 0),
            capacity=30,
            requires_ticket_type=self.family_type,
            max_per_required=4,
            is_active=False,
            is_hidden=True,
        )
        self.day_type = TicketType.objects.create(
            event=self.source,
            name="Saturday only",
            price=80,
            kind=TicketType.Kind.SESSION_BUNDLE,
        )
        self.day_type.sessions.set([self.sat])
        self.dinner = Extra.objects.create(
            event=self.source, session=self.sat, name="Dinner", price=60
        )
        ExtraChoice.objects.create(extra=self.dinner, label="Veg", price_delta=0)
        ExtraChoice.objects.create(
            extra=self.dinner, label="Meat", price_delta=10, is_active=False
        )
        self.shirt = Extra.objects.create(
            event=self.source, name="T-shirt", price=100, is_active=False
        )
        self.promo = PromoCode.objects.create(
            event=self.source,
            code="early",
            discount_type="percent",
            discount_value=10,
            max_uses=5,
            uses_count=3,
            valid_from=self._stockholm(2027, 3, 1, 0, 0),
            valid_until=self._stockholm(2027, 3, 10, 23, 59),
            is_active=False,
        )
        self.promo.applies_to_ticket_types.set([self.family_type])
        self.promo.unlocks_ticket_types.set([self.child_type])

    def _stockholm(self, *args):
        return timezone.make_aware(datetime(*args), self.tz)

    def _copy(self, start=date(2027, 4, 3)):
        from events.services import copy_event

        return copy_event(self.source, name="Spring Camp II", start_date=start)

    def test_copies_event_settings_and_shifts_dates(self):
        new = self._copy()

        self.assertNotEqual(new.pk, self.source.pk)
        self.assertEqual(new.name, "Spring Camp II")
        self.assertEqual(new.cloned_from, self.source)
        self.assertEqual(new.start_date, date(2027, 4, 3))
        self.assertEqual(new.end_date, date(2027, 4, 5))
        self.assertEqual(new.ticket_rule_default, "children")
        self.assertEqual(new.price, 250)
        self.assertEqual(new.header_image_url, "https://example.com/hero.png")
        self.assertEqual(new.accent_color, "#2563EB")
        self.assertEqual(
            timezone.localtime(new.registration_opens_at, self.tz).date(),
            date(2027, 3, 15),
        )
        closes = timezone.localtime(new.registration_closes_at, self.tz)
        self.assertEqual(
            (closes.date(), closes.hour, closes.minute), (date(2027, 3, 29), 23, 59)
        )
        self.assertEqual(list(self.source.copies.all()), [new])

    def test_datetimes_keep_wall_clock_across_dst(self):
        # Clocks go forward on 2027-03-28; 09:00 must stay 09:00 local.
        new = self._copy()

        start = new.sessions.get(name="Saturday").start_time
        self.assertEqual(self.sat.start_time.astimezone(UTC).hour, 8)
        self.assertEqual(timezone.localtime(start, self.tz).hour, 9)
        self.assertEqual(start.astimezone(UTC).hour, 7)
        self.assertEqual(timezone.localtime(start, self.tz).date(), date(2027, 4, 3))

    def test_negative_shift_across_dst(self):
        new = self._copy(start=date(2027, 3, 6))

        start = timezone.localtime(
            new.sessions.get(name="Saturday").start_time, self.tz
        )
        self.assertEqual((start.date(), start.hour), (date(2027, 3, 6), 9))

    def test_sessions_copied(self):
        new = self._copy()

        sat = new.sessions.get(name="Saturday")
        self.assertNotEqual(sat.pk, self.sat.pk)
        self.assertTrue(self.sat.is_active)
        self.assertFalse(sat.is_active)
        self.assertEqual(sat.ticket_rule, "all")
        self.assertTrue(sat.adults_not_checked_in)
        self.assertEqual(
            timezone.localtime(sat.end_time, self.tz).replace(tzinfo=None),
            datetime(2027, 4, 3, 17, 0),
        )
        self.assertFalse(new.sessions.get(name="Sunday").is_active)
        self.assertEqual(new.sessions.count(), 2)

    def test_ticket_types_copied_with_remapped_references(self):
        new = self._copy()

        types = {t.name: t for t in new.ticket_types.all()}
        self.assertEqual(set(types), {"Family", "Child", "Saturday only"})
        old_ids = {self.family_type.pk, self.child_type.pk, self.day_type.pk}
        self.assertFalse(old_ids & {t.pk for t in types.values()})

        child = types["Child"]
        self.assertEqual(child.requires_ticket_type, types["Family"])
        self.assertEqual(child.max_per_required, 4)
        self.assertEqual(child.capacity, 30)
        self.assertEqual(child.applies_to, "child")
        self.assertTrue(child.is_hidden)
        self.assertFalse(child.is_active)
        self.assertEqual(types["Family"].price, 400)
        self.assertEqual(types["Family"].sort_order, 1)

        bundle = types["Saturday only"]
        self.assertEqual(bundle.kind, TicketType.Kind.SESSION_BUNDLE)
        self.assertEqual(
            set(bundle.sessions.all()), {new.sessions.get(name="Saturday")}
        )

    def test_extra_gate_follows_the_copied_ticket_types(self):
        self.dinner.ticket_types.add(self.child_type)
        new = self._copy()
        gate = new.extras.get(name="Dinner").ticket_types.get()
        self.assertEqual(gate.event, new)
        self.assertNotEqual(gate.pk, self.child_type.pk)
        self.assertEqual(gate.name, "Child")

    def test_ticket_type_dates_and_birthdate_bounds_shift(self):
        new = self._copy()  # +14 days

        child = new.ticket_types.get(name="Child")
        self.assertEqual(child.min_birthdate, date(2015, 4, 4))
        self.assertEqual(child.max_birthdate, date(2022, 4, 3))
        until = timezone.localtime(child.available_until, self.tz)
        # 2027-03-10 12:00 CET -> 2027-03-24 12:00 CET (before the DST change).
        self.assertEqual((until.date(), until.hour), (date(2027, 3, 24), 12))
        self.assertIsNone(new.ticket_types.get(name="Family").available_from)
        self.assertIsNone(new.ticket_types.get(name="Family").min_birthdate)

    def test_registration_close_crossing_dst_keeps_local_time(self):
        new = self._copy()

        # 23:59 CET is 22:59 UTC; 23:59 CEST is 21:59 UTC.
        self.assertEqual(self.source.registration_closes_at.astimezone(UTC).hour, 22)
        self.assertEqual(new.registration_closes_at.astimezone(UTC).hour, 21)

    def test_age_bounds_stay_on_the_anniversary_across_a_leap_day(self):
        # Delta is 364 days; a plain shift would give 2020-06-10.
        source = Event.objects.create(
            name="June", start_date=date(2026, 6, 12), end_date=date(2026, 6, 12)
        )
        TicketType.objects.create(
            event=source,
            name="Kids",
            price=0,
            max_birthdate=date(2019, 6, 12),
            min_birthdate=date(2013, 6, 13),
        )
        from events.services import copy_event

        new = copy_event(source, name="June 27", start_date=date(2027, 6, 11))

        kids = new.ticket_types.get()
        self.assertEqual(kids.max_birthdate, date(2020, 6, 11))
        self.assertEqual(kids.min_birthdate, date(2014, 6, 12))

    def test_age_bound_off_the_anniversary_is_refused_with_its_path(self):
        # The old copier shifted such a bound and produced a row that failed
        # clean(); apply's validation now refuses it.
        from events.services import copy_event

        TicketType.objects.create(
            event=self.source, name="Odd", price=0, max_birthdate=date(2020, 1, 1)
        )
        with self.assertRaises(SpecError) as ctx:
            copy_event(self.source, name="X", start_date=date(2027, 4, 3))
        self.assertIn(
            "max_birthdate",
            {e["path"].rsplit(".", 1)[-1] for e in ctx.exception.errors},
        )
        self.assertFalse(Event.objects.filter(name="X").exists())

    def test_negative_price_is_refused_and_nothing_is_created(self):
        from events.services import copy_event

        TicketType.objects.filter(pk=self.family_type.pk).update(price=-5)
        with self.assertRaises(SpecError) as ctx:
            copy_event(self.source, name="X", start_date=date(2027, 4, 3))
        self.assertTrue(any("price" in e["path"] for e in ctx.exception.errors))
        self.assertFalse(Event.objects.filter(name="X").exists())

    def test_open_or_past_window_is_dropped(self):
        # Source window 2027-03-01..15; shifting back puts it in the past.
        past = self._copy(start=date(2020, 3, 20))
        self.assertIsNone(past.registration_opens_at)
        self.assertIsNone(past.registration_closes_at)

        # A shifted window that is open right now is dropped too.
        now = timezone.now()
        Event.objects.filter(pk=self.source.pk).update(
            registration_opens_at=now - timezone.timedelta(days=1),
            registration_closes_at=now + timezone.timedelta(days=30),
        )
        self.source.refresh_from_db()
        from events.services import copy_event

        live = copy_event(self.source, name="Live", start_date=self.source.start_date)
        self.assertIsNone(live.registration_opens_at)
        self.assertIsNone(live.registration_closes_at)
        self.assertEqual(live.sessions.count(), 2)

    def test_future_window_is_kept(self):
        new = self._copy()
        self.assertIsNotNone(new.registration_opens_at)
        self.assertIsNotNone(new.registration_closes_at)

    def test_autumn_dst_change_keeps_wall_clock(self):
        # 09:00 CEST (+02:00) moved past 2027-10-31 must be 09:00 CET (+01:00),
        # not the 08:00 a fixed-offset shift would give.
        from datetime import timedelta

        from events.services import copy_event

        source = Event.objects.create(
            name="Autumn", start_date=date(2027, 9, 18), end_date=date(2027, 9, 18)
        )
        Session.objects.create(
            event=source,
            name="Morning",
            start_time=self._stockholm(2027, 9, 18, 9, 0),
            end_time=self._stockholm(2027, 9, 18, 11, 0),
        )
        new = copy_event(source, name="Autumn 2", start_date=date(2027, 11, 6))

        start = timezone.localtime(new.sessions.get().start_time, self.tz)
        self.assertEqual((start.date(), start.hour), (date(2027, 11, 6), 9))
        self.assertEqual(start.utcoffset(), timedelta(hours=1))

    def test_tied_choice_ordering_still_copies(self):
        ExtraChoice.objects.filter(extra=self.dinner).update(
            label="Same", price_delta=0
        )
        ExtraChoice.objects.filter(extra=self.dinner).update(sort_order=0)

        new = self._copy()

        self.assertEqual(new.extras.get(name="Dinner").choice_rows.count(), 2)

    def test_clones_are_recorded_for_event_and_extras(self):
        new = self._copy()

        self.assertEqual(new.cloned_from, self.source)
        self.assertEqual(new.extras.get(name="Dinner").cloned_from, self.dinner)
        self.assertEqual(new.extras.get(name="T-shirt").cloned_from, self.shirt)

    def test_leap_day_start_uses_nearest_leap_year(self):
        from events.services import copy_event

        source = Event.objects.create(
            name="Leap", start_date=date(2028, 2, 29), end_date=date(2028, 2, 29)
        )
        TicketType.objects.create(
            event=source, name="K", price=0, max_birthdate=date(2016, 2, 29)
        )
        new = copy_event(source, name="Leap 2", start_date=date(2029, 2, 28))
        self.assertEqual(new.ticket_types.get().max_birthdate, date(2017, 2, 28))

    def test_every_copied_row_passes_full_clean(self):
        new = self._copy()

        new.full_clean()
        for obj in [
            *new.sessions.all(),
            *new.ticket_types.all(),
            *new.extras.all(),
            *new.promo_codes.all(),
        ]:
            obj.full_clean()

    def test_cross_event_reference_is_refused_before_anything_is_created(self):
        from events.services import copy_event

        other = Event.objects.create(
            name="Other", start_date=date(2027, 1, 1), end_date=date(2027, 1, 1)
        )
        foreign = TicketType.objects.create(event=other, name="Foreign", price=1)
        self.promo.applies_to_ticket_types.add(foreign)

        with self.assertRaisesMessage(SpecError, "Foreign"):
            copy_event(self.source, name="Nope", start_date=date(2027, 5, 1))
        self.assertFalse(Event.objects.filter(name="Nope").exists())

    def test_cross_event_session_in_bundle_is_refused(self):
        from events.services import copy_event

        self.day_type.sessions.add(foreign_session("Elsewhere"))

        with self.assertRaisesMessage(SpecError, "Elsewhere"):
            copy_event(self.source, name="Nope", start_date=date(2027, 5, 1))

    def test_extras_copied_with_choices_and_session_remap(self):
        new = self._copy()

        extras = {e.name: e for e in new.extras.all()}
        self.assertEqual(set(extras), {"Dinner", "T-shirt"})
        dinner = extras["Dinner"]
        self.assertEqual(dinner.session, new.sessions.get(name="Saturday"))
        self.assertEqual(dinner.cloned_from, self.dinner)
        self.assertEqual(dinner.price, 60)
        self.assertEqual(
            set(dinner.choice_rows.values_list("label", "price_delta", "is_active")),
            {("Veg", 0, True), ("Meat", 10, False)},
        )
        self.assertIsNone(extras["T-shirt"].session)
        self.assertFalse(extras["T-shirt"].is_active)

    def test_promo_codes_copied_remapped_and_counter_reset(self):
        new = self._copy()

        promo = new.promo_codes.get()
        self.assertNotEqual(promo.pk, self.promo.pk)
        self.assertEqual(promo.code, "EARLY")
        self.assertEqual(promo.discount_type, "percent")
        self.assertEqual(promo.discount_value, 10)
        self.assertEqual(promo.max_uses, 5)
        self.assertEqual(promo.uses_count, 0)
        self.assertFalse(promo.is_active)
        self.assertEqual(
            set(promo.applies_to_ticket_types.all()),
            {new.ticket_types.get(name="Family")},
        )
        self.assertEqual(
            set(promo.unlocks_ticket_types.all()),
            {new.ticket_types.get(name="Child")},
        )
        self.assertEqual(
            timezone.localtime(promo.valid_until, self.tz).date(), date(2027, 3, 24)
        )

    def test_nothing_in_the_copy_points_at_source_rows(self):
        new = self._copy()

        new_session_ids = set(new.sessions.values_list("pk", flat=True))
        new_type_ids = set(new.ticket_types.values_list("pk", flat=True))
        for t in new.ticket_types.all():
            self.assertTrue({s.pk for s in t.sessions.all()} <= new_session_ids)
            if t.requires_ticket_type_id:
                self.assertIn(t.requires_ticket_type_id, new_type_ids)
        for e in new.extras.all():
            if e.session_id:
                self.assertIn(e.session_id, new_session_ids)
        for p in new.promo_codes.all():
            self.assertTrue(
                {t.pk for t in p.applies_to_ticket_types.all()} <= new_type_ids
            )
            self.assertTrue(
                {t.pk for t in p.unlocks_ticket_types.all()} <= new_type_ids
            )

    def test_registrations_and_tickets_not_copied(self):
        from registrations.models import Registration

        family = Family.objects.create()
        child = Child.objects.create(
            family=family,
            first_name="A",
            last_name="B",
            birthdate=date(2018, 1, 1),
        )
        Registration.objects.create(
            event=self.source,
            family=family,
            contact_email="a@example.com",
            verification_token_hash="x" * 64,
        )
        EventTicket.objects.create(
            attendee=child, event=self.source, ticket_type=self.child_type
        )
        SessionTicket.objects.create(attendee=child, session=self.sat)

        new = self._copy()

        self.assertFalse(new.registrations.exists())
        self.assertFalse(EventTicket.objects.filter(event=new).exists())
        self.assertFalse(SessionTicket.objects.filter(session__event=new).exists())

    def test_source_unchanged(self):
        before = {
            "event": Event.objects.filter(pk=self.source.pk).values().get(),
            "sessions": list(self.source.sessions.order_by("pk").values()),
            "types": list(self.source.ticket_types.order_by("pk").values()),
            "extras": list(self.source.extras.order_by("pk").values()),
            "promos": list(self.source.promo_codes.order_by("pk").values()),
        }

        self._copy()

        self.assertEqual(
            before,
            {
                "event": Event.objects.filter(pk=self.source.pk).values().get(),
                "sessions": list(self.source.sessions.order_by("pk").values()),
                "types": list(self.source.ticket_types.order_by("pk").values()),
                "extras": list(self.source.extras.order_by("pk").values()),
                "promos": list(self.source.promo_codes.order_by("pk").values()),
            },
        )
        self.assertEqual(
            self.promo.__class__.objects.get(pk=self.promo.pk).uses_count, 3
        )
        self.assertEqual(self.source.sessions.count(), 2)

    def test_failure_rolls_everything_back(self):
        from events.services import copy_event

        from events.event_spec import _apply

        real_save = _apply._save

        def fail_on_promo(obj, model, *args, **kwargs):
            if model is PromoCode:
                raise RuntimeError
            return real_save(obj, model, *args, **kwargs)

        with patch("events.event_spec._apply._save", side_effect=fail_on_promo):
            with self.assertRaises(RuntimeError):
                copy_event(self.source, name="Doomed", start_date=date(2027, 5, 1))

        self.assertFalse(Event.objects.filter(name="Doomed").exists())
        self.assertEqual(Session.objects.count(), 2)

    def test_source_deletion_keeps_copy(self):
        new = self._copy()
        TicketType.objects.filter(event=self.source).update(requires_ticket_type=None)
        self.source.delete()
        new.refresh_from_db()
        self.assertIsNone(new.cloned_from)


class CopyEventAdminActionTest(NonManifestStaticfilesTestCase, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = AdminUser.objects.create_superuser("copyadmin", "pw12345")
        cls.a = Event.objects.create(
            name="Alpha", start_date=date(2027, 6, 1), end_date=date(2027, 6, 3)
        )
        cls.b = Event.objects.create(
            name="Beta", start_date=date(2027, 7, 1), end_date=date(2027, 7, 3)
        )
        Session.objects.create(
            event=cls.a,
            name="Opening",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1),
        )

    def setUp(self):
        # The source window (March 2027) must stay in the future of the test clock.
        patcher = patch(
            "django.utils.timezone.now",
            return_value=datetime(2026, 11, 19, 12, 0, tzinfo=UTC),
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client.force_login(self.user)
        self.url = reverse("admin:events_event_changelist")

    def _post(self, ids, follow=False, **extra):
        data = {
            "action": "copy_event_action",
            "_selected_action": [str(i) for i in ids],
            **extra,
        }
        return self.client.post(self.url, data, follow=follow)

    def test_first_step_shows_form(self):
        response = self._post([self.a.pk])
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="start_date"')
        self.assertEqual(Event.objects.count(), 2)

    def test_apply_copies_and_redirects_to_new_event(self):
        response = self._post(
            [self.a.pk], apply="yes", name="Alpha 2028", start_date="2028-06-01"
        )

        new = Event.objects.get(name="Alpha 2028")
        self.assertRedirects(
            response, reverse("admin:events_event_change", args=[new.pk])
        )
        self.assertEqual(new.cloned_from, self.a)
        self.assertEqual(new.end_date, date(2028, 6, 3))
        self.assertEqual(new.sessions.count(), 1)

    def test_more_than_one_selected_is_an_error(self):
        response = self._post([self.a.pk, self.b.pk], follow=True)
        self.assertContains(response, "Select exactly one event to copy.")
        self.assertEqual(Event.objects.count(), 2)

    def test_invalid_date_rerenders_form(self):
        response = self._post([self.a.pk], apply="yes", name="X", start_date="nope")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Event.objects.count(), 2)

    def test_copied_from_is_read_only_on_change_page(self):
        new = Event.objects.create(
            name="Gamma",
            start_date=date(2027, 8, 1),
            end_date=date(2027, 8, 1),
            cloned_from=self.a,
        )
        response = self.client.get(reverse("admin:events_event_change", args=[new.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("cloned_from", response.context["adminform"].form.fields)
        self.assertContains(response, "Alpha")

    def test_cross_event_reference_shows_error_not_500(self):
        other = Event.objects.create(
            name="Other", start_date=date(2027, 1, 1), end_date=date(2027, 1, 1)
        )
        foreign = TicketType.objects.create(event=other, name="Foreign", price=1)
        promo = PromoCode.objects.create(event=self.a, code="X")
        promo.applies_to_ticket_types.add(foreign)

        response = self._post(
            [self.a.pk],
            apply="yes",
            name="Alpha 2",
            start_date="2028-06-01",
            follow=True,
        )
        self.assertContains(response, "Foreign")
        self.assertFalse(Event.objects.filter(name="Alpha 2").exists())

    def test_refused_spec_shows_error_with_paths_not_500(self):
        TicketType.objects.create(event=self.a, name="Bad", price=-1)

        response = self._post(
            [self.a.pk],
            apply="yes",
            name="Alpha 3",
            start_date="2028-06-01",
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Could not copy")
        self.assertContains(response, "ticket_types[0].price")
        self.assertFalse(Event.objects.filter(name="Alpha 3").exists())

    def test_spec_warnings_from_a_copy_are_shown(self):
        # An event with no registration window gets the "self-serve is off" warning.
        response = self._post(
            [self.a.pk],
            apply="yes",
            name="Alpha 5",
            start_date="2028-06-01",
            follow=True,
        )
        messages_ = list(response.context["messages"])
        self.assertTrue(any(m.level_tag == "warning" for m in messages_))

    def test_dropped_registration_window_is_reported(self):
        now = timezone.now()
        Event.objects.filter(pk=self.a.pk).update(
            registration_opens_at=now - timezone.timedelta(days=1),
            registration_closes_at=now + timezone.timedelta(days=30),
        )

        response = self._post(
            [self.a.pk],
            apply="yes",
            name="Alpha 4",
            start_date="2027-06-01",
            follow=True,
        )
        new = Event.objects.get(name="Alpha 4")
        self.assertIsNone(new.registration_opens_at)
        self.assertContains(response, "registration")
        self.assertContains(response, "Alpha 4")

    def test_user_with_only_add_event_is_refused(self):
        from django.contrib.auth.models import Permission

        staff = AdminUser.objects.create_user("limited", password="pw12345")
        staff.is_staff = True
        staff.save()
        staff.user_permissions.set(
            Permission.objects.filter(
                codename__in=["add_event", "change_event", "view_event"]
            )
        )
        self.client.force_login(staff)

        self._post([self.a.pk], apply="yes", name="Sneaky", start_date="2028-06-01")

        self.assertFalse(Event.objects.filter(name="Sneaky").exists())
