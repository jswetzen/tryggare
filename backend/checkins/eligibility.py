from django.utils.translation import gettext as _

from events.models import Session
from families.models import Parent


def parent_checkin_gate_error(parent: Parent, session: Session) -> str | None:
    """Return an error message if `parent` may not check into `session`, else None.

    Single source of truth for the session's effective parent-check-in
    policy, used by both the check_in view action and the serializer's
    validate() so a stray POST to the generic CheckInRecord endpoint can't
    bypass it.
    """
    policy = session.effective_parent_checkin_policy

    if policy == Session.ParentCheckinPolicy.DISABLED:
        return _("Parent check-in is not enabled for this session")

    if policy == Session.ParentCheckinPolicy.TICKET_REQUIRED and not parent.has_ticket:
        return _("Parent does not have a ticket for this event")

    return None
