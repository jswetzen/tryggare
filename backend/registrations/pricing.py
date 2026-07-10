"""Single source of truth for what a Registration owes.

``calculate_total`` is the only place that decides a registration's price —
``verify_registration`` and ``registration_payment_status`` read it rather
than re-deriving paid-ness from ``Event.is_paid`` (see the case catalog's
"zero-priced ticket types and the Event.is_paid trap"). Nothing here ever
recomputes a *snapshotted* line (``price_at_registration`` on tickets/
extras, ``discount_amount`` on the registration) — those are frozen at
submission time and read verbatim.
"""

from decimal import Decimal

ZERO = Decimal("0")


def _itemized_ticket_total(registration, *, ticket_type_ids=None) -> Decimal:
    """Sum of EventTicket/SessionTicket price_at_registration snapshots,
    optionally restricted to a given set of ticket_type ids. Shared by
    calculate_total (unrestricted) and calculate_discount (restricted to
    a promo code's applies_to_ticket_types). A session_bundle ticket type
    produces one SessionTicket per covered session, all sharing one
    ticket_type — grouped by (attendee, ticket_type) here so the bundle's
    price is counted once, not once per session.
    """
    event_tickets = registration.event_tickets.all()
    session_tickets = registration.session_tickets.all()
    if ticket_type_ids is not None:
        event_tickets = event_tickets.filter(ticket_type_id__in=ticket_type_ids)
        session_tickets = session_tickets.filter(ticket_type_id__in=ticket_type_ids)

    event_ticket_total = sum(
        (ticket.price_at_registration or ZERO) for ticket in event_tickets
    )

    session_ticket_total = ZERO
    seen_bundles: set[tuple] = set()
    for ticket in session_tickets:
        bundle_key = (ticket.attendee_id, ticket.ticket_type_id)
        if ticket.ticket_type_id is not None:
            if bundle_key in seen_bundles:
                continue
            seen_bundles.add(bundle_key)
        session_ticket_total += ticket.price_at_registration or ZERO

    return event_ticket_total + session_ticket_total


def calculate_total(registration) -> Decimal:
    """Sum of everything this registration owes, net of any promo-code
    discount.

    Two modes, chosen per-event:

    - **Itemized** (the event has at least one active ``TicketType``):
      sums ticket lines (see ``_itemized_ticket_total``) plus
      ``RegistrationExtra`` snapshots x quantity.
    - **Flat fallback** (no ``TicketType`` configured for the event at
      all): the Phase 0-2 behavior, preserved exactly for events that
      haven't opted into itemization — a single flat ``Event.price``
      regardless of attendee count.

    Either way, ``registration.discount_amount`` (snapshotted once at
    submission by ``calculate_discount``, see below) is subtracted and the
    result floored at zero — a misconfigured or scoped discount can never
    manufacture a negative total.
    """
    event = registration.event

    if not event.ticket_types.filter(is_active=True).exists():
        raw_total = event.price or ZERO
    else:
        extras_total = sum(
            (extra.price_at_registration or ZERO) * extra.quantity
            for extra in registration.extras.all()
        )
        raw_total = _itemized_ticket_total(registration) + extras_total

    return max(raw_total - (registration.discount_amount or ZERO), ZERO)


def calculate_discount(registration, promo_code) -> Decimal:
    """Discount amount to snapshot as ``Registration.discount_amount`` at
    submission (P2 — computed once, never recomputed even if the code is
    edited afterwards). Must be called *before* ``discount_amount`` is set
    on the registration, since it reads the raw (undiscounted) total/lines
    to compute the base it discounts from.

    ``promo_code.applies_to_ticket_types`` empty = discount computed over
    the whole itemized total; non-empty = discount computed only over the
    matching ticket lines (extras untouched either way) — this is what
    keeps a "10% off children's tickets" code from silently eating the
    adult tickets too (case catalog §5.4(b)). The result is always capped
    at the base it was computed from, so a fixed discount larger than its
    (possibly scoped) base can never go negative.
    """
    ticket_type_ids = list(
        promo_code.applies_to_ticket_types.values_list("id", flat=True)
    )
    if ticket_type_ids:
        base = _itemized_ticket_total(registration, ticket_type_ids=ticket_type_ids)
    else:
        base = calculate_total(registration)  # discount_amount is still 0 here

    if promo_code.discount_type == promo_code.DiscountType.PERCENT:
        discount = base * promo_code.discount_value / Decimal("100")
    else:
        discount = promo_code.discount_value

    return min(discount, base)
