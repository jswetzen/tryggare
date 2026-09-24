import logging
from datetime import timedelta

from django.utils import timezone

from .models import Payment, Registration, RegistrationIdempotencyKey
from .services import release_promo_code_use

logger = logging.getLogger(__name__)

# How long a RegistrationIdempotencyKey row is kept before the sweep below
# hard-deletes it. Deliberately much longer than STALE_RESERVATION_AGE
# (views.py, 60s — "has the owning request died") or RESEND_COOLDOWN
# (models.py-adjacent, 10min — "is a resend allowed yet"): this is a
# completely different question, "could a retry of the original POST still
# plausibly arrive". A guardian's tab, or a network-level retry sitting
# behind it, isn't realistically going to resend a week-old request, and
# every row this app cares about elsewhere on a similar timescale
# (REGISTRATION_TTL_HOURS, PAYMENT_TTL_DAYS in models.py) is already gone
# well before 7 days.
IDEMPOTENCY_KEY_TTL_DAYS = 7


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


def sweep_idempotency_keys():
    """Hard-delete RegistrationIdempotencyKey rows older than
    IDEMPOTENCY_KEY_TTL_DAYS.

    Added 2026-09-24 (P3, gate review) alongside the reclaim logic in
    views.py::_reserve_idempotency_key — that handles a reservation whose
    owning request died within seconds; this handles the row existing at
    all once it's simply too old to matter. These rows exist purely to make
    a retried submit POST safe to replay (see RegistrationIdempotencyKey's
    docstring in models.py); once a retry of the original request is no
    longer plausible, the row has no purpose left.

    Includes orphaned rows (``registration`` already NULL) on purpose —
    that FK is SET_NULL rather than CASCADE specifically so a row can
    outlive the Registration it cached a response for (see the field's own
    comment), and an orphaned row is exactly as done being useful as one
    still pointing at a live Registration once it's past the TTL. No
    separate query needed: the filter is on ``created_at`` alone, which
    every row has regardless of whether ``registration`` is still set.
    """
    cutoff = timezone.now() - timedelta(days=IDEMPOTENCY_KEY_TTL_DAYS)
    deleted, _unused = RegistrationIdempotencyKey.objects.filter(
        created_at__lt=cutoff
    ).delete()
    if deleted:
        logger.info(
            "Registration expiry sweep: hard-deleted %d stale idempotency key row(s)",
            deleted,
        )


def run_registration_sweeps():
    """Combined entry point for the scheduled job — runs all three sweep
    passes: unverified-registration hard-delete, unpaid-registration
    cancel, and stale-idempotency-key hard-delete."""
    sweep_expired_registrations()
    sweep_unpaid_registrations()
    sweep_idempotency_keys()
