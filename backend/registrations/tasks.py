import logging

from django.utils import timezone

from .models import Registration

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
