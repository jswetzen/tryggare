import logging

from django.utils import timezone

from .models import Payment, Registration
from .services import release_promo_code_use

logger = logging.getLogger(__name__)


def sweep_expired_registrations():
    """Hard-delete unverified registrations past their TTL.

    Only ever deletes rows this app created. Phase 1 always sets
    created_new_family=True (every submission materializes a brand-new
    family), so deleting the family cascades to its parents/children/
    tickets and to the Registration row itself. The False branch isn't
    reachable yet (nothing sets it), but is written defensively per the
    Track 1 plan: a future "attach to an existing matched family" flow must
    never have the sweep delete that pre-existing family — only the
    specific attendee/ticket rows this registration itself created.
    """
    from families.models import Attendee

    expired = Registration.objects.filter(
        status=Registration.Status.PENDING_VERIFICATION,
        expires_at__lt=timezone.now(),
    ).select_related("family")

    swept = 0
    for registration in expired:
        release_promo_code_use(registration)
        if registration.created_new_family:
            registration.family.delete()
        else:
            attendee_ids = list(
                registration.event_tickets.values_list("attendee_id", flat=True)
            ) + list(registration.session_tickets.values_list("attendee_id", flat=True))
            Attendee.objects.filter(id__in=attendee_ids).delete()
            registration.delete()
        swept += 1

    if swept:
        logger.info(
            "Registration expiry sweep: hard-deleted %d unverified registration(s)",
            swept,
        )


def sweep_unpaid_registrations():
    """Cancel (never hard-delete) pending_payment registrations past their
    payment TTL.

    Unlike pending_verification (never-real, spam-shaped) rows, these already
    passed email verification and represent a real family relationship —
    destroying their child data because payment was late has no upside and a
    real downside. Cancelling is reversible: staff can see the cancelled
    registration, contact the family, and manually re-open it if needed.
    """
    expired = Registration.objects.filter(
        status=Registration.Status.PENDING_PAYMENT,
        expires_at__lt=timezone.now(),
    ).select_related("payment")

    cancelled = 0
    for registration in expired:
        registration.status = Registration.Status.CANCELLED
        registration.save(update_fields=["status"])
        payment = getattr(registration, "payment", None)
        if payment is not None and payment.status == Payment.Status.PENDING:
            payment.status = Payment.Status.CANCELLED
            payment.save(update_fields=["status"])
        release_promo_code_use(registration)
        cancelled += 1

    if cancelled:
        logger.info(
            "Registration expiry sweep: cancelled %d unpaid pending_payment "
            "registration(s)",
            cancelled,
        )


def run_registration_sweeps():
    """Combined entry point for the scheduled job — runs both sweep passes."""
    sweep_expired_registrations()
    sweep_unpaid_registrations()
