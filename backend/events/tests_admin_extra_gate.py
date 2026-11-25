"""ExtraAdmin's ticket-type picker is limited to the extra's own event."""

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AdminUser
from tests.support import NonManifestStaticfilesTestCase

from .admin import ExtraAdminForm, PromoCodeAdminForm, TicketTypeAdminForm
from .models import Event, Extra, PromoCode, Session, TicketType


def _event(name):
    today = timezone.now().date()
    return Event.objects.create(name=name, start_date=today, end_date=today)


class ExtraAdminGateTests(NonManifestStaticfilesTestCase, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = AdminUser.objects.create_superuser("gateadmin", "pw12345")
        cls.event = _event("Mine")
        cls.other = _event("Other")
        cls.mine = TicketType.objects.create(event=cls.event, name="Mine pass", price=1)
        cls.foreign = TicketType.objects.create(
            event=cls.other, name="Foreign pass", price=1
        )
        cls.extra = Extra.objects.create(event=cls.event, name="Workshop")

    def setUp(self):
        self.client.force_login(self.user)

    def data(self, **overrides):
        data = {
            "event": self.event.pk,
            "name": "Workshop",
            "price": "0",
            "applies_to": "either",
            "sort_order": 0,
        }
        data.update(overrides)
        return data

    def test_change_form_offers_only_the_extras_event(self):
        response = self.client.get(
            reverse("admin:events_extra_change", args=[self.extra.pk])
        )
        queryset = response.context["adminform"].form.fields["ticket_types"].queryset
        self.assertEqual(list(queryset), [self.mine])

    def test_form_refuses_a_ticket_type_of_another_event(self):
        form = ExtraAdminForm(
            data=self.data(ticket_types=[self.foreign.pk]), instance=self.extra
        )
        self.assertFalse(form.is_valid())
        # Either the narrowed picker or clean() refuses it; never saved.
        self.assertIn("ticket_types", form.errors)

    def test_clean_refuses_when_the_picker_could_not_be_narrowed(self):
        # clean() is the real guard when a picker could not be narrowed.
        form = ExtraAdminForm(data=self.data(ticket_types=[self.foreign.pk]))
        form.fields["ticket_types"].queryset = TicketType.objects.all()
        self.assertFalse(form.is_valid())
        self.assertIn("Foreign pass", str(form.errors["ticket_types"]))

    def test_form_accepts_the_events_own_types(self):
        form = ExtraAdminForm(
            data=self.data(ticket_types=[self.mine.pk]), instance=self.extra
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_posted_event_does_not_narrow_an_unlocked_add_form(self):
        # The add form's event comes from ?event=, never from the body.
        form = ExtraAdminForm(data=self.data(event=self.other.pk))
        self.assertEqual(list(form.fields["ticket_types"].queryset), [])

    def test_malformed_posted_event_does_not_crash(self):
        form = ExtraAdminForm(data=self.data(event="not-a-uuid"))
        self.assertFalse(form.is_valid())
        self.assertIn("event", form.errors)
        form = ExtraAdminForm(data=self.data(event="not-a-uuid"), instance=self.extra)
        self.assertEqual(list(form.fields["ticket_types"].queryset), [self.mine])

    def test_unknown_event_falls_back_to_the_instance(self):
        form = ExtraAdminForm(
            data=self.data(event="00000000-0000-0000-0000-000000000000"),
            instance=self.extra,
        )
        self.assertEqual(list(form.fields["ticket_types"].queryset), [self.mine])

    def test_duplicate_action_warns_about_an_unmatched_gate(self):
        self.extra.ticket_types.add(self.mine)
        response = self.client.post(
            reverse("admin:events_extra_changelist"),
            {
                "action": "duplicate_to_event",
                "apply": "1",
                "target_event": self.other.pk,
                "_selected_action": [self.extra.pk],
            },
            follow=True,
        )
        texts = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("Workshop" in m and "inactive" in m for m in texts), texts)
        self.assertFalse(self.other.extras.get(name="Workshop").is_active)
        self.assertTrue(any("Re-pick" in m for m in texts), texts)

    def test_deleting_the_only_gate_type_deactivates_the_extra(self):
        second = TicketType.objects.create(event=self.event, name="Second", price=1)
        sole = Extra.objects.create(event=self.event, name="Sole")
        sole.ticket_types.add(self.mine)
        shared = Extra.objects.create(event=self.event, name="Shared")
        shared.ticket_types.add(self.mine, second)
        response = self.client.post(
            reverse("admin:events_tickettype_delete", args=[self.mine.pk]),
            {"post": "yes"},
            follow=True,
        )
        texts = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("Sole" in m and "Shared" not in m for m in texts), texts)
        sole.refresh_from_db()
        shared.refresh_from_db()
        self.assertFalse(sole.is_active)
        self.assertTrue(shared.is_active)

    def test_bulk_delete_of_every_gate_type_deactivates_the_extra(self):
        second = TicketType.objects.create(event=self.event, name="Second", price=1)
        shared = Extra.objects.create(event=self.event, name="Shared")
        shared.ticket_types.add(self.mine, second)
        response = self.client.post(
            reverse("admin:events_tickettype_changelist"),
            {
                "action": "delete_selected",
                "post": "yes",
                "_selected_action": [self.mine.pk, second.pk],
            },
            follow=True,
        )
        shared.refresh_from_db()
        self.assertFalse(shared.is_active)
        self.assertFalse(shared.ticket_types.exists())
        texts = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("Shared" in m for m in texts), texts)


