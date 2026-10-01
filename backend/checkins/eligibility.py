from django.utils.translation import gettext as _

from events.models import Session
from families.models import Attendee, Parent
from registrations.models import Registration


def unconfirmed_registration_blocks(
    event_tickets, session_tickets, guardian_registrations
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    """The ONE statement of "this person's registration is not confirmed".

    Both ``registration_checkin_gate_error`` (the door's refusal) and the
    family serializers' ``unconfirmed_registration`` marker (the check-in
    screen's warning) call this, so what the screen marks and what the server
    refuses cannot drift apart. It takes already-loaded rows so each caller
    keeps its own query strategy: the gate asks about one session and loads
    just those rows; the serializers work from the family list's prefetch and
    so add no query per person.

    Arguments:
        event_tickets: the person's ``EventTicket`` rows, ``registration``
            loaded (``select_related``) so reading it costs no query.
        session_tickets: the person's ``SessionTicket`` rows, likewise.
        guardian_registrations: the ``Registration`` rows, of ANY status, on
            which the person is a stored guardian-only adult.

    Returns ``(by_event, by_session)``: event id -> ids of the registrations
    that block the person on every session of that event, and session id ->
    ids of the registrations that block them on that exact session. All ids
    are strings. Returning the blocking registrations (not just a flag) is
    what lets the serializers tell "blocked by the registration the unpaid
    banner already shows" from "blocked by one nothing else surfaces".

    Rules (unchanged from the gate they were lifted out of): a ticket whose
    ``registration`` FK is set counts only once that registration is
    CONFIRMED -- staff-created tickets (``registration=None``) are never
    blocked; and a guardian-only adult holds no ticket, so they are blocked on
    an event unless at least one of their guardian-only registrations for it
    is CONFIRMED.
    """
    confirmed = Registration.Status.CONFIRMED
    by_event: dict[str, set[str]] = {}
    by_session: dict[str, set[str]] = {}

    for ticket in event_tickets:
        if ticket.registration_id and ticket.registration.status != confirmed:
            by_event.setdefault(str(ticket.event_id), set()).add(
                str(ticket.registration_id)
            )

    for ticket in session_tickets:
        if ticket.registration_id and ticket.registration.status != confirmed:
            by_session.setdefault(str(ticket.session_id), set()).add(
                str(ticket.registration_id)
            )

    guardian_by_event: dict[str, list[Registration]] = {}
    for registration in guardian_registrations:
        guardian_by_event.setdefault(str(registration.event_id), []).append(
            registration
        )
    for event_id, registrations in guardian_by_event.items():
        if not any(r.status == confirmed for r in registrations):
            by_event.setdefault(event_id, set()).update(
                str(r.id) for r in registrations
            )

    return by_event, by_session


def registration_checkin_gate_error(attendee: Attendee, session: Session) -> str | None:
    """Return an error message if a pending self-serve registration blocks
    `attendee` from checking into `session`, else None.

    New gate, not an extension of an existing one: before self-serve
    registration existed there was no ticket-validity check for children at
    check-in at all (the former Session.requires_ticket was pure display metadata). A ticket
    whose `registration` FK is set only counts toward eligibility once
    `registration.status == CONFIRMED` — staff-created tickets always have
    `registration=None` and are entirely unaffected. `EventTicket`/
    `SessionTicket` are each unique per (attendee, event)/(attendee,
    session), so there's at most one relevant ticket to check per call.

    The decision itself is ``unconfirmed_registration_blocks`` (shared with
    the serializers that mark the same people on the check-in screen); this
    function only loads the rows that matter for ``session`` and asks it.
    A guardian-only adult (Registration.guardian_only_parents) holds no
    ticket, so the ticket rows find nothing to block on -- but they must not
    be able to check in through a registration that a ticketed attendee would
    be refused on. Same message, same rule: blocked unless at least one of
    their registrations for this event is CONFIRMED.
    """
    by_event, by_session = unconfirmed_registration_blocks(
        attendee.event_tickets.filter(event=session.event).select_related(
            "registration"
        ),
        attendee.session_tickets.filter(session=session).select_related("registration"),
        Registration.objects.filter(
            event_id=session.event_id, guardian_only_parents__pk=attendee.pk
        ),
    )
    if str(session.event_id) in by_event or str(session.pk) in by_session:
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
    the former ``parent_checkin_policy`` column no longer exists.
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
