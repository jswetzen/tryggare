"""Extra.ticket_types: an extra offered only to holders of the listed ticket
types, enforced on submit (views._attach_extra and the required-extra checks)
and projected into the form spec."""

from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import AppliesTo, Event, Extra, TicketType

from .form_spec import build_form_spec
from .models import Registration, RegistrationExtra


def _event(name):
    today = timezone.now().date()
    return Event.objects.create(
        name=name,
        start_date=today,
        end_date=today,
        registration_opens_at=timezone.now() - timezone.timedelta(days=1),
    )


class ExtraGatingTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.event = _event("Gated 2027")
        make = lambda name, applies_to: TicketType.objects.create(  # noqa: E731
            event=self.event, name=name, price=100, applies_to=applies_to
        )
        self.adult = make("Adult", AppliesTo.PARENT)
        self.teen = make("Child 13-17", AppliesTo.CHILD)
        self.kid = make("Child 0-12", AppliesTo.CHILD)
        self.workshop = Extra.objects.create(
            event=self.event, name="Workshop", price=50, applies_to=AppliesTo.CHILD
        )
        self.workshop.ticket_types.add(self.teen)

    def post(self, children, extras=(), parent_extras=()):
        # A fresh address each time: a second pending registration is refused.
        self.sent = getattr(self, "sent", 0) + 1
        payload = {
            "event": str(self.event.id),
            "contact_email": f"guardian{self.sent}@example.com",
            "parents": [
                {
                    "first_name": "Anna",
                    "phone": "070-123 45 67",
                    "relationship_type": "Mother",
                    "ticket_type": str(self.adult.id),
                    "extras": [{"extra": str(e.id)} for e in parent_extras],
                }
            ],
            "children": [
                {
                    "first_name": f"Child{i}",
                    "last_name": "Andersson",
                    "birthdate": "2012-01-01",
                    "ticket_type": str(ticket_type.id),
                    "extras": [{"extra": str(e.id)} for e in child_extras],
                }
                for i, (ticket_type, child_extras) in enumerate(children)
            ],
            "extras": [{"extra": str(e.id)} for e in extras],
        }
        with patch("registrations.views.send_verification_email", return_value=True):
            return self.client.post("/api/registrations/", payload, format="json")

    def test_holder_of_the_listed_type_may_take_it(self):
        response = self.post([(self.teen, [self.workshop])])
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(RegistrationExtra.objects.get().extra, self.workshop)

    def test_holder_of_another_type_is_refused(self):
        response = self.post([(self.kid, [self.workshop])])
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("Child 13-17", str(response.data))
        self.assertFalse(Registration.objects.exists())

    def test_gate_is_judged_per_attendee_not_per_booking(self):
        response = self.post([(self.teen, []), (self.kid, [self.workshop])])
        self.assertEqual(response.status_code, 400, response.data)

    def test_any_listed_type_opens_it(self):
        self.workshop.ticket_types.add(self.kid)
        response = self.post([(self.kid, [self.workshop])])
        self.assertEqual(response.status_code, 201, response.data)

    def test_empty_gate_is_open_to_everyone(self):
        ungated = Extra.objects.create(
            event=self.event, name="Lunch", price=10, applies_to=AppliesTo.CHILD
        )
        response = self.post([(self.kid, [ungated])])
        self.assertEqual(response.status_code, 201, response.data)

    def test_bundle_holder_counts_as_holding_the_type(self):
        bundle = TicketType.objects.create(
            event=self.event,
            name="Day pass",
            price=10,
            applies_to=AppliesTo.CHILD,
            kind=TicketType.Kind.SESSION_BUNDLE,
        )
        bundle.sessions.add(
            self.event.sessions.create(
                name="Day",
                start_time=timezone.now(),
                end_time=timezone.now() + timezone.timedelta(hours=1),
            )
        )
        self.workshop.ticket_types.set([bundle])
        response = self.post([(bundle, [self.workshop])])
        self.assertEqual(response.status_code, 201, response.data)

    def test_gate_on_a_ticket_type_of_another_event_is_never_open(self):
        other = _event("Other 2027")
        foreign = TicketType.objects.create(
            event=other, name="Foreign pass", price=1, applies_to=AppliesTo.CHILD
        )
        self.workshop.ticket_types.set([foreign])
        for ticket_type in (self.teen, self.kid):
            response = self.post([(ticket_type, [self.workshop])])
            self.assertEqual(response.status_code, 400, response.data)

    def test_registration_level_extra_needs_any_holder_in_the_booking(self):
        cabin = Extra.objects.create(
            event=self.event, name="Cabin", price=500, per_attendee=False
        )
        cabin.ticket_types.add(self.teen)
        refused = self.post([(self.kid, [])], extras=[cabin])
        self.assertEqual(refused.status_code, 400, refused.data)
        accepted = self.post([(self.kid, []), (self.teen, [])], extras=[cabin])
        self.assertEqual(accepted.status_code, 201, accepted.data)

    def test_required_gated_extra_is_only_required_of_holders(self):
        self.workshop.required = True
        self.workshop.save()
        # A 0-12 child is not asked for it; a 13-17 child must take it.
        self.assertEqual(self.post([(self.kid, [])]).status_code, 201)
        refused = self.post([(self.teen, [])])
        self.assertEqual(refused.status_code, 400, refused.data)
        self.assertEqual(self.post([(self.teen, [self.workshop])]).status_code, 201)

    def test_required_gated_registration_extra_waits_for_a_holder(self):
        cabin = Extra.objects.create(
            event=self.event,
            name="Cabin",
            per_attendee=False,
            required=True,
        )
        cabin.ticket_types.add(self.teen)
        self.assertEqual(self.post([(self.kid, [])]).status_code, 201)
        self.assertEqual(self.post([(self.teen, [])]).status_code, 400)
        self.assertEqual(self.post([(self.teen, [])], extras=[cabin]).status_code, 201)


class ExtraGateFormSpecTests(TestCase):
    def test_form_spec_lists_the_gate(self):
        event = _event("Spec 2027")
        teen = TicketType.objects.create(
            event=event, name="Teen", price=1, sort_order=1
        )
        secret = TicketType.objects.create(
            event=event, name="Secret", price=1, is_hidden=True, sort_order=2
        )
        gated = Extra.objects.create(event=event, name="Workshop", sort_order=1)
        gated.ticket_types.set([teen, secret])
        Extra.objects.create(event=event, name="Lunch", sort_order=2)

        extras = {e["name"]: e for e in build_form_spec(event)["extras"]}
        self.assertEqual(
            sorted(extras["Workshop"]["ticket_type_ids"]),
            sorted([str(teen.id), str(secret.id)]),
        )
        # A hidden type's name is not published.
        self.assertEqual(extras["Workshop"]["ticket_type_names"], ["Teen"])
        self.assertEqual(extras["Lunch"]["ticket_type_ids"], [])
