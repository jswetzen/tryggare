from django.utils.translation import gettext as _

from events.models import Session
from families.models import Attendee, Parent
from registrations.models import Registration


def registration_checkin_gate_error(attendee: Attendee, session: Session) -> str | None:
    """Return an error message if a pending self-serve registration blocks
    `attendee` from checking into `session`, else None.

    New gate, not an extension of an existing one: before self-serve
    registration existed there was no ticket-validity check for children at
    check-in at all (the old `requires_ticket` was pure display metadata). A ticket
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
    """Return an error message if the adult ``parent`` may not check into
    ``session``, else None.

    Single source of truth for adult check-in, used by both the check_in view
    action and the serializer's validate() so a stray POST to the generic
    CheckInRecord endpoint can't bypass it. Driven by the session's ticket
    rule (``Session.effective_ticket_rule``) and ``adults_not_checked_in``;
    the old ``parent_checkin_policy`` is no longer read.
    """
    # The checkbox beats everything, guardians included: nobody is checked in
    # as an adult here, whatever they hold.
    if session.adults_not_checked_in:
        return _("Parent check-in is not enabled for this session")

    if session.adults_need_ticket and not parent.has_ticket_for(session):
        # A stored guardian-only adult on a CONFIRMED registration for this
        # event satisfies the rule without a ticket (owner decision
        # d9245e21: they are responsible for the children but not attending,
        # so "has a ticket" is the wrong question for them). Deliberately
        # keyed on the stored marker, not on "has no ticket", so an ordinary
        # adult whose ticket went missing is still refused; and only for the
        # rule that asks adults for a ticket -- the checkbox above still
        # excludes everyone.
        if Registration.Status.CONFIRMED in _guardian_only_statuses(parent, session):
            return None
        return _("Parent does not have a ticket for this event")

    return None


def child_ticket_gate_error(child: Attendee, session: Session) -> str | None:
    """Return an error message if ``child`` needs a ticket for ``session`` and
    has none, else None.

    Fires when the session's effective rule is ``children`` or ``all``. The
    ticket must cover THIS session (``has_ticket_for``): a ticket for another
    event, or a SessionTicket for another session, does not count. Staff
    assigning a ticket at the door creates it with ``registration=None``, so
    the gate passes right after assignment; whether a self-serve registration
    is confirmed is ``registration_checkin_gate_error``'s question, not this
    one's.
    """
    if session.children_need_ticket and not child.has_ticket_for(session):
        return _("Child does not have a ticket for this session")
    return None
