"""
Phase 3: itemized ticket types & extras.

Covers pricing.py::calculate_total directly (flat fallback, itemized sum,
session-bundle grouping, extras with quantity/choice), the submission-time
ticket-type/extras validation in views.py, and verify_registration's
paid-ness gate now reading calculate_total() instead of Event.is_paid.
"""

from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from django.utils import timezone

from events.models import (
    AppliesTo,
    Event,
    EventTicket,
    Extra,
    ExtraChoice,
    Session,
    SessionTicket,
    TicketType,
)
from families.models import Child, Family, Parent

from .models import Payment, Registration, RegistrationExtra
from .pricing import calculate_total
from .tokens import generate_verification_token, hash_token


def _make_event(name="Summer Camp", price=None, days=1):
    today = timezone.now().date()
    return Event.objects.create(
        name=name,
        start_date=today,
        end_date=today + timezone.timedelta(days=days - 1),
        price=price,
        registration_opens_at=timezone.now() - timezone.timedelta(days=1),
    )


def _make_registration(event, *, contact_email="guardian@example.com"):
    family = Family.objects.create(last_name="Test")
    return Registration.objects.create(
        event=event,
        family=family,
        contact_email=contact_email,
        verification_token_hash=hash_token(generate_verification_token()),
    )


class CalculateTotalTests(TestCase):
    def test_falls_back_to_flat_event_price_when_no_ticket_types_configured(self):
        event = _make_event(price=Decimal("500.00"))
        registration = _make_registration(event)
        family = registration.family
        for _ in range(3):
            Parent.objects.create(family=family, first_name="P", relationship_type="X")
        # Flat fallback ignores attendee count entirely — Phase 0-2 behavior.
        self.assertEqual(calculate_total(registration), Decimal("500.00"))

    def test_flat_fallback_zero_for_free_event(self):
        event = _make_event(price=None)
        registration = _make_registration(event)
        self.assertEqual(calculate_total(registration), Decimal("0"))

    def test_sums_event_ticket_snapshots(self):
        event = _make_event()
        ticket_type = TicketType.objects.create(event=event, name="Adult", price=1100)
        registration = _make_registration(event)
        family = registration.family
        parent = Parent.objects.create(
            family=family, first_name="Anna", relationship_type="Mother"
        )
        EventTicket.objects.create(
            attendee=parent,
            event=event,
            registration=registration,
            ticket_type=ticket_type,
            price_at_registration=Decimal("1100.00"),
        )
        self.assertEqual(calculate_total(registration), Decimal("1100.00"))

    def test_session_bundle_price_counted_once_not_per_session(self):
        event = _make_event(days=3)
        friday = Session.objects.create(
            event=event,
            name="Friday",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=8),
        )
        saturday = Session.objects.create(
            event=event,
            name="Saturday",
            start_time=timezone.now() + timezone.timedelta(days=1),
            end_time=timezone.now() + timezone.timedelta(days=1, hours=8),
        )
        bundle = TicketType.objects.create(
            event=event,
            name="Weekend",
            price=350,
            kind=TicketType.Kind.SESSION_BUNDLE,
        )
        bundle.sessions.set([friday, saturday])
        registration = _make_registration(event)
        child = Child.objects.create(family=registration.family, first_name="Kim")
        for session in (friday, saturday):
            SessionTicket.objects.create(
                attendee=child,
                session=session,
                registration=registration,
                ticket_type=bundle,
                price_at_registration=Decimal("350.00"),
            )
        # Two SessionTicket rows share one ticket_type — must be counted once.
        self.assertEqual(calculate_total(registration), Decimal("350.00"))


