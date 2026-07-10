"""
GET /api/registrations/events/<event_id>/ — the public event-info lookup
that feeds the /register/[eventId] form (ticket types, extras, and the
registration window).
"""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import AppliesTo, Event, Extra, ExtraChoice, TicketType


def _make_event(name="Summer Camp"):
    today = timezone.now().date()
    return Event.objects.create(
        name=name,
        start_date=today,
        end_date=today,
        registration_opens_at=timezone.now() - timezone.timedelta(days=1),
    )


class RegistrationEventInfoTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_no_hidden_ticket_types_reports_false(self):
        event = _make_event()
        TicketType.objects.create(
            event=event, name="Adult", price=100, applies_to=AppliesTo.PARENT
        )

        response = self.client.get(f"/api/registrations/events/{event.id}/")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data["has_hidden_ticket_types"])
        self.assertEqual(len(response.data["ticket_types"]), 1)

    def test_hidden_only_event_reports_true_with_empty_ticket_types(self):
        """The exact invite-only configuration the promo-unlock feature is
        for: every active TicketType is hidden, so ticket_types is empty
        but the frontend still needs a signal to show the promo-code box."""
        event = _make_event()
        TicketType.objects.create(
            event=event,
            name="VIP",
            price=100,
            applies_to=AppliesTo.PARENT,
            is_hidden=True,
        )

        response = self.client.get(f"/api/registrations/events/{event.id}/")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["ticket_types"], [])
        self.assertTrue(response.data["has_hidden_ticket_types"])

    def test_extras_choices_are_returned_and_filtered_to_active(self):
        event = _make_event()
        shirt = Extra.objects.create(
            event=event, name="Shirt", price=Decimal("100.00"), requires_choice=True
        )
        ExtraChoice.objects.create(extra=shirt, label="M")
        inactive = ExtraChoice.objects.create(extra=shirt, label="L", is_active=False)

        response = self.client.get(f"/api/registrations/events/{event.id}/")

        self.assertEqual(response.status_code, 200, response.data)
        extras = response.data["extras"]
        self.assertEqual(len(extras), 1)
        choice_labels = {c["label"] for c in extras[0]["choices"]}
        self.assertEqual(choice_labels, {"M"})
        self.assertNotIn(str(inactive.id), {c["id"] for c in extras[0]["choices"]})

    def test_query_count_does_not_scale_with_number_of_extras(self):
        event = _make_event()
        for i in range(5):
            extra = Extra.objects.create(
                event=event, name=f"Extra {i}", price=Decimal("10.00")
            )
            ExtraChoice.objects.create(extra=extra, label="Only choice")

        # event, active ticket types, has_hidden_ticket_types exists(),
        # extras, and one prefetch query for all their choice_rows —
        # constant regardless of how many extras/choices exist.
        with self.assertNumQueries(5):
            response = self.client.get(f"/api/registrations/events/{event.id}/")

        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data["extras"]), 5)
