"""Event -> spec dict. Read-only."""

import re
import unicodedata

from django.utils import timezone

from ..models import Event
from ..services import _check_references_stay_in_event

_MAX_KEY = 64


def slugify_key(text: str) -> str:
    """'Child pass 0-12' -> 'child-pass-0-12'; never empty."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug[:_MAX_KEY].strip("-") or "item"


class KeyAllocator:
    """Slugs unique within one kind: 'adult', 'adult-2', 'adult-3'."""

    def __init__(self):
        self._taken: set[str] = set()

    def allocate(self, text: str) -> str:
        base = slugify_key(text)
        key, n = base, 2
        while key in self._taken:
            suffix = f"-{n}"
            key = base[: _MAX_KEY - len(suffix)].strip("-") + suffix
            n += 1
        self._taken.add(key)
        return key


def _dt(value):
    if value is None:
        return None
    return timezone.localtime(value, timezone.get_default_timezone()).isoformat()


def _d(value):
    return None if value is None else value.isoformat()


def _money(value):
    return None if value is None else str(value)


def export(event: Event) -> dict:
    """The event's configuration as a JSON-ready spec; ids and live state are left out.

    Built as plain dicts, not through the spec models, so data the models allow
    but validation rejects (a negative price) still exports. Ties in the ordering
    break on id so derived keys do not swap between runs.
    """
    _check_references_stay_in_event(event)

    session_keys: dict = {}
    allocator = KeyAllocator()
    sessions = []
    for s in event.sessions.order_by("start_time", "name", "id"):
        session_keys[s.id] = allocator.allocate(s.name)
        sessions.append(
            {
                "key": session_keys[s.id],
                "name": s.name,
                "start_time": _dt(s.start_time),
                "end_time": _dt(s.end_time),
                "ticket_rule": s.ticket_rule,
                "adults_not_checked_in": s.adults_not_checked_in,
            }
        )

    type_rows = list(
        event.ticket_types.prefetch_related("sessions").order_by(
            "sort_order", "name", "id"
        )
    )
    allocator = KeyAllocator()
    type_keys = {t.id: allocator.allocate(t.name) for t in type_rows}
    ticket_types = [
        {
            "key": type_keys[t.id],
            "name": t.name,
            "price": _money(t.price),
            "applies_to": t.applies_to,
            "min_birthdate": _d(t.min_birthdate),
            "max_birthdate": _d(t.max_birthdate),
            "available_from": _dt(t.available_from),
            "available_until": _dt(t.available_until),
            "is_hidden": t.is_hidden,
            "kind": t.kind,
            "sessions": sorted(session_keys[s.id] for s in t.sessions.all()),
            "capacity": t.capacity,
            "requires_ticket_type": type_keys.get(t.requires_ticket_type_id),
            "max_per_required": t.max_per_required,
            "sort_order": t.sort_order,
            "is_active": t.is_active,
        }
        for t in type_rows
    ]

    allocator = KeyAllocator()
    extras = []
    for e in event.extras.order_by("sort_order", "name", "id"):
        choice_alloc = KeyAllocator()
        extras.append(
            {
                "key": allocator.allocate(e.name),
                "name": e.name,
                "price": _money(e.price),
                "per_attendee": e.per_attendee,
                "applies_to": e.applies_to,
                "requires_choice": e.requires_choice,
                "required": e.required,
                "default_selected": e.default_selected,
                "session": session_keys.get(e.session_id),
                "sort_order": e.sort_order,
                "is_active": e.is_active,
                "choices": [
                    {
                        "key": choice_alloc.allocate(c.label),
                        "label": c.label,
                        "price_delta": _money(c.price_delta),
                        "sort_order": c.sort_order,
                        "is_active": c.is_active,
                    }
                    for c in e.choice_rows.order_by("sort_order", "label", "id")
                ],
            }
        )

    allocator = KeyAllocator()
    promos = []
    for p in event.promo_codes.prefetch_related(
        "applies_to_ticket_types", "unlocks_ticket_types"
    ).order_by("code", "id"):
        promos.append(
            {
                "key": allocator.allocate(p.code),
                "code": p.code,
                "discount_type": p.discount_type,
                "discount_value": _money(p.discount_value),
                "applies_to_ticket_types": sorted(
                    type_keys[t.id] for t in p.applies_to_ticket_types.all()
                ),
                "unlocks_ticket_types": sorted(
                    type_keys[t.id] for t in p.unlocks_ticket_types.all()
                ),
                "max_uses": p.max_uses,
                "valid_from": _dt(p.valid_from),
                "valid_until": _dt(p.valid_until),
                "is_active": p.is_active,
            }
        )

    return {
        "event_spec_version": 1,
        "event": {
            "name": event.name,
            "start_date": _d(event.start_date),
            "end_date": _d(event.end_date),
            "ticket_rule_default": event.ticket_rule_default,
            "price": _money(event.price),
            "registration_opens_at": _dt(event.registration_opens_at),
            "registration_closes_at": _dt(event.registration_closes_at),
            "header_image_url": event.header_image_url,
            "accent_color": event.accent_color,
        },
        "sessions": sessions,
        "ticket_types": ticket_types,
        "extras": extras,
        "promo_codes": promos,
    }