class MaterializeTicketEmptyBundleTests(TestCase):
    """A2: TicketTypeAdminForm.clean() (events/tests.py) is the staff-facing
    guard; this is the belt-and-suspenders runtime backstop in
    _materialize_ticket itself for any path that isn't the admin form."""

    def test_empty_sessions_bundle_is_rejected_not_silently_ticketless(self):
        from rest_framework.exceptions import ValidationError

        from .views import _materialize_ticket

        event = _make_event()
        bundle = TicketType.objects.create(
            event=event,
            name="Weekend",
            price=350,
            kind=TicketType.Kind.SESSION_BUNDLE,
        )
        registration = _make_registration(event)
        child = Child.objects.create(family=registration.family, first_name="Kim")

        with self.assertRaises(ValidationError):
            _materialize_ticket(
                attendee=child,
                event=event,
                ticket_type=bundle,
                registration=registration,
            )
        self.assertEqual(SessionTicket.objects.count(), 0)

    def test_extras_summed_with_quantity_and_choice_delta(self):
        event = _make_event()
        TicketType.objects.create(event=event, name="Adult", price=0)
        registration = _make_registration(event)
        cabin = Extra.objects.create(
            event=event, name="Cabin", price=200, per_attendee=False
        )
        shirt = Extra.objects.create(
            event=event, name="Shirt", price=100, requires_choice=True
        )
        xl = ExtraChoice.objects.create(extra=shirt, label="XL", price_delta=20)
        child = Child.objects.create(family=registration.family, first_name="Kim")

        RegistrationExtra.objects.create(
            registration=registration,
            extra=cabin,
            attendee=None,
            quantity=2,
            price_at_registration=Decimal("200.00"),
        )
        RegistrationExtra.objects.create(
            registration=registration,
            extra=shirt,
            attendee=child,
            choice=xl,
            price_at_registration=Decimal("120.00"),
        )

        # cabin: 200 * 2 = 400; shirt+XL: 120 * 1 = 120 -> 520 total.
        self.assertEqual(calculate_total(registration), Decimal("520.00"))


class AttachExtraChoiceDedupTests(TestCase):
    """A per-registration extra selected twice with different choices (e.g.
    "Large cabin" then "Small cabin") must materialize as two line items,
    not one row whose quantity silently bumps at the first choice's price —
    get_or_create's lookup must include `choice`, not just
    (registration, extra, attendee=None)."""

    def test_same_extra_different_choice_creates_separate_line_items(self):
        from .views import _attach_extra

        event = _make_event()
        TicketType.objects.create(event=event, name="Adult", price=0)
        registration = _make_registration(event)
        cabin = Extra.objects.create(
            event=event,
            name="Cabin",
            price=0,
            per_attendee=False,
            requires_choice=True,
        )
        large = ExtraChoice.objects.create(extra=cabin, label="Large", price_delta=300)
        small = ExtraChoice.objects.create(extra=cabin, label="Small", price_delta=150)

        _attach_extra(
            registration=registration,
            attendee=None,
            selection={"extra": cabin, "choice": large, "quantity": 1},
            is_child=None,
        )
        _attach_extra(
            registration=registration,
            attendee=None,
            selection={"extra": cabin, "choice": small, "quantity": 1},
            is_child=None,
        )

        rows = RegistrationExtra.objects.filter(registration=registration, extra=cabin)
        self.assertEqual(rows.count(), 2)
        large_row = rows.get(choice=large)
        small_row = rows.get(choice=small)
        self.assertEqual(large_row.quantity, 1)
        self.assertEqual(large_row.price_at_registration, Decimal("300.00"))
        self.assertEqual(small_row.quantity, 1)
        self.assertEqual(small_row.price_at_registration, Decimal("150.00"))
        self.assertEqual(calculate_total(registration), Decimal("450.00"))

    def test_same_extra_same_choice_still_bumps_quantity(self):
        from .views import _attach_extra

        event = _make_event()
        registration = _make_registration(event)
        cabin = Extra.objects.create(
            event=event, name="Cabin", price=100, per_attendee=False
        )

        _attach_extra(
            registration=registration,
            attendee=None,
            selection={"extra": cabin, "quantity": 1},
            is_child=None,
        )
        _attach_extra(
            registration=registration,
            attendee=None,
            selection={"extra": cabin, "quantity": 2},
            is_child=None,
        )

        row = RegistrationExtra.objects.get(registration=registration, extra=cabin)
        self.assertEqual(row.quantity, 3)


