"""
Safe ticket-type correction (increment 0.6 / roadmap step 1).

The failure this exists to prevent: a family says their 13-year-old is on the
0-12 ticket. Increment 0.2 made that child findable. Fixing her was still a
raw ``ticket_type`` edit on the Django change form, which changed the type,
left ``price_at_registration`` describing the old one, left the Payment
describing the old one, and would just as happily have attached a ticket type
belonging to a completely different event.

These tests pin the four things ``change_attendee_ticket_type`` adds: the
same-event rule, the age *warning* (which must fire and must be overridable —
case catalog §2.2's birthday-crossing child is a legitimate reason to sit
outside the window), the money moving in the right direction, and the
snapshot on ``price_at_registration`` never being rewritten.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import AdminUser
from checkins.models import AuditLog
from events.models import Event, EventTicket, TicketType
from families.models import Child, Family, Parent

from .models import Payment, PaymentEvent, Registration
from .services import (
    PriceEffect,
    TicketTypeChangeRejected,
    change_attendee_ticket_type,
    plan_ticket_type_change,
    record_payment_event,
)
from .tokens import generate_verification_token, hash_token

# Event runs in July; Ebba turns 13 in May, so she is 12 at registration and
# 13 on day one — case catalog §2.2 exactly.
EVENT_START = date(2026, 7, 6)


def _make_event(name="Sommarläger 2026"):
    return Event.objects.create(
        name=name,
        start_date=EVENT_START,
        end_date=EVENT_START + timezone.timedelta(days=4),
        registration_opens_at=timezone.now() - timezone.timedelta(days=1),
    )


def _child_type(event, **kwargs):
    """0-12: born 2013-07-06 or later (i.e. 12 or younger on day one)."""
    defaults = {
        "name": "Barn 0-12",
        "price": Decimal("400.00"),
        "min_birthdate": date(2013, 7, 7),
        "max_birthdate": None,
    }
    return TicketType.objects.create(event=event, **{**defaults, **kwargs})


def _youth_type(event, **kwargs):
    """13-17: born 2008-07-06 .. 2013-07-06."""
    defaults = {
        "name": "Ungdom 13-17",
        "price": Decimal("700.00"),
        "min_birthdate": date(2008, 7, 7),
        "max_birthdate": date(2013, 7, 6),
    }
    return TicketType.objects.create(event=event, **{**defaults, **kwargs})


def _make_registration(event, *, family=None, status=Registration.Status.CONFIRMED):
    family = family or Family.objects.create(last_name="Lindqvist")
    return Registration.objects.create(
        event=event,
        family=family,
        contact_email="lindqvist@example.com",
        verification_token_hash=hash_token(generate_verification_token()),
        status=status,
        verified_at=timezone.now(),
    )


def _make_ticket(
    event,
    ticket_type,
    *,
    registration=None,
    price=Decimal("400.00"),
    birthdate=date(2013, 5, 12),
    family=None,
    first_name="Ebba",
):
    family = family or (
        registration.family if registration else Family.objects.create()
    )
    attendee = Child.objects.create(
        family=family, first_name=first_name, birthdate=birthdate
    )
    return EventTicket.objects.create(
        attendee=attendee,
        event=event,
        registration=registration,
        ticket_type=ticket_type,
        price_at_registration=price,
    )


class TicketTypeValidationTests(TestCase):
    """The three hard rejections. Nothing in the schema enforces any of
    them today — ``ticket_type`` is a plain FK to TicketType with no
    same-event tie."""

    def setUp(self):
        self.user = AdminUser.objects.create_superuser("triage", "pw12345")
        self.event = _make_event()
        self.child_type = _child_type(self.event)
        self.youth_type = _youth_type(self.event)
        self.ticket = _make_ticket(self.event, self.child_type)

    def test_ticket_type_from_another_event_is_rejected(self):
        other_event = _make_event("Vinterläger 2027")
        foreign_type = _youth_type(other_event)
        with self.assertRaises(TicketTypeChangeRejected):
            change_attendee_ticket_type(
                self.ticket, new_ticket_type=foreign_type, changed_by=self.user
            )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.ticket_type_id, self.child_type.id)

    def test_retired_ticket_type_is_rejected(self):
        retired = _youth_type(self.event, name="Ungdom (utgången)", is_active=False)
        with self.assertRaises(TicketTypeChangeRejected):
            change_attendee_ticket_type(
                self.ticket, new_ticket_type=retired, changed_by=self.user
            )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.ticket_type_id, self.child_type.id)

    def test_changing_to_the_type_it_already_has_is_rejected(self):
        with self.assertRaises(TicketTypeChangeRejected):
            change_attendee_ticket_type(
                self.ticket, new_ticket_type=self.child_type, changed_by=self.user
            )

    def test_a_legal_change_goes_through(self):
        plan = change_attendee_ticket_type(
            self.ticket,
            new_ticket_type=self.youth_type,
            changed_by=self.user,
            acknowledge_age_warning=True,
        )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.ticket_type_id, self.youth_type.id)
        self.assertEqual(plan.new_ticket_type, self.youth_type)


class AgeWarningTests(TestCase):
    """§2.2: warn, never block. A child who turns 13 during the event is a
    legitimate reason to sit outside the window, so the operator has to be
    told and then allowed to proceed anyway."""

    def setUp(self):
        self.user = AdminUser.objects.create_superuser("triage", "pw12345")
        self.event = _make_event()
        self.child_type = _child_type(self.event)
        self.youth_type = _youth_type(self.event)

    def test_no_warning_when_the_birthdate_fits_the_window(self):
        # Born 2012-03-01 -> 14 on day one, inside 13-17.
        ticket = _make_ticket(self.event, self.child_type, birthdate=date(2012, 3, 1))
        plan = plan_ticket_type_change(ticket, self.youth_type)
        self.assertIsNone(plan.age_warning)
        self.assertEqual(plan.age_at_event, 14)

    def test_warning_fires_when_the_birthdate_is_outside_the_window(self):
        # Born 2020 -> 6 on day one, nowhere near 13-17.
        ticket = _make_ticket(self.event, self.child_type, birthdate=date(2020, 1, 1))
        plan = plan_ticket_type_change(ticket, self.youth_type)
        self.assertIsNotNone(plan.age_warning)
        self.assertTrue(plan.requires_acknowledgement)

    def test_an_unacknowledged_warning_blocks_the_change(self):
        ticket = _make_ticket(self.event, self.child_type, birthdate=date(2020, 1, 1))
        with self.assertRaises(TicketTypeChangeRejected):
            change_attendee_ticket_type(
                ticket, new_ticket_type=self.youth_type, changed_by=self.user
            )
        ticket.refresh_from_db()
        self.assertEqual(ticket.ticket_type_id, self.child_type.id)

    def test_the_warning_is_overridable(self):
        ticket = _make_ticket(self.event, self.child_type, birthdate=date(2020, 1, 1))
        change_attendee_ticket_type(
            ticket,
            new_ticket_type=self.youth_type,
            changed_by=self.user,
            acknowledge_age_warning=True,
        )
        ticket.refresh_from_db()
        self.assertEqual(ticket.ticket_type_id, self.youth_type.id)

    def test_the_birthday_crossing_child_is_warned_but_allowed(self):
        """Ebba: 12 at registration in March, 13 on the first day of camp.
        Her birthdate (2013-05-12) is inside the youth window, so this is
        actually the *quiet* case — the point of the test is that fixing her
        does not require an override, while a genuine mismatch does."""
        ticket = _make_ticket(self.event, self.child_type)
        plan = plan_ticket_type_change(ticket, self.youth_type)
        self.assertEqual(plan.age_at_event, 13)
        self.assertIsNone(plan.age_warning)

    def test_a_missing_birthdate_warns_rather_than_silently_passing(self):
        ticket = _make_ticket(self.event, self.child_type, birthdate=None)
        plan = plan_ticket_type_change(ticket, self.youth_type)
        self.assertIsNotNone(plan.age_warning)

    def test_a_parent_ticket_on_an_age_ranged_type_warns(self):
        family = Family.objects.create(last_name="Lindqvist")
        parent = Parent.objects.create(
            family=family, first_name="Anna", relationship_type="Mother"
        )
        ticket = EventTicket.objects.create(
            attendee=parent,
            event=self.event,
            ticket_type=self.child_type,
            price_at_registration=Decimal("400.00"),
        )
        plan = plan_ticket_type_change(ticket, self.youth_type)
        self.assertIsNotNone(plan.age_warning)

    def test_a_type_with_no_window_never_warns(self):
        adult = TicketType.objects.create(
            event=self.event, name="Vuxen", price=Decimal("1100.00")
        )
        ticket = _make_ticket(self.event, self.child_type, birthdate=date(2020, 1, 1))
        plan = plan_ticket_type_change(ticket, adult)
        self.assertIsNone(plan.age_warning)


class PriceDeltaTests(TestCase):
    """The delta arithmetic, in both directions.

    ``price_at_registration`` is asserted unchanged in every one of these:
    increment 0.5 shipped operator-facing help text on that field promising
    "Editing a price is safe — tickets already sold keep the price they were
    sold at", and this service is the most likely thing to break it.
    """

    def setUp(self):
        self.user = AdminUser.objects.create_superuser("triage", "pw12345")
        self.event = _make_event()
        self.child_type = _child_type(self.event)
        self.youth_type = _youth_type(self.event)
        self.registration = _make_registration(
            self.event, status=Registration.Status.PENDING_PAYMENT
        )
        self.payment = Payment.objects.create(
            registration=self.registration, amount=Decimal("400.00")
        )
        self.ticket = _make_ticket(
            self.event, self.child_type, registration=self.registration
        )

    def _reread(self):
        self.payment.refresh_from_db()
        self.ticket.refresh_from_db()

    def test_upgrade_raises_what_is_owed(self):
        plan = change_attendee_ticket_type(
            self.ticket,
            new_ticket_type=self.youth_type,
            changed_by=self.user,
            acknowledge_age_warning=True,
        )
        self._reread()
        self.assertEqual(plan.delta, Decimal("300.00"))
        self.assertEqual(plan.effect, PriceEffect.AMOUNT_INCREASED)
        self.assertEqual(self.payment.balance, Decimal("700.00"))
        self.assertEqual(self.payment.amount, Decimal("700.00"))
        self.assertEqual(self.ticket.price_at_registration, Decimal("400.00"))

    def test_upgrade_writes_no_ledger_event(self):
        change_attendee_ticket_type(
            self.ticket,
            new_ticket_type=self.youth_type,
            changed_by=self.user,
            acknowledge_age_warning=True,
        )
        # An ADJUSTMENT can only *reduce* a balance and a REFUNDED would lie
        # about money having moved (and flip recompute_status to REFUNDED),
        # so an upgrade must not touch the ledger at all.
        self.assertEqual(self.payment.events.count(), 0)

    def test_downgrade_writes_an_adjustment_that_lowers_the_balance(self):
        # The other direction: an adult wrongly on the 1100 kr type.
        adult = TicketType.objects.create(
            event=self.event, name="Vuxen", price=Decimal("1100.00")
        )
        self.ticket.ticket_type = adult
        self.ticket.price_at_registration = Decimal("1100.00")
        self.ticket.save()
        self.payment.amount = Decimal("1100.00")
        self.payment.save()

        plan = change_attendee_ticket_type(
            self.ticket,
            new_ticket_type=self.youth_type,
            changed_by=self.user,
            acknowledge_age_warning=True,
        )
        self._reread()
        self.assertEqual(plan.delta, Decimal("-400.00"))
        self.assertEqual(plan.effect, PriceEffect.LEDGER_ADJUSTMENT)
        adjustment = self.payment.events.get()
        self.assertEqual(adjustment.kind, PaymentEvent.Kind.ADJUSTMENT)
        # Positive amount, ADJUSTMENT kind: the ledger stores magnitudes and
        # lets the kind carry the sign.
        self.assertEqual(adjustment.amount, Decimal("400.00"))
        self.assertEqual(adjustment.created_by, self.user)
        self.assertEqual(self.payment.balance, Decimal("700.00"))
        self.assertEqual(self.payment.amount, Decimal("1100.00"))
        self.assertEqual(self.ticket.price_at_registration, Decimal("1100.00"))

    def test_downgrade_below_what_was_already_paid_moves_the_amount_instead(self):
        """A family who already paid in full and is then moved to a cheaper
        type is not owed a *write-off* — they are owed money back. The
        ledger refuses an ADJUSTMENT bigger than what is still outstanding
        (record_payment_event's C1 invariant 2), so the owed side moves and
        the overpayment surfaces as a negative balance, which is §5.3's
        supported "staff registers a refund" state."""
        adult = TicketType.objects.create(
            event=self.event, name="Vuxen", price=Decimal("1100.00")
        )
        self.ticket.ticket_type = adult
        self.ticket.price_at_registration = Decimal("1100.00")
        self.ticket.save()
        self.payment.amount = Decimal("1100.00")
        self.payment.save()
        record_payment_event(
            self.payment,
            kind=PaymentEvent.Kind.RECEIVED,
            amount=Decimal("1100.00"),
            created_by=self.user,
        )

        plan = change_attendee_ticket_type(
            self.ticket,
            new_ticket_type=self.youth_type,
            changed_by=self.user,
            acknowledge_age_warning=True,
        )
        self._reread()
        self.assertEqual(plan.effect, PriceEffect.AMOUNT_REDUCED)
        self.assertEqual(self.payment.amount, Decimal("700.00"))
        self.assertEqual(self.payment.balance, Decimal("-400.00"))
        self.assertEqual(self.payment.events.count(), 1)  # only the RECEIVED

    def test_zero_delta_writes_nothing_to_the_ledger(self):
        """Two types at the same price. record_payment_event rejects a
        non-positive amount outright, and PaymentEvent.amount carries
        MinValueValidator(0.01) — a zero-amount row is not merely noise, it
        is unrepresentable. The audit trail lives in AuditLog instead."""
        same_price = TicketType.objects.create(
            event=self.event, name="Ledare barn", price=Decimal("400.00")
        )
        plan = change_attendee_ticket_type(
            self.ticket, new_ticket_type=same_price, changed_by=self.user
        )
        self._reread()
        self.assertEqual(plan.delta, Decimal("0.00"))
        self.assertEqual(plan.effect, PriceEffect.NONE)
        self.assertEqual(self.payment.events.count(), 0)
        self.assertEqual(self.payment.amount, Decimal("400.00"))
        self.assertEqual(self.ticket.ticket_type_id, same_price.id)

    def test_a_ticket_with_no_registration_changes_type_and_touches_no_money(self):
        """The nullable FK is not an edge case: staff-created and imported
        tickets have no Registration and therefore no Payment."""
        orphan = _make_ticket(self.event, self.child_type, registration=None)
        plan = change_attendee_ticket_type(
            orphan,
            new_ticket_type=self.youth_type,
            changed_by=self.user,
            acknowledge_age_warning=True,
        )
        orphan.refresh_from_db()
        self.assertIsNone(plan.payment)
        self.assertEqual(plan.effect, PriceEffect.NONE)
        self.assertEqual(orphan.ticket_type_id, self.youth_type.id)
        self.assertEqual(orphan.price_at_registration, Decimal("400.00"))

    def test_a_registration_with_no_payment_is_handled(self):
        """A free registration (0 kr total) never gets a Payment row."""
        free_registration = _make_registration(self.event)
        ticket = _make_ticket(
            self.event, self.child_type, registration=free_registration
        )
        plan = change_attendee_ticket_type(
            ticket,
            new_ticket_type=self.youth_type,
            changed_by=self.user,
            acknowledge_age_warning=True,
        )
        self.assertIsNone(plan.payment)
        self.assertEqual(plan.effect, PriceEffect.NONE)

    def test_a_ticket_with_no_price_snapshot_touches_no_money(self):
        """price_at_registration is null on staff-created and imported
        tickets. There is no snapshot to compute a difference from and none
        may be invented, so the type moves and the balance does not."""
        self.ticket.price_at_registration = None
        self.ticket.save()
        plan = change_attendee_ticket_type(
            self.ticket,
            new_ticket_type=self.youth_type,
            changed_by=self.user,
            acknowledge_age_warning=True,
        )
        self._reread()
        self.assertEqual(plan.effect, PriceEffect.NONE)
        self.assertIsNone(self.ticket.price_at_registration)
        self.assertEqual(self.payment.amount, Decimal("400.00"))

    def test_a_cancelled_payment_is_left_alone(self):
        self.payment.status = Payment.Status.CANCELLED
        self.payment.save()
        plan = change_attendee_ticket_type(
            self.ticket,
            new_ticket_type=self.youth_type,
            changed_by=self.user,
            acknowledge_age_warning=True,
        )
        self._reread()
        self.assertEqual(plan.effect, PriceEffect.NONE)
        self.assertEqual(self.payment.amount, Decimal("400.00"))
        self.assertEqual(self.payment.status, Payment.Status.CANCELLED)

    def test_a_downgrade_that_settles_the_balance_confirms_the_registration(self):
        """Same side effect record_payment_event owns on the ledger path: a
        payment that lands on PAID confirms a registration still waiting on
        money. Reaching PAID through the owed side must behave identically."""
        adult = TicketType.objects.create(
            event=self.event, name="Vuxen", price=Decimal("1100.00")
        )
        self.ticket.ticket_type = adult
        self.ticket.price_at_registration = Decimal("1100.00")
        self.ticket.save()
        self.payment.amount = Decimal("1100.00")
        self.payment.save()
        record_payment_event(
            self.payment,
            kind=PaymentEvent.Kind.RECEIVED,
            amount=Decimal("900.00"),
            created_by=self.user,
        )
        self.registration.refresh_from_db()
        self.assertEqual(self.registration.status, Registration.Status.PENDING_PAYMENT)

        change_attendee_ticket_type(
            self.ticket,
            new_ticket_type=self.youth_type,
            changed_by=self.user,
            acknowledge_age_warning=True,
        )
        self._reread()
        self.registration.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.Status.PAID)
        self.assertEqual(self.registration.status, Registration.Status.CONFIRMED)


class BalanceAnnotationStaysConsistentTests(TestCase):
    """Increment 0.3's SQL twin of ``Payment.balance`` has to keep agreeing
    with the property after this service has moved money — through both the
    ledger path and the amount path."""

    def setUp(self):
        self.user = AdminUser.objects.create_superuser("triage", "pw12345")
        self.event = _make_event()
        self.child_type = _child_type(self.event)
        self.youth_type = _youth_type(self.event)
        self.adult_type = TicketType.objects.create(
            event=self.event, name="Vuxen", price=Decimal("1100.00")
        )

    def _annotated(self, payment):
        return (
            Payment.objects.filter(pk=payment.pk)
            .annotate(**{Payment.BALANCE_ANNOTATION: Payment.balance_expression()})
            .values_list(Payment.BALANCE_ANNOTATION, flat=True)
            .first()
        )

    def _scenario(self, *, start_type, start_price, amount, new_type, received=None):
        registration = _make_registration(
            self.event, status=Registration.Status.PENDING_PAYMENT
        )
        payment = Payment.objects.create(registration=registration, amount=amount)
        ticket = _make_ticket(
            self.event, start_type, registration=registration, price=start_price
        )
        if received is not None:
            record_payment_event(
                payment,
                kind=PaymentEvent.Kind.RECEIVED,
                amount=received,
                created_by=self.user,
            )
        change_attendee_ticket_type(
            ticket,
            new_ticket_type=new_type,
            changed_by=self.user,
            acknowledge_age_warning=True,
        )
        payment.refresh_from_db()
        return payment

    def test_after_an_upgrade(self):
        payment = self._scenario(
            start_type=self.child_type,
            start_price=Decimal("400.00"),
            amount=Decimal("400.00"),
            new_type=self.youth_type,
        )
        self.assertEqual(payment.balance, self._annotated(payment))

    def test_after_a_ledger_adjustment(self):
        payment = self._scenario(
            start_type=self.adult_type,
            start_price=Decimal("1100.00"),
            amount=Decimal("1100.00"),
            new_type=self.youth_type,
        )
        self.assertEqual(payment.balance, self._annotated(payment))

    def test_after_an_amount_reduction_on_an_overpaid_payment(self):
        payment = self._scenario(
            start_type=self.adult_type,
            start_price=Decimal("1100.00"),
            amount=Decimal("1100.00"),
            new_type=self.youth_type,
            received=Decimal("1100.00"),
        )
        self.assertEqual(payment.balance, self._annotated(payment))
        self.assertEqual(payment.balance, Decimal("-400.00"))


# Same reason as tests_admin_index.py: WhiteNoise's manifest storage refuses
# to resolve admin CSS unless collectstatic has run, and rendering an admin
# page here is unrelated to static-asset hashing.
@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }
)
class ChangeTicketTypeAdminActionTests(TestCase):
    """The intermediate page — the only place the operator sees the price
    difference and the age warning before committing."""

    def setUp(self):
        self.user = AdminUser.objects.create_superuser("triage", "pw12345")
        self.client.force_login(self.user)
        self.url = reverse("admin:events_eventticket_changelist")
        self.event = _make_event()
        self.child_type = _child_type(self.event)
        self.youth_type = _youth_type(self.event)
        self.registration = _make_registration(
            self.event, status=Registration.Status.PENDING_PAYMENT
        )
        self.payment = Payment.objects.create(
            registration=self.registration, amount=Decimal("400.00")
        )
        self.ticket = _make_ticket(
            self.event, self.child_type, registration=self.registration
        )

    def _post(self, data):
        return self.client.post(self.url, data, follow=True)

    def test_step_one_offers_only_this_events_active_ticket_types(self):
        other_event_type = _youth_type(_make_event("Vinterläger"))
        retired = _youth_type(self.event, name="Utgången", is_active=False)
        response = self._post(
            {"action": "change_ticket_type", "_selected_action": [str(self.ticket.id)]}
        )
        choices = response.context["form"].fields["ticket_type"].queryset
        self.assertIn(self.youth_type, choices)
        self.assertNotIn(other_event_type, choices)
        self.assertNotIn(retired, choices)

    def test_step_two_shows_the_price_difference_before_committing(self):
        response = self._post(
            {
                "action": "change_ticket_type",
                "_selected_action": [str(self.ticket.id)],
                "preview": "yes",
                "ticket_type": str(self.youth_type.id),
            }
        )
        self.assertTrue(response.context["is_preview"])
        (plan,) = response.context["plans"]
        self.assertEqual(plan.delta, Decimal("300.00"))
        self.assertContains(response, "300")
        # Nothing written yet.
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.ticket_type_id, self.child_type.id)

    def test_step_two_surfaces_the_age_warning(self):
        self.ticket.attendee.child.birthdate = date(2020, 1, 1)
        self.ticket.attendee.child.save()
        response = self._post(
            {
                "action": "change_ticket_type",
                "_selected_action": [str(self.ticket.id)],
                "preview": "yes",
                "ticket_type": str(self.youth_type.id),
            }
        )
        self.assertTrue(response.context["needs_acknowledgement"])
        (plan,) = response.context["plans"]
        self.assertIsNotNone(plan.age_warning)

    def test_apply_commits_the_change_and_writes_an_audit_entry(self):
        self._post(
            {
                "action": "change_ticket_type",
                "_selected_action": [str(self.ticket.id)],
                "apply": "yes",
                "ticket_type": str(self.youth_type.id),
                "acknowledge_age_warning": "on",
            }
        )
        self.ticket.refresh_from_db()
        self.payment.refresh_from_db()
        self.assertEqual(self.ticket.ticket_type_id, self.youth_type.id)
        self.assertEqual(self.payment.amount, Decimal("700.00"))

        entry = AuditLog.objects.get(action="event_ticket_type_changed")
        self.assertEqual(entry.entity_type, "EventTicket")
        self.assertEqual(entry.entity_id, str(self.ticket.id))
        self.assertEqual(entry.user, self.user)
        self.assertEqual(entry.details["from_ticket_type"], "Barn 0-12")
        self.assertEqual(entry.details["to_ticket_type"], "Ungdom 13-17")
        self.assertEqual(entry.details["delta"], "300.00")
        self.assertEqual(entry.details["price_effect"], "amount_increased")

    def test_apply_without_acknowledging_an_age_warning_changes_nothing(self):
        self.ticket.attendee.child.birthdate = date(2020, 1, 1)
        self.ticket.attendee.child.save()
        self._post(
            {
                "action": "change_ticket_type",
                "_selected_action": [str(self.ticket.id)],
                "apply": "yes",
                "ticket_type": str(self.youth_type.id),
            }
        )
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.ticket_type_id, self.child_type.id)
        self.assertFalse(
            AuditLog.objects.filter(action="event_ticket_type_changed").exists()
        )

    def test_tickets_from_two_events_are_refused_outright(self):
        other_event = _make_event("Vinterläger")
        other_ticket = _make_ticket(other_event, _child_type(other_event))
        response = self._post(
            {
                "action": "change_ticket_type",
                "_selected_action": [str(self.ticket.id), str(other_ticket.id)],
            }
        )
        self.assertNotIn("plans", response.context)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.ticket_type_id, self.child_type.id)

    def test_a_rejected_row_is_reported_rather_than_silently_dropped(self):
        response = self._post(
            {
                "action": "change_ticket_type",
                "_selected_action": [str(self.ticket.id)],
                "preview": "yes",
                "ticket_type": str(self.child_type.id),
            }
        )
        self.assertEqual(len(response.context["rejections"]), 1)
        self.assertEqual(response.context["plans"], [])
