from django.utils.translation import gettext as _

from events.models import Session
from families.models import Attendee, Parent
from registrations.models import Registration


def registration_checkin_gate_error(attendee: Attendee, session: Session) -> str | None:
    """Return an error message if a pending self-serve registration blocks
    `attendee` from checking into `session`, else None.

    New gate, not an extension of an existing one: before self-serve
    registration existed there was no ticket-validity check for children at
    check-in at all (`requires_ticket` was pure display metadata). A ticket
    whose `registration` FK is set only counts toward eligibility once
    `registration.status == CONFIRMED` — staff-created tickets always have
    `registration=None` and are entirely unaffected. `EventTicket`/
    `SessionTicket` are each unique per (attendee, event)/(attendee,
    session), so there's at most one relevant ticket to check per call.
    """
    event_ticket = (
        attendee.event_tickets.filter(event=session.event)
        .select_related("registration")
        .first()
    )
    if (
        event_ticket
        and event_ticket.registration_id
        and event_ticket.registration.status != Registration.Status.CONFIRMED
    ):
        return _("Registration is not yet confirmed")

    session_ticket = (
        attendee.session_tickets.filter(session=session)
        .select_related("registration")
        .first()
    )
    if (
        session_ticket
        and session_ticket.registration_id
        and session_ticket.registration.status != Registration.Status.CONFIRMED
    ):
        return _("Registration is not yet confirmed")

    return None


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