class SubmitWithTicketTypesTests(TestCase):
    def setUp(self):
        # Shared anon-throttle cache persists across test classes within a
        # run (see registrations/tests_throttling.py's setUp for the same
        # pattern) — clear it so this class's own request volume doesn't
        # depend on run order.
        cache.clear()
        self.client = APIClient()
        self.event = _make_event()
        self.adult_type = TicketType.objects.create(
            event=self.event, name="Adult", price=1100, applies_to=AppliesTo.PARENT
        )
        self.child_type = TicketType.objects.create(
            event=self.event,
            name="Child",
            price=400,
            applies_to=AppliesTo.CHILD,
            min_birthdate="2014-01-01",
            max_birthdate="2020-12-31",
        )
        self.url = "/api/registrations/"

    def _payload(self, **overrides):
        payload = {
            "event": str(self.event.id),
            "contact_email": "guardian@example.com",
            "parents": [
                {
                    "first_name": "Anna",
                    "relationship_type": "Mother",
                    "ticket_type": str(self.adult_type.id),
                }
            ],
            "children": [
                {
                    "first_name": "Kim",
                    "last_name": "Andersson",
                    "birthdate": "2018-01-01",
                    "ticket_type": str(self.child_type.id),
                }
            ],
        }
        payload.update(overrides)
        return payload

    def test_missing_ticket_type_is_rejected_when_event_is_itemized(self):
        payload = self._payload()
        payload["children"][0]["ticket_type"] = None

        with patch("registrations.views.send_verification_email", return_value=True):
            response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400, response.data)

    def test_ticket_type_outside_birthdate_window_is_rejected(self):
        payload = self._payload()
        payload["children"][0]["birthdate"] = "1990-01-01"  # too old for child_type

        with patch("registrations.views.send_verification_email", return_value=True):
            response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400, response.data)

    def test_valid_submission_snapshots_ticket_type_prices(self):
        with patch("registrations.views.send_verification_email", return_value=True):
            response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, 201, response.data)
        registration = Registration.objects.get()
        parent = registration.family.parents.get()
        child = registration.family.children.get()

        parent_ticket = EventTicket.objects.get(attendee=parent)
        child_ticket = EventTicket.objects.get(attendee=child)
        self.assertEqual(parent_ticket.ticket_type_id, self.adult_type.id)
        self.assertEqual(parent_ticket.price_at_registration, Decimal("1100.00"))
        self.assertEqual(child_ticket.ticket_type_id, self.child_type.id)
        self.assertEqual(child_ticket.price_at_registration, Decimal("400.00"))
        self.assertEqual(calculate_total(registration), Decimal("1500.00"))

    def test_session_scoped_extra_rejected_without_session_coverage(self):
        saturday = Session.objects.create(
            event=self.event,
            name="Saturday",
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=8),
        )
        sunday = Session.objects.create(
            event=self.event,
            name="Sunday",
            start_time=timezone.now() + timezone.timedelta(days=1),
            end_time=timezone.now() + timezone.timedelta(days=1, hours=8),
        )
        sunday_only = TicketType.objects.create(
            event=self.event,
            name="Sunday only",
            price=100,
            applies_to=AppliesTo.CHILD,
            kind=TicketType.Kind.SESSION_BUNDLE,
        )
        sunday_only.sessions.add(sunday)
        dinner = Extra.objects.create(
            event=self.event, name="Saturday dinner", session=saturday, price=50
        )

        payload = self._payload()
        payload["children"][0]["ticket_type"] = str(sunday_only.id)
        payload["children"][0]["extras"] = [{"extra": str(dinner.id)}]

        with patch("registrations.views.send_verification_email", return_value=True):
            response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400, response.data)


class RequiredExtraTests(TestCase):
    """Extra.required=True (case 3.2's must-choose-one pattern, e.g.
    accommodation) must be present in the submission for every applicable
    attendee — not just valid *if* submitted, which is all _attach_extra's
    per-selection checks cover on their own."""

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.event = _make_event()
        self.adult_type = TicketType.objects.create(
            event=self.event, name="Adult", price=0, applies_to=AppliesTo.PARENT
        )
        self.accommodation = Extra.objects.create(
            event=self.event,
            name="Boende",
            price=0,
            per_attendee=True,
            applies_to=AppliesTo.EITHER,
            requires_choice=True,
            required=True,
        )
        self.tent = ExtraChoice.objects.create(extra=self.accommodation, label="Tält")
        self.url = "/api/registrations/"

    def _payload(self, **overrides):
        payload = {
            "event": str(self.event.id),
            "contact_email": "guardian@example.com",
            "parents": [
                {
                    "first_name": "Anna",
                    "relationship_type": "Mother",
                    "ticket_type": str(self.adult_type.id),
                }
            ],
            "children": [],
        }
        payload.update(overrides)
        return payload

    def test_omitting_a_required_extra_entirely_is_rejected(self):
        with patch("registrations.views.send_verification_email", return_value=True):
            response = self.client.post(self.url, self._payload(), format="json")

        self.assertEqual(response.status_code, 400, response.data)

    def test_submitting_the_required_extra_with_a_choice_succeeds(self):
        payload = self._payload()
        payload["parents"][0]["extras"] = [
            {"extra": str(self.accommodation.id), "choice": str(self.tent.id)}
        ]

        with patch("registrations.views.send_verification_email", return_value=True):
            response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 201, response.data)
        registration = Registration.objects.get()
        reg_extra = RegistrationExtra.objects.get(registration=registration)
        self.assertEqual(reg_extra.choice_id, self.tent.id)

    def test_submitting_required_extra_without_a_choice_is_still_rejected(self):
        """A required extra that IS submitted but without a choice must
        still fail _attach_extra's existing requires_choice check — the new
        presence check doesn't relax that."""
        payload = self._payload()
        payload["parents"][0]["extras"] = [{"extra": str(self.accommodation.id)}]

        with patch("registrations.views.send_verification_email", return_value=True):
            response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400, response.data)

    def test_required_per_registration_extra_must_be_present(self):
        cabin = Extra.objects.create(
            event=self.event,
            name="Boende (hela familjen)",
            price=0,
            per_attendee=False,
            required=True,
        )
        # Satisfy the per-attendee "Boende" required extra from setUp too,
        # so this test isolates the per-registration required-extra check.
        payload = self._payload()
        payload["parents"][0]["extras"] = [
            {"extra": str(self.accommodation.id), "choice": str(self.tent.id)}
        ]

        with patch("registrations.views.send_verification_email", return_value=True):
            response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 400, response.data)

        payload["extras"] = [{"extra": str(cabin.id)}]
        with patch("registrations.views.send_verification_email", return_value=True):
            response = self.client.post(self.url, payload, format="json")

        self.assertEqual(response.status_code, 201, response.data)


class VerifyRegistrationPaidnessTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.event = _make_event()

    @staticmethod
    def _verify(client, token):
        return client.get(f"/api/registrations/verify/{token}/")

    def test_zero_total_itemized_registration_confirms_directly(self):
        free_type = TicketType.objects.create(event=self.event, name="Ledare", price=0)
        registration = _make_registration(self.event)
        parent = Parent.objects.create(
            family=registration.family, first_name="Anna", relationship_type="Mother"
        )
        EventTicket.objects.create(
            attendee=parent,
            event=self.event,
            registration=registration,
            ticket_type=free_type,
            price_at_registration=Decimal("0.00"),
        )
        token = "a" * 43
        registration.verification_token_hash = hash_token(token)
        registration.save(update_fields=["verification_token_hash"])

        with patch("registrations.views.send_confirmation_email", return_value=True):
            response = self._verify(self.client, token)

        self.assertEqual(response.status_code, 200, response.data)
        registration.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.CONFIRMED)
        self.assertFalse(hasattr(registration, "payment"))

    def test_nonzero_total_itemized_registration_routes_to_pending_payment(self):
        ticket_type = TicketType.objects.create(
            event=self.event, name="Adult", price=Decimal("1100.00")
        )
        registration = _make_registration(self.event)
        parent = Parent.objects.create(
            family=registration.family, first_name="Anna", relationship_type="Mother"
        )
        EventTicket.objects.create(
            attendee=parent,
            event=self.event,
            registration=registration,
            ticket_type=ticket_type,
            price_at_registration=Decimal("1100.00"),
        )
        token = "b" * 43
        registration.verification_token_hash = hash_token(token)
        registration.save(update_fields=["verification_token_hash"])

        with patch(
            "registrations.views.send_payment_instructions_email", return_value=True
        ):
            response = self._verify(self.client, token)

        self.assertEqual(response.status_code, 200, response.data)
        registration.refresh_from_db()
        self.assertEqual(registration.status, Registration.Status.PENDING_PAYMENT)
        payment = Payment.objects.get(registration=registration)
        self.assertEqual(payment.amount, Decimal("1100.00"))

    def test_payment_status_lookup_works_for_itemized_event_with_no_event_price(self):
        """registration_payment_status must key off the Payment row's
        existence, not Event.is_paid — an itemized event can owe money
        while Event.price itself stays unset."""
        ticket_type = TicketType.objects.create(
            event=self.event, name="Adult", price=Decimal("1100.00")
        )
        self.assertIsNone(self.event.price)
        registration = _make_registration(self.event)
        parent = Parent.objects.create(
            family=registration.family, first_name="Anna", relationship_type="Mother"
        )
        EventTicket.objects.create(
            attendee=parent,
            event=self.event,
            registration=registration,
            ticket_type=ticket_type,
            price_at_registration=Decimal("1100.00"),
        )
        Payment.objects.create(registration=registration, amount=Decimal("1100.00"))

        response = self.client.post(
            "/api/registrations/payment-status/",
            {
                "reference_code": registration.reference_code,
                "contact_email": registration.contact_email,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200, response.data)
