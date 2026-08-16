"""Plain-ORM payment-state logic (matches families/services.py's convention:
no DRF coupling — callers own validation, error handling, and audit logging).
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Literal

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import F, Q
from django.db.models.functions import Greatest
from django.utils.translation import gettext_lazy as _

from events.models import EventTicket, PromoCode, TicketType

from .emails import send_confirmation_email, send_payment_instructions_email
from .models import (
    ZERO,
    Payment,
    PaymentEvent,
    Registration,
    default_payment_expires_at,
)


class InvalidPaymentTransition(Exception):
    """Raised when a payment/registration state-changing function is asked to
    act on a Payment/Registration that isn't in the right state for it.
    Callers (the admin actions) catch this per-row rather than letting one
    bad row abort a bulk action."""


def record_payment_event(
    payment: Payment, *, kind: str, amount: Decimal, note: str = "", created_by
) -> PaymentEvent:
    """The only path that creates a PaymentEvent — the append-only ledger
    Payment.status/balance are derived from. Atomically records the event,
    recomputes Payment.status, and — only if that recompute lands on PAID
    while the registration is still pending_payment — confirms the
    registration (mirrors the pre-ledger mark_payment_paid side effect
    exactly). Confirmation email is sent outside the transaction.

    C1: enforces two prefix invariants on the ledger before the new event is
    created, checked against cumulative totals *including* it:
    1. refunded can never exceed received — you can't refund money that was
       never received (this is what stopped a single oversized refund from
       jumping a partially_paid Payment straight to a pending-looking state
       while real money was still sitting un-returned).
    2. for a REFUNDED or ADJUSTMENT event specifically, received − refunded
       + adjusted can't exceed amount. Deliberately *not* checked for a
       RECEIVED event — event_registration_ux_case_catalog.md §5.3 makes
       overpayment (a negative balance, surfaced to staff as a "registrera
       återbetalning" action) an intentional, supported state, not a bug.
       Combined with invariant 1 (refunded events can only ever shrink this
       expression), the only event kind invariant 2 can actually reject is
       an oversized ADJUSTMENT — a write-off larger than what's currently
       owed.
    """
    if amount <= Decimal("0"):
        raise ValueError("PaymentEvent amount must be positive")

    should_send_confirmation = False
    with transaction.atomic():
        # Locks the row and refreshes onto the *same* object the caller
        # passed in (rather than rebinding to a freshly fetched one) — some
        # callers (mark_payment_paid's own "already paid" guard) read
        # payment.status again afterwards and need to see this call's
        # effect, not a stale in-memory copy.
        payment.refresh_from_db(from_queryset=Payment.objects.select_for_update())
        if payment.status == Payment.Status.CANCELLED:
            raise InvalidPaymentTransition("Payment is cancelled")

        received, refunded, adjusted = payment.ledger_totals()
        if kind == PaymentEvent.Kind.RECEIVED:
            received += amount
        elif kind == PaymentEvent.Kind.REFUNDED:
            refunded += amount
        elif kind == PaymentEvent.Kind.ADJUSTMENT:
            adjusted += amount

        if refunded > received:
            raise InvalidPaymentTransition("Cannot refund more than has been received")
        if (
            kind != PaymentEvent.Kind.RECEIVED
            and received - refunded + adjusted > payment.amount
        ):
            raise InvalidPaymentTransition(
                "This would write off more than is currently owed"
            )

        event = PaymentEvent.objects.create(
            payment=payment, kind=kind, amount=amount, note=note, created_by=created_by
        )
        payment.recompute_status()

        registration = payment.registration
        if (
            payment.status == Payment.Status.PAID
            and registration.status == Registration.Status.PENDING_PAYMENT
        ):
            registration.status = Registration.Status.CONFIRMED
            registration.save(update_fields=["status"])
            should_send_confirmation = True

    if should_send_confirmation:
        send_confirmation_email(registration)

    return event


def mark_payment_paid(payment: Payment, *, method: str, marked_by) -> None:
    """Fast path: record the full outstanding balance as received in one
    shot — the common case where a family pays everything at once. For
    partial payments, refunds, or goodwill adjustments, record a
    PaymentEvent directly instead (see PaymentEventAdmin)."""
    if payment.status not in (Payment.Status.PENDING, Payment.Status.PARTIALLY_PAID):
        raise InvalidPaymentTransition(f"Payment is already {payment.status}")
    if payment.registration.status != Registration.Status.PENDING_PAYMENT:
        raise InvalidPaymentTransition(
            f"Registration is {payment.registration.status}, not pending_payment"
        )

    outstanding = payment.balance
    # method/marked_by are written only once record_payment_event has
    # actually committed the transition — it re-reads the row under
    # select_for_update and can reject it (e.g. the hourly sweep cancelled
    # this payment concurrently), and a rejected transition must not leave
    # method/marked_by set on a payment with no matching PaymentEvent.
    record_payment_event(
        payment,
        kind=PaymentEvent.Kind.RECEIVED,
        amount=outstanding,
        created_by=marked_by,
    )
    payment.method = method
    payment.marked_by = marked_by
    payment.save(update_fields=["method", "marked_by"])


def confirm_registration_despite_balance(
    registration: Registration, *, confirmed_by
) -> None:
    """Explicit staff-judgment-call path (case catalog §5.3: "de betalar
    resten på lägret") — confirms a pending_payment registration regardless
    of its outstanding balance. Deliberately separate from the ledger-driven
    auto-confirm in record_payment_event() so it's independently auditable:
    this is a staff decision to let someone in without full payment, not a
    consequence of money actually arriving."""
    with transaction.atomic():
        # Re-read under lock rather than trusting the caller's in-memory
        # instance (e.g. an admin bulk action's queryset row) — otherwise a
        # concurrent transition (the hourly sweep cancelling this
        # registration past its payment TTL) can go unnoticed and this call
        # resurrects an already-cancelled registration. Mirrors
        # record_payment_event's own select_for_update re-read.
        registration.refresh_from_db(
            from_queryset=Registration.objects.select_for_update()
        )
        if registration.status != Registration.Status.PENDING_PAYMENT:
            raise InvalidPaymentTransition(
                f"Registration is {registration.status}, not pending_payment"
            )

        registration.status = Registration.Status.CONFIRMED
        registration.save(update_fields=["status"])

    send_confirmation_email(registration)


def release_promo_code_use(registration: Registration) -> None:
    """Gives back a PromoCode slot a registration consumed but never
    completed — identical semantics to TicketType.capacity's (unimplemented)
    release, per event_registration_ux_case_catalog.md §5.4. Called from
    both TTL sweeps (tasks.py), RegistrationAdmin.cancel_registrations, and
    resolve_pending_review's reject path — the four ways a registration that
    used a code can end without confirming. An F()-based update so
    concurrent releases can't race each other; floored at 0 defensively
    (Greatest), though in practice each registration's promo use is only
    ever released once, since the four call sites are mutually exclusive by
    status transition."""
    if registration.promo_code_id is None:
        return
    PromoCode.objects.filter(pk=registration.promo_code_id).update(
        uses_count=Greatest(F("uses_count") - 1, 0)
    )


def resolve_pending_review(
    registration: Registration,
    *,
    action: Literal["confirm", "reject"],
    resolved_by,
) -> None:
    """Gives pending_review (verify_registration's anti-spoofing dedup gate —
    a verified email matched an existing Parent on a *different* family) a
    real resolution path. Mirrors confirm_registration_despite_balance's
    pattern: a dedicated service function so every transition out of
    pending_review gets the same Payment handling, email, and (via the
    caller's admin action) audit log that every other transition gets —
    unlike the raw Django-admin field edit this replaces, which skipped all
    three.

    ``action="confirm"``: routes exactly like a from-scratch
    verify_registration call would have if the email hadn't matched another
    family — pending_payment (with the payment-instructions email) if this
    registration's Payment (already created at verify time whenever its
    total is nonzero) is outstanding, confirmed (with the confirmation
    email) otherwise.

    ``action="reject"``: cancels the registration, cancels its Payment if
    one exists and is still untouched, and releases any promo-code use.
    """
    if registration.status != Registration.Status.PENDING_REVIEW:
        raise InvalidPaymentTransition(
            f"Registration is {registration.status}, not pending_review"
        )

    if action == "confirm":
        payment = getattr(registration, "payment", None)
        if payment is not None:
            registration.status = Registration.Status.PENDING_PAYMENT
            registration.expires_at = default_payment_expires_at()
            registration.save(update_fields=["status", "expires_at"])
            send_payment_instructions_email(registration)
        else:
            registration.status = Registration.Status.CONFIRMED
            registration.save(update_fields=["status"])
            send_confirmation_email(registration)
    elif action == "reject":
        registration.status = Registration.Status.CANCELLED
        registration.save(update_fields=["status"])
        payment = getattr(registration, "payment", None)
        if payment is not None and payment.status == Payment.Status.PENDING:
            payment.status = Payment.Status.CANCELLED
            payment.save(update_fields=["status"])
        release_promo_code_use(registration)
    else:
        raise ValueError(f"Unknown action: {action!r}")


# ---------------------------------------------------------------------------
# Ticket-type correction (case catalog §2.2 / §8.2)
# ---------------------------------------------------------------------------


class TicketTypeChangeRejected(Exception):
    """Raised when a ticket-type change must not happen at all — a type from
    another event, a retired type, or an unacknowledged age warning.

    Deliberately separate from InvalidPaymentTransition: that one means "the
    money is not in a state for this", this one means "this is not a legal
    re-tiering". Callers (the admin action) catch it per-row so one bad
    selection doesn't abort a bulk correction.
    """


class PriceEffect(str, Enum):
    """What ``change_attendee_ticket_type`` will do to the family's balance.

    Computed *before* the write so the admin's confirmation page can tell
    the operator which of these is about to happen — the whole point of the
    intermediate page is that nobody discovers the financial consequence
    afterwards.

    NONE
        No Payment to move (staff-created/imported ticket with no
        Registration, a free registration, a cancelled Payment), the price
        is unchanged, or the ticket carries no price snapshot to compare
        against.
    LEDGER_ADJUSTMENT
        The family owes *less* and the reduction fits inside what is still
        outstanding, so it is recorded as a PaymentEvent ADJUSTMENT — a
        write-off of part of a debt that still stands. ``Payment.amount``
        and ``price_at_registration`` are both left alone.
    AMOUNT_INCREASED / AMOUNT_REDUCED
        The ledger cannot express the change (see the module note on
        ``change_attendee_ticket_type``), so the owed side — the Payment's
        own amount — moves instead.
    """

    NONE = "none"
    LEDGER_ADJUSTMENT = "ledger_adjustment"
    AMOUNT_INCREASED = "amount_increased"
    AMOUNT_REDUCED = "amount_reduced"


EFFECT_LABELS = {
    PriceEffect.NONE: _("No change to what the family owes."),
    PriceEffect.LEDGER_ADJUSTMENT: _(
        "Recorded as an adjustment on the payment ledger: the outstanding "
        "balance goes down by the difference."
    ),
    PriceEffect.AMOUNT_INCREASED: _(
        "The amount owed goes up by the difference. The family has more to "
        "pay after this change."
    ),
    PriceEffect.AMOUNT_REDUCED: _(
        "The amount owed goes down by the difference. The family has "
        "already paid more than the new price, so the balance turns "
        "negative — repay the difference and record it as a refund."
    ),
}


@dataclass(frozen=True)
class TicketTypeChangePlan:
    """Everything the operator must be shown before the change is committed,
    and everything ``change_attendee_ticket_type`` needs to commit it."""

    ticket: EventTicket
    old_ticket_type: TicketType | None
    new_ticket_type: TicketType
    old_price: Decimal | None
    new_price: Decimal
    delta: Decimal
    payment: Payment | None
    effect: PriceEffect
    age_warning: str | None
    age_at_event: int | None

    @property
    def effect_label(self) -> str:
        return EFFECT_LABELS[self.effect]

    @property
    def requires_acknowledgement(self) -> bool:
        return self.age_warning is not None


# Revision round 1 (R2): a coordinator persona test had to eye-scan 212
# tickets to answer "is this child on the right tier?" by hand, because
# nothing on the changelist was filterable on that question. The predicate
# below is that filter's DB half; ``_age_window_mismatch`` just under it is
# the same rule stated for one ticket already loaded into Python, and
# ``_age_warning_for`` calls into it rather than repeating the comparison
# itself. Keeping both halves next to each other, deliberately not letting
# either drift into its own copy of "< min_birthdate or > max_birthdate", is
# the point: a filter that disagrees with the guarded wizard about who is
# mis-tiered is a worse failure than the scan it replaces.
#
# min_birthdate/max_birthdate are ordinary date columns on TicketType, so
# this is a plain field-to-field comparison — no annotate(), no date
# arithmetic, no migration.
AGE_MISMATCH_Q = Q(attendee__child__birthdate__lt=F("ticket_type__min_birthdate")) | Q(
    attendee__child__birthdate__gt=F("ticket_type__max_birthdate")
)

# The other half of "Åldern passar biljettypen": the two cases where the fit
# can't be evaluated at all (no Child row behind the attendee, or a Child
# with no birthdate recorded) *and* the assigned type actually has a window
# to check against. Mirrors the two early-return branches in
# ``_age_warning_for`` below.
UNCHECKABLE_AGE_FIT_Q = (
    Q(ticket_type__min_birthdate__isnull=False)
    | Q(ticket_type__max_birthdate__isnull=False)
) & (Q(attendee__child__isnull=True) | Q(attendee__child__birthdate__isnull=True))


def _age_window_mismatch(birthdate, ticket_type: TicketType) -> tuple[bool, bool]:
    """(too_old, too_young) for placing a child born on ``birthdate`` onto
    ``ticket_type``. The Python-side twin of ``AGE_MISMATCH_Q`` above — see
    its comment. ``_age_warning_for`` is the only caller; it exists as its
    own function so that comment has one predicate to point at, not two."""
    too_old = (
        ticket_type.min_birthdate is not None and birthdate < ticket_type.min_birthdate
    )
    too_young = (
        ticket_type.max_birthdate is not None and birthdate > ticket_type.max_birthdate
    )
    return too_old, too_young


def _age_warning_for(ticket: EventTicket, ticket_type: TicketType):
    """(warning, age_at_event) for putting ``ticket``'s attendee on
    ``ticket_type``.

    A *warning*, never a rejection: case catalog §2.2 (the birthday-crossing
    child) is a legitimate reason to sit outside the window, and the whole
    recommendation there is that a mis-tiering is fixed by "a staff-initiated
    ticket-type change through the edit flow, visible and audited". Blocking
    it would leave the operator with no way to do the thing the catalog says
    they must be able to do.

    The window is compared against the attendee's *birthdate*, not a derived
    age, because that is how TicketType stores it (a cohort/årskurs window).
    ``age_at_event`` is returned alongside purely so the confirmation page
    can show the number a human actually reasons about, and uses the same
    ``reports.services.age_on`` the 0.2 changelist column uses — two age
    calculations in one codebase eventually disagree on a birthday boundary.
    """
    from reports.services import age_on

    has_window = (
        ticket_type.min_birthdate is not None or ticket_type.max_birthdate is not None
    )

    try:
        child = ticket.attendee.child
    except ObjectDoesNotExist:
        # A parent's ticket. No birthdate exists to check, and an adult
        # ticket type legitimately has no window either.
        if has_window:
            return (
                _(
                    "%(attendee)s is not registered as a child, so the age "
                    "range for %(ticket_type)s could not be checked."
                )
                % {
                    "attendee": str(ticket.attendee),
                    "ticket_type": ticket_type.name,
                },
                None,
            )
        return None, None

    age = age_on(child.birthdate, ticket.event.start_date)

    if not has_window:
        return None, age

    if child.birthdate is None:
        return (
            _(
                "No birthdate is recorded for %(attendee)s, so the age range "
                "for %(ticket_type)s could not be checked."
            )
            % {"attendee": str(ticket.attendee), "ticket_type": ticket_type.name},
            None,
        )

    too_old, too_young = _age_window_mismatch(child.birthdate, ticket_type)
    if not (too_old or too_young):
        return None, age

    return (
        _(
            "%(attendee)s was born %(birthdate)s and is %(age)s on the first "
            "day of the event, which falls outside the age range for "
            "%(ticket_type)s. Continue only if this is deliberate."
        )
        % {
            "attendee": str(ticket.attendee),
            "birthdate": child.birthdate.isoformat(),
            "age": age,
            "ticket_type": ticket_type.name,
        },
        age,
    )


def plan_ticket_type_change(
    ticket: EventTicket, new_ticket_type: TicketType
) -> TicketTypeChangePlan:
    """Validate a proposed re-tiering and work out what it would do, without
    writing anything. Raises TicketTypeChangeRejected for the three things
    that are never allowed; everything else — including an age mismatch — is
    reported back for the operator to decide on.
    """
    if new_ticket_type.event_id != ticket.event_id:
        raise TicketTypeChangeRejected(
            _("%(ticket_type)s belongs to a different event.")
            % {"ticket_type": str(new_ticket_type)}
        )
    if not new_ticket_type.is_active:
        raise TicketTypeChangeRejected(
            _("%(ticket_type)s has been retired and can no longer be assigned.")
            % {"ticket_type": new_ticket_type.name}
        )
    if ticket.ticket_type_id == new_ticket_type.id:
        raise TicketTypeChangeRejected(
            _("This ticket is already on %(ticket_type)s.")
            % {"ticket_type": new_ticket_type.name}
        )

    age_warning, age_at_event = _age_warning_for(ticket, new_ticket_type)

    old_price = ticket.price_at_registration
    new_price = new_ticket_type.price
    payment = None
    if ticket.registration_id is not None:
        payment = getattr(ticket.registration, "payment", None)

    if old_price is None:
        # Nothing to compare against: this ticket was never priced into the
        # registration's total (staff-created, imported, or a flat-price
        # event). Inventing a charge from an absent snapshot would be a
        # guess, and price_at_registration is written once at submission and
        # never recomputed, so there is nothing to repair it from either.
        delta = ZERO
        effect = PriceEffect.NONE
    else:
        delta = new_price - old_price
        if payment is None or payment.status == Payment.Status.CANCELLED or delta == 0:
            effect = PriceEffect.NONE
        elif delta > 0:
            effect = PriceEffect.AMOUNT_INCREASED
        elif payment.balance >= -delta:
            # The write-off fits inside what is still owed, which is exactly
            # what an ADJUSTMENT means.
            effect = PriceEffect.LEDGER_ADJUSTMENT
        else:
            effect = PriceEffect.AMOUNT_REDUCED

    return TicketTypeChangePlan(
        ticket=ticket,
        old_ticket_type=ticket.ticket_type,
        new_ticket_type=new_ticket_type,
        old_price=old_price,
        new_price=new_price,
        delta=delta,
        payment=payment,
        effect=effect,
        age_warning=age_warning,
        age_at_event=age_at_event,
    )


def change_attendee_ticket_type(
    ticket: EventTicket,
    *,
    new_ticket_type: TicketType,
    changed_by,
    acknowledge_age_warning: bool = False,
) -> TicketTypeChangePlan:
    """Move one EventTicket onto another TicketType and carry the money with
    it. The safe version of the raw Django-admin field edit, which changed
    the type and left the family's balance describing the old one.

    Validates (hard failures, TicketTypeChangeRejected):
      * the new type belongs to the same Event as the ticket;
      * the new type is still ``is_active``;
      * it is not the type the ticket already has;
      * any age warning has been acknowledged by the caller.

    Warns (never blocks): the attendee's birthdate falling outside the new
    type's min/max window — see ``_age_warning_for`` and case catalog §2.2.

    Writes:
      * ``EventTicket.ticket_type``;
      * and, depending on ``plan.effect``, either a PaymentEvent ADJUSTMENT
        or a new ``Payment.amount``.

    ``price_at_registration`` is never touched. It is the snapshot written
    once at submission that makes mid-sale price edits safe by construction
    (case catalog §9.4), and the operator-facing help text on that field
    promises exactly that. The correction therefore lands on the *owed*
    side, per case catalog §8.2 ("status and balance are orthogonal;
    edits update the owed side and the derived balance").

    Why not always a PaymentEvent ADJUSTMENT: the ledger has three kinds and
    ``balance = amount - received + refunded - adjusted``, so an ADJUSTMENT
    can only ever make a family owe *less*. The headline case — a 13-year-old
    sitting on the 0-12 ticket — makes them owe *more*, and the only kind
    that raises a balance is REFUNDED, which would both lie about money
    having moved and flip ``recompute_status`` to REFUNDED. Likewise a
    reduction larger than what is still outstanding is rejected outright by
    ``record_payment_event``'s C1 invariant 2. So the ledger is used wherever
    it can express the change honestly, and ``Payment.amount`` moves in the
    two cases where it cannot. See ``PriceEffect``.

    Returns the executed plan, so the caller can audit-log and report exactly
    what happened.
    """
    plan = plan_ticket_type_change(ticket, new_ticket_type)
    if plan.requires_acknowledgement and not acknowledge_age_warning:
        raise TicketTypeChangeRejected(plan.age_warning)

    note = str(
        _("Ticket type changed from %(old)s to %(new)s")
        % {
            "old": plan.old_ticket_type.name if plan.old_ticket_type else _("none"),
            "new": plan.new_ticket_type.name,
        }
    )[:255]

    registration_to_confirm = None
    with transaction.atomic():
        # Re-read under lock rather than trusting the admin queryset's
        # snapshot, mirroring record_payment_event: another operator may have
        # re-tiered this same ticket between the confirmation page rendering
        # and this submit, and the delta shown was computed against the old
        # row.
        ticket.refresh_from_db(from_queryset=EventTicket.objects.select_for_update())
        if ticket.ticket_type_id != (
            plan.old_ticket_type.id if plan.old_ticket_type else None
        ):
            raise TicketTypeChangeRejected(
                _("This ticket was changed by someone else — review it again.")
            )

        ticket.ticket_type = new_ticket_type
        ticket.save(update_fields=["ticket_type"])

        if plan.effect == PriceEffect.LEDGER_ADJUSTMENT:
            record_payment_event(
                plan.payment,
                kind=PaymentEvent.Kind.ADJUSTMENT,
                amount=-plan.delta,
                note=note,
                created_by=changed_by,
            )
        elif plan.effect in (
            PriceEffect.AMOUNT_INCREASED,
            PriceEffect.AMOUNT_REDUCED,
        ):
            payment = plan.payment
            payment.refresh_from_db(from_queryset=Payment.objects.select_for_update())
            payment.amount = payment.amount + plan.delta
            payment.save(update_fields=["amount"])
            payment.recompute_status()
            registration = payment.registration
            if (
                payment.status == Payment.Status.PAID
                and registration.status == Registration.Status.PENDING_PAYMENT
            ):
                # Same side effect record_payment_event owns for the ledger
                # path: a payment that lands on PAID confirms a registration
                # still waiting on money. Repeated here rather than folded
                # into that function, which is deliberately the *ledger's*
                # entry point and is not modified by this change.
                registration.status = Registration.Status.CONFIRMED
                registration.save(update_fields=["status"])
                registration_to_confirm = registration

    if registration_to_confirm is not None:
        send_confirmation_email(registration_to_confirm)

    return plan
