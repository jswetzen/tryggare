"""views._attach_extra called directly: each refusal it can raise, and what it
stores. The submit endpoint's own serializer stops several of these first, so
the API tests never reach them."""

from unittest.mock import patch

from django.core.cache import cache

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from events.models import AppliesTo, Event, Extra, ExtraChoice, TicketType

from .models import Registration, RegistrationExtra
from .views import _attach_extra


class AttachExtraTests(TestCase):
    def setUp(self):
        cache.clear()
        today = timezone.now().date()
        self.event = Event.objects.create(
            name="Attach 2027",
            start_date=today,
            end_date=today,
            registration_opens_at=timezone.now() - timezone.timedelta(days=1),
        )
        adult = TicketType.objects.create(
            event=self.event, name="Adult", price=100, applies_to=AppliesTo.PARENT
        )
        child = TicketType.objects.create(
            event=self.event, name="Child", price=50, applies_to=AppliesTo.CHILD
        )
        payload = {
            "event": str(self.event.id),
            "contact_email": "guardian@example.com",
            "parents": [
                {
                    "first_name": "Anna",
                    "phone": "070-123 45 67",
                    "relationship_type": "Mother",
                    "ticket_type": str(adult.id),
                }
            ],
            "children": [
                {
                    "first_name": "Child",
                    "last_name": "Andersson",
                    "birthdate": "2012-01-01",
                    "ticket_type": str(child.id),
                }
            ],
        }
        with patch("registrations.views.send_verification_email", return_value=True):
            response = APIClient().post("/api/registrations/", payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.registration = Registration.objects.get()
        self.parent = self.registration.family.parents.get()
        self.child = self.registration.family.children.get()

    def extra(self, **fields):
        fields.setdefault("event", self.event)
        fields.setdefault("name", "Extra")
        fields.setdefault("price", 10)
        return Extra.objects.create(**fields)

    def attach(self, extra, attendee=None, is_child=False, **selection):
        _attach_extra(
            registration=self.registration,
            attendee=attendee,
            selection={"extra": extra, **selection},
            is_child=is_child,
        )

    def assertRefused(self, message, extra, **kwargs):
        with self.assertRaisesMessage(ValidationError, message):
            self.attach(extra, **kwargs)

    def test_extra_of_another_event(self):
        other = Event.objects.create(
            name="Other", start_date=self.event.start_date, end_date=self.event.end_date
        )
        self.assertRefused(
            "Invalid extra for this event.",
            self.extra(event=other),
            attendee=self.child,
            is_child=True,
        )

    def test_inactive_extra(self):
        self.assertRefused(
            "Invalid extra for this event.",
            self.extra(is_active=False),
            attendee=self.child,
            is_child=True,
        )

    def test_choice_of_another_extra(self):
        choice = ExtraChoice.objects.create(extra=self.extra(name="Other"), label="L")
        self.assertRefused(
            "Invalid choice for this extra.",
            self.extra(),
            attendee=self.child,
            is_child=True,
            choice=choice,
        )

    def test_missing_required_choice(self):
        self.assertRefused(
            "This extra requires a choice.",
            self.extra(requires_choice=True),
            attendee=self.child,
            is_child=True,
        )

    def test_per_attendee_extra_without_attendee(self):
        self.assertRefused("This extra must be attached to an attendee.", self.extra())

    def test_per_registration_extra_with_attendee(self):
        self.assertRefused(
            "This extra can't be attached to a specific attendee.",
            self.extra(per_attendee=False),
            attendee=self.child,
            is_child=True,
        )

    def test_quantity_on_per_attendee_extra(self):
        self.assertRefused(
            "A quantity greater than one is only allowed",
            self.extra(),
            attendee=self.child,
            is_child=True,
            quantity=2,
        )

    def test_extra_for_the_other_kind_of_attendee(self):
        self.assertRefused(
            "This extra isn't available for this attendee.",
            self.extra(applies_to=AppliesTo.PARENT),
            attendee=self.child,
            is_child=True,
        )
        self.assertRefused(
            "This extra isn't available for this attendee.",
            self.extra(applies_to=AppliesTo.CHILD),
            attendee=self.parent,
        )

    def test_session_extra_needs_an_attendee(self):
        # per_attendee=False so the earlier attendee checks let it through.
        session = self.event.sessions.create(
            name="Sat",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1),
        )
        self.assertRefused(
            "A session-scoped extra must be attached to an attendee.",
            self.extra(session=session, per_attendee=False),
        )

    def test_session_extra_for_an_attendee_without_the_session(self):
        session = self.event.sessions.create(
            name="Sat",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1),
        )
        # An event ticket covers every session, so drop the parent's.
        self.registration.event_tickets.filter(attendee=self.parent).delete()
        self.assertRefused(
            "This attendee isn't registered for that session.",
            self.extra(session=session),
            attendee=self.parent,
        )

    def test_gate_with_no_visible_type_names_none(self):
        hidden = TicketType.objects.create(
            event=self.event, name="Secret", price=1, is_hidden=True
        )
        extra = self.extra()
        extra.ticket_types.add(hidden)
        with self.assertRaises(ValidationError) as caught:
            self.attach(extra, attendee=self.child, is_child=True)
        self.assertEqual(
            caught.exception.detail, ["This extra requires a different ticket."]
        )

    def test_second_per_attendee_selection(self):
        extra = self.extra()
        self.attach(extra, attendee=self.child, is_child=True)
        self.assertRefused(
            "This extra is already attached to this attendee.",
            extra,
            attendee=self.child,
            is_child=True,
        )

    def test_price_includes_the_choice_delta(self):
        extra = self.extra(requires_choice=True)
        choice = ExtraChoice.objects.create(extra=extra, label="Big", price_delta=5)
        self.attach(extra, attendee=self.child, is_child=True, choice=choice)
        row = RegistrationExtra.objects.get()
        self.assertEqual(row.price_at_registration, 15)
        self.assertEqual(
            (row.attendee_id, row.choice, row.quantity), (self.child.pk, choice, 1)
        )

    def test_per_registration_extra_adds_up_per_choice(self):
        extra = self.extra(per_attendee=False, requires_choice=True)
        big = ExtraChoice.objects.create(extra=extra, label="Big")
        small = ExtraChoice.objects.create(extra=extra, label="Small")
        self.attach(extra, choice=big, quantity=2)
        self.attach(extra, choice=big, quantity=3)
        self.attach(extra, choice=small)
        rows = {
            r.choice.label: r.quantity
            for r in RegistrationExtra.objects.filter(attendee=None)
        }
        self.assertEqual(rows, {"Big": 5, "Small": 1})
