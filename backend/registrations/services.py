"""Plain-ORM payment-state logic (matches families/services.py's convention:
no DRF coupling — callers own validation, error handling, and audit logging).
"""

from decimal import Decimal
from typing import Literal

from django.db import transaction
from django.db.models import F
from django.db.models.functions import Greatest

from events.models import PromoCode

from .emails import send_confirmation_email, send_payment_instructions_email
from .models import Payment, PaymentEvent, Registration, default_payment_expires_at


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
            raise InvalidPaymentTransition(
                "Cannot refund more than has been received"
            )
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
    payment.method = method
    payment.marked_by = marked_by
    payment.save(update_fields=["method", "marked_by"])
    record_payment_event(
        payment,
        kind=PaymentEvent.Kind.RECEIVED,
        amount=outstanding,
        created_by=marked_by,
    )


def confirm_registration_despite_balance(
    registration: Registration, *, confirmed_by
) -> None:
    """Explicit staff-judgment-call path (case catalog §5.3: "de betalar
    resten på lägret") — confirms a pending_payment registration regardless
    of its outstanding balance. Deliberately separate from the ledger-driven
    auto-confirm in record_payment_event() so it's independently auditable:
    this is a staff decision to let someone in without full payment, not a
    consequence of money actually arriving."""
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
