"""Single source of truth for what a Registration owes.

``calculate_total`` is the only place that decides a registration's price —
``verify_registration`` and ``registration_payment_status`` read it rather
than re-deriving paid-ness from ``Event.is_paid`` (see the case catalog's
"zero-priced ticket types and the Event.is_paid trap"). Nothing here ever
recomputes a *snapshotted* line (``price_at_registration`` on tickets/
extras) — those are frozen at submission time and read verbatim.
"""

from decimal import Decimal

ZERO = Decimal("0")


def calculate_total(registration) -> Decimal:
    """Sum of everything this registration owes.

    Two modes, chosen per-event:

    - **Itemized** (the event has at least one active ``TicketType``):
      sums ``EventTicket``/``SessionTicket`` ``price_at_registration``
      snapshots plus ``RegistrationExtra`` snapshots × quantity. A
      ``session_bundle`` ticket type produces one ``SessionTicket`` per
      covered session, all sharing one ``ticket_type`` — grouped by
      ``(attendee, ticket_type)`` here so the bundle's price is counted
      once, not once per session.
    - **Flat fallback** (no ``TicketType`` configured for the event at
      all): the Phase 0-2 behavior, preserved exactly for events that
      haven't opted into itemization — a single flat ``Event.price``
      regardless of attendee count.
    """
    event = registration.event

    if not event.ticket_types.filter(is_active=True).exists():
        return event.price or ZERO

    event_ticket_total = sum(
        (ticket.price_at_registration or ZERO)
        for ticket in registration.event_tickets.all()
    )

    session_ticket_total = ZERO
    seen_bundles: set[tuple] = set()
    for ticket in registration.session_tickets.all():
        bundle_key = (ticket.attendee_id, ticket.ticket_type_id)
        if ticket.ticket_type_id is not None:
            if bundle_key in seen_bundles:
                continue
            seen_bundles.add(bundle_key)
        session_ticket_total += ticket.price_at_registration or ZERO

    extras_total = sum(
        (extra.price_at_registration or ZERO) * extra.quantity
        for extra in registration.extras.all()
    )

    return event_ticket_total + session_ticket_total + extras_total
