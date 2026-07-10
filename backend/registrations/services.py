"""Plain-ORM payment-state logic (matches families/services.py's convention:
no DRF coupling — callers own validation, error handling, and audit logging).
"""

from decimal import Decimal

from django.db import transaction

from .emails import send_confirmation_email
from .models import Payment, PaymentEvent, Registration


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
    exactly). Confirmation email is sent outside the transaction."""
    if amount <= Decimal("0"):
        raise ValueError("PaymentEvent amount must be positive")
    if payment.status == Payment.Status.CANCELLED:
        raise InvalidPaymentTransition("Payment is cancelled")

    should_send_confirmation = False
    with transaction.atomic():
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
