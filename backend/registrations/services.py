"""Plain-ORM payment-state logic (matches families/services.py's convention:
no DRF coupling — callers own validation, error handling, and audit logging).
"""

from django.db import transaction
from django.utils import timezone

from .emails import send_confirmation_email
from .models import Payment, Registration


class InvalidPaymentTransition(Exception):
    """Raised when mark_payment_paid() is asked to pay a Payment/Registration
    that isn't in a payable state. Callers (the admin actions) catch this
    per-row rather than letting one bad row abort a bulk action."""


def mark_payment_paid(payment: Payment, *, method: str, marked_by) -> None:
    """The only gate between "money received" and check-in eligibility
    flipping to CONFIRMED — must never silently no-op on a mismatched state."""
    if payment.status != Payment.Status.PENDING:
        raise InvalidPaymentTransition(f"Payment is already {payment.status}")
    if payment.registration.status != Registration.Status.PENDING_PAYMENT:
        raise InvalidPaymentTransition(
            f"Registration is {payment.registration.status}, not pending_payment"
        )

    with transaction.atomic():
        payment.status = Payment.Status.PAID
        payment.method = method
        payment.paid_at = timezone.now()
        payment.marked_by = marked_by
        payment.save(update_fields=["status", "method", "paid_at", "marked_by"])

        registration = payment.registration
        registration.status = Registration.Status.CONFIRMED
        registration.save(update_fields=["status"])

    send_confirmation_email(registration)