class EventScopedAdminTests(NonManifestStaticfilesTestCase, TestCase):
    """Extra.session, TicketType.sessions/requires_ticket_type and PromoCode's
    two ticket-type pickers stay inside their own event."""

    @classmethod
    def setUpTestData(cls):
        cls.user = AdminUser.objects.create_superuser("scopeadmin", "pw12345")
        cls.event = _event("Mine")
        cls.other = _event("Other")
        cls.mine_s = Session.objects.create(
            event=cls.event,
            name="Mine session",
            start_time=timezone.now(),
            end_time=timezone.now(),
        )
        cls.foreign_s = Session.objects.create(
            event=cls.other,
            name="Foreign session",
            start_time=timezone.now(),
            end_time=timezone.now(),
        )
        cls.mine_t = TicketType.objects.create(
            event=cls.event, name="Mine pass", price=1
        )
        cls.foreign_t = TicketType.objects.create(
            event=cls.other, name="Foreign pass", price=1
        )
        cls.extra = Extra.objects.create(event=cls.event, name="Dinner")
        cls.promo = PromoCode.objects.create(
            event=cls.event, code="X", discount_type="percent", discount_value=10
        )

    def setUp(self):
        self.client.force_login(self.user)

    def form_for(self, name, obj):
        response = self.client.get(
            reverse(f"admin:events_{name}_change", args=[obj.pk])
        )
        return response.context["adminform"].form

    def test_extra_model_refuses_another_events_session(self):
        extra = Extra(event=self.event, name="E", session=self.foreign_s)
        with self.assertRaises(ValidationError) as ctx:
            extra.full_clean(exclude=["cloned_from"])
        self.assertIn("session", ctx.exception.error_dict)
        extra.session = self.mine_s
        extra.full_clean(exclude=["cloned_from"])

    def test_extra_change_form_lists_only_its_events_sessions(self):
        form = self.form_for("extra", self.extra)
        self.assertEqual(list(form.fields["session"].queryset), [self.mine_s])

    def test_extra_form_refuses_a_foreign_session(self):
        form = ExtraAdminForm(
            data={
                "event": self.event.pk,
                "name": "Dinner",
                "price": "0",
                "applies_to": "either",
                "sort_order": 0,
                "session": self.foreign_s.pk,
            },
            instance=self.extra,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("session", form.errors)

    def test_ticket_type_model_refuses_another_events_requirement(self):
        tt = TicketType(
            event=self.event,
            name="T",
            price=1,
            requires_ticket_type=self.foreign_t,
        )
        with self.assertRaises(ValidationError) as ctx:
            tt.full_clean(exclude=["event", "cloned_from"])
        self.assertIn("requires_ticket_type", ctx.exception.error_dict)

    def test_ticket_type_change_form_is_narrowed(self):
        sibling = TicketType.objects.create(event=self.event, name="Sibling", price=1)
        form = self.form_for("tickettype", self.mine_t)
        self.assertEqual(list(form.fields["sessions"].queryset), [self.mine_s])
        # Its own event's other types only: not the row itself, not a foreign one.
        self.assertEqual(list(form.fields["requires_ticket_type"].queryset), [sibling])

    def test_ticket_type_form_refuses_foreign_session_and_requirement(self):
        data = {
            "event": self.event.pk,
            "name": "Mine pass",
            "price": "1",
            "applies_to": "either",
            "kind": TicketType.Kind.SESSION_BUNDLE,
            "sort_order": 0,
            "sessions": [self.foreign_s.pk],
            "requires_ticket_type": self.foreign_t.pk,
        }
        form = TicketTypeAdminForm(data=data, instance=self.mine_t)
        self.assertFalse(form.is_valid())
        self.assertIn("sessions", form.errors)
        self.assertIn("requires_ticket_type", form.errors)

    def test_promo_change_form_is_narrowed(self):
        form = self.form_for("promocode", self.promo)
        for name in ("applies_to_ticket_types", "unlocks_ticket_types"):
            self.assertEqual(list(form.fields[name].queryset), [self.mine_t])

    def test_promo_form_refuses_foreign_ticket_types(self):
        # Simulate a picker that could not be narrowed: clean() still refuses.
        form = PromoCodeAdminForm(
            data={
                "event": self.event.pk,
                "code": "X",
                "discount_type": "percent",
                "discount_value": "10",
                "is_active": "on",
                "applies_to_ticket_types": [self.foreign_t.pk],
            },
            instance=self.promo,
        )
        for name in ("applies_to_ticket_types", "unlocks_ticket_types"):
            form.fields[name].queryset = TicketType.objects.all()
        self.assertFalse(form.is_valid())
        self.assertIn("Foreign pass", str(form.errors["applies_to_ticket_types"]))

    ADD_URLS = ("extra", "tickettype", "promocode")

    def test_add_without_event_shows_the_chooser(self):
        for name in self.ADD_URLS:
            with self.subTest(name):
                response = self.client.get(reverse(f"admin:events_{name}_add"))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'data-testid="event-chooser"')
                self.assertContains(response, self.event.name)

    def test_chooser_with_a_bad_event_is_shown_again(self):
        response = self.client.get(
            reverse("admin:events_extra_add"), {"event": "not-a-uuid"}
        )
        self.assertContains(response, 'data-testid="event-chooser"')

    def test_chooser_carries_other_query_params(self):
        response = self.client.get(reverse("admin:events_extra_add"), {"_popup": "1"})
        self.assertContains(response, 'name="_popup" value="1"')

    def test_add_with_event_is_narrowed_and_preselected(self):
        for name, fields in (
            ("extra", ["session", "ticket_types"]),
            ("tickettype", ["sessions"]),
            ("promocode", ["applies_to_ticket_types", "unlocks_ticket_types"]),
        ):
            response = self.client.get(
                reverse(f"admin:events_{name}_add"), {"event": self.event.pk}
            )
            form = response.context["adminform"].form
            self.assertEqual(form.initial["event"], self.event.pk)
            for field in fields:
                with self.subTest(name=name, field=field):
                    ids = {o.event_id for o in form.fields[field].queryset}
                    self.assertEqual(ids, {self.event.pk})

    def test_add_takes_the_event_from_the_changelist_filter(self):
        url = reverse("admin:events_extra_add")
        response = self.client.get(
            url, {"_changelist_filters": f"event__id__exact={self.other.pk}"}
        )
        self.assertNotContains(response, 'data-testid="event-chooser"')
        form = response.context["adminform"].form
        self.assertEqual(list(form.fields["session"].queryset), [self.foreign_s])

    def test_failed_add_submit_keeps_the_posted_events_pickers(self):
        response = self.client.post(
            reverse("admin:events_extra_add") + f"?event={self.event.pk}",
            {"name": "", "price": "0", "applies_to": "either"},
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["adminform"].form
        self.assertTrue(form.errors)
        self.assertEqual(list(form.fields["session"].queryset), [self.mine_s])

    def test_session_bundle_ticket_type_is_created_in_one_submit(self):
        response = self.client.post(
            reverse("admin:events_tickettype_add") + f"?event={self.event.pk}",
            {
                "name": "Day pass",
                "price": "10",
                "applies_to": "either",
                "kind": TicketType.Kind.SESSION_BUNDLE,
                "sort_order": 0,
                "is_active": "on",
                "sessions": [self.mine_s.pk],
            },
        )
        self.assertEqual(
            response.status_code,
            302,
            response.context["adminform"].form.errors if response.context else None,
        )
        made = TicketType.objects.get(name="Day pass")
        self.assertEqual(list(made.sessions.all()), [self.mine_s])

    def test_event_is_read_only_on_change_forms(self):
        for name, obj in (
            ("extra", self.extra),
            ("tickettype", self.mine_t),
            ("promocode", self.promo),
            ("session", self.mine_s),
        ):
            with self.subTest(name):
                form = self.form_for(name, obj)
                self.assertNotIn("event", form.fields)

    def test_moving_a_row_to_another_event_is_ignored(self):
        response = self.client.post(
            reverse("admin:events_extra_change", args=[self.extra.pk]),
            {
                "event": self.other.pk,
                "name": "Dinner",
                "price": "0",
                "applies_to": "either",
                "sort_order": 0,
                "choice_rows-TOTAL_FORMS": 0,
                "choice_rows-INITIAL_FORMS": 0,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.extra.refresh_from_db()
        self.assertEqual(self.extra.event_id, self.event.pk)

    def test_resaving_a_legacy_foreign_link_names_it(self):
        self.extra.session = self.foreign_s
        self.extra.save()
        self.extra.ticket_types.add(self.foreign_t)
        response = self.client.post(
            reverse("admin:events_extra_change", args=[self.extra.pk]),
            {
                "name": "Dinner",
                "price": "0",
                "applies_to": "either",
                "sort_order": 0,
                "session": self.foreign_s.pk,
                "ticket_types": [self.foreign_t.pk],
                "choice_rows-TOTAL_FORMS": 0,
                "choice_rows-INITIAL_FORMS": 0,
            },
        )
        # Still listed, so the refusal names the type, not "invalid choice".
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Foreign pass")
        self.assertContains(response, "Must belong to the same event")
        self.assertContains(response, "The session must belong to the extra")

    def test_add_without_permission_is_denied_before_the_chooser(self):
        nobody = AdminUser.objects.create_user("nobody", "pw12345", is_staff=True)
        self.client.force_login(nobody)
        for name in self.ADD_URLS:
            with self.subTest(name):
                response = self.client.get(reverse(f"admin:events_{name}_add"))
                self.assertEqual(response.status_code, 403)
                self.assertNotContains(response, self.event.name, status_code=403)

    def test_add_form_shows_the_locked_event_with_a_way_back(self):
        response = self.client.get(
            reverse("admin:events_extra_add"), {"event": self.event.pk}
        )
        form = response.context["adminform"].form
        self.assertNotIn("event", form.fields)
        self.assertContains(response, self.event.name)
        self.assertContains(response, f'href="{reverse("admin:events_extra_add")}"')

    def test_posted_event_cannot_override_the_locked_one(self):
        response = self.client.post(
            reverse("admin:events_extra_add") + f"?event={self.event.pk}",
            {
                "event": self.other.pk,
                "name": "Lunch",
                "price": "0",
                "applies_to": "either",
                "sort_order": 0,
                "choice_rows-TOTAL_FORMS": 0,
                "choice_rows-INITIAL_FORMS": 0,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Extra.objects.get(name="Lunch").event_id, self.event.pk)

    def test_save_and_add_another_keeps_the_event(self):
        response = self.client.post(
            reverse("admin:events_extra_add") + f"?event={self.event.pk}",
            {
                "_addanother": "1",
                "name": "Snack",
                "price": "0",
                "applies_to": "either",
                "sort_order": 0,
                "choice_rows-TOTAL_FORMS": 0,
                "choice_rows-INITIAL_FORMS": 0,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(f"event={self.event.pk}", response.url)

    def test_chooser_in_a_popup_drops_the_admin_chrome(self):
        response = self.client.get(reverse("admin:events_extra_add"), {"_popup": "1"})
        self.assertTrue(response.context["is_popup"])
        self.assertNotContains(response, 'id="header"')

    def test_chooser_escapes_injected_params(self):
        response = self.client.get(
            reverse("admin:events_extra_add"), {"_popup": '"><script>alert(1)</script>'}
        )
        self.assertNotContains(response, "<script>alert(1)")
        self.assertContains(response, "&lt;script&gt;alert(1)")

    def test_plus_popup_links_carry_the_event(self):
        response = self.client.get(
            reverse("admin:events_extra_add"), {"event": self.event.pk}
        )
        self.assertContains(response, f"_popup=1&amp;event={self.event.pk}")
        change = self.client.get(
            reverse("admin:events_extra_change", args=[self.extra.pk])
        )
        self.assertContains(change, f"_popup=1&amp;event={self.event.pk}")

    def test_session_popup_preselects_the_event(self):
        response = self.client.get(
            reverse("admin:events_session_add"),
            {"_popup": "1", "event": self.event.pk},
        )
        form = response.context["adminform"].form
        self.assertEqual(str(form.initial["event"]), str(self.event.pk))

    def test_popup_flow_end_to_end(self):
        url = reverse("admin:events_tickettype_add")
        chooser = self.client.get(url, {"_popup": "1", "_to_field": "id"})
        self.assertContains(chooser, 'name="_popup" value="1"')
        form = self.client.get(
            url, {"_popup": "1", "_to_field": "id", "event": self.event.pk}
        )
        self.assertNotContains(form, 'data-testid="event-chooser"')
        saved = self.client.post(
            f"{url}?_popup=1&_to_field=id&event={self.event.pk}",
            {
                "_popup": "1",
                "_to_field": "id",
                "name": "Popup pass",
                "price": "5",
                "applies_to": "either",
                "kind": TicketType.Kind.EVENT,
                "sort_order": 0,
                "is_active": "on",
            },
        )
        self.assertEqual(saved.status_code, 200)
        made = TicketType.objects.get(name="Popup pass")
        self.assertEqual(made.event_id, self.event.pk)
        self.assertContains(saved, "popup-response")
        self.assertContains(saved, str(made.pk))

    def test_a_legacy_self_requirement_still_gets_its_message(self):
        TicketType.objects.filter(pk=self.mine_t.pk).update(
            requires_ticket_type=self.mine_t
        )
        form = self.form_for("tickettype", self.mine_t)
        self.assertIn(self.mine_t, form.fields["requires_ticket_type"].queryset)
        with self.assertRaises(ValidationError) as ctx:
            TicketType.objects.get(pk=self.mine_t.pk).full_clean()
        self.assertIn("cannot require itself", str(ctx.exception))
