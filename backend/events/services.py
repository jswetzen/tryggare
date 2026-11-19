"""Business logic that doesn't belong on a model or in a view/admin handler.

Extra-duplication (``duplicate_extra_to_event``) and whole-event copy
(``copy_event``) — the service-module pattern mirrors
``registrations/pricing.py`` and ``registrations/ticket_rules.py``.
"""

from datetime import date, datetime, timedelta

from django.db import transaction
from django.utils import timezone

from .models import Event, Extra

# Copying (and spec apply) creates rows in all five models, not just events.
SPEC_MODELS = (
    "event",
    "session",
    "tickettype",
    "extra",
    "extrachoice",
    "promocode",
)
COPY_PERMISSIONS = tuple(f"events.add_{m}" for m in SPEC_MODELS)
VIEW_PERMISSIONS = tuple(f"events.view_{m}" for m in SPEC_MODELS)
# Replacing a setup deletes rows too.
REPLACE_PERMISSIONS = tuple(
    f"events.{verb}_{m}" for m in SPEC_MODELS for verb in ("add", "change", "delete")
)


def can_copy_events(user) -> bool:
    return all(user.has_perm(p) for p in COPY_PERMISSIONS)


def duplicate_extra_to_event(extra: Extra, target_event: Event) -> Extra:
    """Deep-copy `extra` (and its ExtraChoice rows) onto `target_event`.

    Extras are deliberately event-owned, not a shared catalog (see the
    docstring on `Extra.cloned_from`) — this is how staff reuse one across
    events instead. `session` is dropped whenever `target_event` differs
    from the source event, since a Session belongs to exactly one event
    (`Session.event`) and the source event's session scoping can never
    carry over to a different event's calendar; staff re-picks it on the
    new copy afterward if needed.
    """
    clone = Extra.objects.create(
        event=target_event,
        session=extra.session if target_event == extra.event else None,
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
    # A nonexistent or ambiguous local time resolves with fold=0 (the
    # earlier offset); never raises.
    tz = timezone.get_default_timezone()
    local = timezone.localtime(value, tz).replace(tzinfo=None)
    return (local + delta).replace(tzinfo=tz)


def _years_before(anchor: date, years: int) -> date:
    """`anchor` moved back `years`; for 29 February, the nearest earlier leap
    year, since only a 29 February satisfies the age-window rule there."""
    for shift in range(years, years + 8):
        try:
            return anchor.replace(year=anchor.year - shift)
        except ValueError:
            continue
    raise AssertionError("no valid year within 8 of the requested shift")


def _shift_birthdate_bound(
    bound: date | None, source_start: date, new_start: date, *, offset_days: int
) -> date | None:
    """Shift a TicketType age bound.

    A bound on the anniversary `TicketType._clean_age_window` requires
    (`offset_days` 0 for max, 1 for min) is rebuilt from the new start date
    with the same whole-year age; a plain day shift would drift off it
    whenever the delta is not a multiple of a year. Other bounds shift by
    the plain delta.
    """
    if bound is None:
        return None
    one = timedelta(days=offset_days)
    anchor = source_start + one
    if (bound.month, bound.day) == (anchor.month, anchor.day):
        return _years_before(new_start + one, anchor.year - bound.year)
    return bound + (new_start - source_start)


def _shift_iso(value: str | None, delta: timedelta) -> str | None:
    # Export gives fixed offsets; shift on the Stockholm wall clock instead.
    if value is None:
        return None
    return _shift_datetime(datetime.fromisoformat(value), delta).isoformat()


def _shift_spec(spec: dict, delta: timedelta, name: str, start_date: date) -> dict:
    """Move every date and time in an exported spec by `delta`."""
    source_start = date.fromisoformat(spec["event"]["start_date"])
    event = spec["event"]
    event.update(
        name=name,
        start_date=start_date.isoformat(),
        end_date=(date.fromisoformat(event["end_date"]) + delta).isoformat(),
    )
    for field in ("registration_opens_at", "registration_closes_at"):
        event[field] = _shift_iso(event[field], delta)
    # Apply refuses an open window; a copy whose window is already open or
    # past ships with self-serve off rather than being opened by the spec.
    now = timezone.now()
    stamps = [
        datetime.fromisoformat(event[f])
        for f in ("registration_opens_at", "registration_closes_at")
        if event[f] is not None
    ]
    if any(t <= now for t in stamps) or (
        event["registration_opens_at"] is None and stamps
    ):
        event["registration_opens_at"] = event["registration_closes_at"] = None
    for session in spec["sessions"]:
        for field in ("start_time", "end_time"):
            session[field] = _shift_iso(session[field], delta)
    for ticket_type in spec["ticket_types"]:
        for field in ("available_from", "available_until"):
            ticket_type[field] = _shift_iso(ticket_type[field], delta)
        for field, offset in (("min_birthdate", 1), ("max_birthdate", 0)):
            bound = ticket_type[field]
            if bound is not None:
                ticket_type[field] = _shift_birthdate_bound(
                    date.fromisoformat(bound),
                    source_start,
                    start_date,
                    offset_days=offset,
                ).isoformat()
    for promo in spec["promo_codes"]:
        for field in ("valid_from", "valid_until"):
            promo[field] = _shift_iso(promo[field], delta)
    return spec


def copy_event(source: Event, *, name: str, start_date: date) -> Event:
    """Copy `source` to a new event; see `copy_event_with_warnings`."""
    return copy_event_with_warnings(source, name=name, start_date=start_date)[0]


@transaction.atomic
def copy_event_with_warnings(
    source: Event, *, name: str, start_date: date
) -> tuple[Event, list[dict]]:
    """Copy `source` with its configuration to a new event starting on
    `start_date`; every date and time moves by the same number of days.

    Exports the source as an event spec, shifts it and applies it, so the
    copy follows the spec's rules. Copies the event settings, sessions,
    ticket types, extras (with choices) and promo codes, and remaps their
    references. Registrations, attendees, tickets and check-ins are never
    copied, `PromoCode.uses_count` starts over and sessions start inactive.
    A registration window that would be open or past after the shift is
    dropped (self-serve off). Raises `event_spec.SpecError` for a source that
    refers to another event's rows and for a setup the spec rules refuse,
    including one over the spec's row caps (`MAX_ROWS`).
    Returns the new event and the spec warnings.
    """
    # Imported here: event_spec imports this module.
    from .event_spec import apply, export
    from .event_spec._export import keyed_rows

    delta = start_date - source.start_date
    spec = _shift_spec(export(source), delta, name, start_date)
    new_event, _diff, warnings = apply(spec)

    # Copy history is not part of the spec; both rows are matched by key.
    Event.objects.filter(pk=new_event.pk).update(cloned_from=source)
    new_event.cloned_from = source
    new_extras = dict(keyed_rows(new_event)["extras"])
    for key, old_extra in keyed_rows(source)["extras"]:
        Extra.objects.filter(pk=new_extras[key].pk).update(cloned_from=old_extra)
    return new_event, warnings
