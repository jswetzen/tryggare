"""ExtraAdmin's ticket-type picker is limited to the extra's own event."""

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import AdminUser
from tests.support import NonManifestStaticfilesTestCase

from .admin import ExtraAdminForm
from .models import Event, Extra, TicketType


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
        # An add form with no event yet shows every type; clean() is the real guard.
        form = ExtraAdminForm(data=self.data(ticket_types=[self.foreign.pk]))
        form.fields["ticket_types"].queryset = TicketType.objects.all()
        self.assertFalse(form.is_valid())
        self.assertIn("Foreign pass", str(form.errors["ticket_types"]))

    def test_form_accepts_the_events_own_types(self):
        form = ExtraAdminForm(
            data=self.data(ticket_types=[self.mine.pk]), instance=self.extra
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_posted_event_narrows_the_picker_of_an_add_form(self):
        form = ExtraAdminForm(data=self.data(event=self.other.pk))
        self.assertEqual(list(form.fields["ticket_types"].queryset), [self.foreign])

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
