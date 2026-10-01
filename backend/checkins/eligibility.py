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

    # A guardian-only adult (Registration.guardian_only_parents) holds no
    # ticket, so the two checks above find nothing to block on -- but they
    # must not be able to check in through a registration that a ticketed
    # attendee would be refused on. Same message, same rule: blocked unless
    # at least one of their registrations for this event is CONFIRMED.
    guardian_statuses = _guardian_only_statuses(attendee, session)
    if guardian_statuses and Registration.Status.CONFIRMED not in guardian_statuses:
        return _("Registration is not yet confirmed")

    return None


def _guardian_only_statuses(attendee: Attendee, session: Session) -> set[str]:
    """Statuses of the registrations for ``session``'s event on which
    ``attendee`` is a stored guardian-only adult (empty for everyone else,
    including every staff-created adult). Works from a base ``Attendee`` or a
    ``Parent``: the reverse relation lives on ``Parent`` but is keyed by the
    shared primary key.
    """
    return set(
        Registration.objects.filter(
            event_id=session.event_id, guardian_only_parents__pk=attendee.pk
        ).values_list("status", flat=True)
    )


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
        # A stored guardian-only adult on a CONFIRMED registration for this
        # event satisfies the policy without a ticket (owner decision
        # d9245e21: they are responsible for the children but not attending,
        # so "has a ticket" is the wrong question for them). Deliberately
        # keyed on the stored marker, not on "has no ticket", so an ordinary
        # adult whose ticket went missing is still refused; and only for
        # TICKET_REQUIRED -- DISABLED above still disables for everyone.
        if Registration.Status.CONFIRMED in _guardian_only_statuses(parent, session):
            return None
        return _("Parent does not have a ticket for this event")

    return None
