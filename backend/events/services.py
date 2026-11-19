"""Business logic that doesn't belong on a model or in a view/admin handler.

Extra-duplication (``duplicate_extra_to_event``) and whole-event copy
(``copy_event``) — the service-module pattern mirrors
``registrations/pricing.py`` and ``registrations/ticket_rules.py``.
"""

from datetime import date, datetime, timedelta

from django.db import transaction
from django.utils import timezone

from .models import Event, Extra, PromoCode, Session, TicketType


def duplicate_extra_to_event(
    extra: Extra, target_event: Event, session_map: dict | None = None
) -> Extra:
    """Deep-copy `extra` (and its ExtraChoice rows) onto `target_event`.

    Extras are deliberately event-owned, not a shared catalog (see the
    docstring on `Extra.cloned_from`) — this is how staff reuse one across
    events instead. `session` is dropped whenever `target_event` differs
    from the source event, since a Session belongs to exactly one event
    (`Session.event`) and the source event's session scoping can never
    carry over to a different event's calendar; staff re-picks it on the
    new copy afterward if needed.

    `session_map` (old session id -> new Session) is for callers that copy
    the sessions too: the extra then follows its session into `target_event`.
    """
    if session_map is not None:
        session = session_map.get(extra.session_id)
    else:
        session = extra.session if target_event == extra.event else None
    clone = Extra.objects.create(
        event=target_event,
        session=session,
        name=extra.name,
        price=extra.price,
        per_attendee=extra.per_attendee,
        applies_to=extra.applies_to,
        requires_choice=extra.requires_choice,
        required=extra.required,
        default_selected=extra.default_selected,
        sort_order=extra.sort_order,
        is_active=extra.is_active,
        cloned_from=extra,
    )
    for choice in extra.choice_rows.all():
        clone.choice_rows.create(
            label=choice.label,
            price_delta=choice.price_delta,
            sort_order=choice.sort_order,
            is_active=choice.is_active,
        )
    return clone


def _shift_datetime(value: datetime | None, delta: timedelta) -> datetime | None:
    """Move `value` by whole days on the Stockholm wall clock, so a 09:00
    session stays 09:00 when the shift crosses a DST change."""
    if value is None:
        return None
    tz = timezone.get_default_timezone()
    local = timezone.localtime(value, tz).replace(tzinfo=None)
    return (local + delta).replace(tzinfo=tz)


def _shift_date(value: date | None, delta: timedelta) -> date | None:
    return None if value is None else value + delta


@transaction.atomic
def copy_event(source: Event, *, name: str, start_date: date) -> Event:
    """Copy `source` with its configuration to a new event starting on
    `start_date`; every date and time moves by the same number of days.

    Copies the event settings, sessions, ticket types, extras (with
    choices) and promo codes, and remaps their references to the new rows.
    Registrations, attendees, tickets and check-ins are never copied, and
    `PromoCode.uses_count` starts over. Other apps' rows that point at the
    event (reports, import sources) are left with the source.
    """
    delta = start_date - source.start_date

    new_event = Event.objects.create(
        name=name,
        start_date=start_date,
        end_date=_shift_date(source.end_date, delta),
        ticket_rule_default=source.ticket_rule_default,
        price=source.price,
        registration_opens_at=_shift_datetime(source.registration_opens_at, delta),
        registration_closes_at=_shift_datetime(source.registration_closes_at, delta),
        header_image_url=source.header_image_url,
        accent_color=source.accent_color,
        cloned_from=source,
    )

    session_map: dict = {}
    for session in source.sessions.all():
        session_map[session.id] = Session.objects.create(
            event=new_event,
            name=session.name,
            start_time=_shift_datetime(session.start_time, delta),
            end_time=_shift_datetime(session.end_time, delta),
            is_active=session.is_active,
            ticket_rule=session.ticket_rule,
            adults_not_checked_in=session.adults_not_checked_in,
        )

    ticket_type_map: dict = {}
    source_types = list(source.ticket_types.prefetch_related("sessions"))
    for ticket_type in source_types:
        new_type = TicketType.objects.create(
            event=new_event,
            name=ticket_type.name,
            price=ticket_type.price,
            applies_to=ticket_type.applies_to,
            min_birthdate=_shift_date(ticket_type.min_birthdate, delta),
            max_birthdate=_shift_date(ticket_type.max_birthdate, delta),
            available_from=_shift_datetime(ticket_type.available_from, delta),
            available_until=_shift_datetime(ticket_type.available_until, delta),
            is_hidden=ticket_type.is_hidden,
            kind=ticket_type.kind,
            capacity=ticket_type.capacity,
            max_per_required=ticket_type.max_per_required,
            sort_order=ticket_type.sort_order,
            is_active=ticket_type.is_active,
        )
        new_type.sessions.set(session_map[s.id] for s in ticket_type.sessions.all())
        ticket_type_map[ticket_type.id] = new_type
    # Second pass: the required type may sort after the one that needs it.
    for ticket_type in source_types:
        if ticket_type.requires_ticket_type_id is not None:
            new_type = ticket_type_map[ticket_type.id]
            new_type.requires_ticket_type = ticket_type_map[
                ticket_type.requires_ticket_type_id
            ]
            new_type.save(update_fields=["requires_ticket_type"])

    for extra in source.extras.all():
        duplicate_extra_to_event(extra, new_event, session_map)

    for promo in source.promo_codes.prefetch_related(
        "applies_to_ticket_types", "unlocks_ticket_types"
    ):
        new_promo = PromoCode.objects.create(
            event=new_event,
            code=promo.code,
            discount_type=promo.discount_type,
            discount_value=promo.discount_value,
            max_uses=promo.max_uses,
            valid_from=_shift_datetime(promo.valid_from, delta),
            valid_until=_shift_datetime(promo.valid_until, delta),
            is_active=promo.is_active,
        )
        new_promo.applies_to_ticket_types.set(
            ticket_type_map[t.id] for t in promo.applies_to_ticket_types.all()
        )
        new_promo.unlocks_ticket_types.set(
            ticket_type_map[t.id] for t in promo.unlocks_ticket_types.all()
        )

    return new_event
