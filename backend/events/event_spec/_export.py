"""Event -> spec dict. Read-only."""

import re
import unicodedata

from django.utils import timezone
from django.utils.translation import gettext as _

from ..models import Event
from ._issues import NOUNS, SpecError, issue

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


def _key_of(keys: dict, target, holder_kind: str, holder, target_kind: str):
    """The key of ``target`` (None passes through); a row of another event has none."""
    if target is None:
        return None
    if target.id not in keys:
        name = getattr(holder, "name", None) or holder.code
        raise SpecError(
            [
                issue(
                    "event",
                    "cross_event_reference",
                    _(
                        "The %(kind)s '%(name)s' refers to the %(target)s '%(other)s', which belongs to another event."
                    )
                    % {
                        "kind": NOUNS[holder_kind],
                        "name": name,
                        "target": NOUNS[target_kind],
                        "other": getattr(target, "name", ""),
                    },
                )
            ]
        )
    return keys[target.id]


def keyed_rows(event: Event) -> dict:
    """The event's rows in export order with their derived keys.

    ``{"sessions": [(key, obj)], "ticket_types": [...], "extras": [...],
    "choices": [(extra_key, key, obj)], "promo_codes": [...]}``. Ties in the
    ordering break on id so derived keys do not swap between runs.
    """
    allocator = KeyAllocator()
    sessions = [
        (allocator.allocate(s.name), s)
        for s in event.sessions.order_by("start_time", "name", "id")
    ]
    allocator = KeyAllocator()
    ticket_types = [
        (allocator.allocate(t.name), t)
        for t in event.ticket_types.select_related("requires_ticket_type")
        .prefetch_related("sessions")
        .order_by("sort_order", "name", "id")
    ]
    allocator = KeyAllocator()
    extras, choices = [], []
    for e in event.extras.select_related("session").order_by(
        "sort_order", "name", "id"
    ):
        extra_key = allocator.allocate(e.name)
        extras.append((extra_key, e))
        choice_alloc = KeyAllocator()
        for c in e.choice_rows.order_by("sort_order", "label", "id"):
            choices.append((extra_key, choice_alloc.allocate(c.label), c))
    allocator = KeyAllocator()
    promos = [
        (allocator.allocate(p.code), p)
        for p in event.promo_codes.prefetch_related(
            "applies_to_ticket_types", "unlocks_ticket_types"
        ).order_by("code", "id")
    ]
    return {
        "sessions": sessions,
        "ticket_types": ticket_types,
        "extras": extras,
        "choices": choices,
        "promo_codes": promos,
    }


def export(event: Event) -> dict:
    """The event's configuration as a JSON-ready spec; ids and live state are left out.

    Built as plain dicts, not through the spec models, so data the models allow
    but validation rejects (a negative price) still exports.
    """
    rows = keyed_rows(event)
    session_keys = {s.id: key for key, s in rows["sessions"]}
    type_keys = {t.id: key for key, t in rows["ticket_types"]}

    sessions = [
        {
            "key": key,
            "name": s.name,
            "start_time": _dt(s.start_time),
            "end_time": _dt(s.end_time),
            "ticket_rule": s.ticket_rule,
            "adults_not_checked_in": s.adults_not_checked_in,
        }
        for key, s in rows["sessions"]
    ]
    ticket_types = [
        {
            "key": key,
            "name": t.name,
            "price": _money(t.price),
            "applies_to": t.applies_to,
            "min_birthdate": _d(t.min_birthdate),
            "max_birthdate": _d(t.max_birthdate),
            "available_from": _dt(t.available_from),
            "available_until": _dt(t.available_until),
            "is_hidden": t.is_hidden,
            "kind": t.kind,
            "sessions": sorted(
                _key_of(session_keys, s, "ticket_types", t, "sessions")
                for s in t.sessions.all()
            ),
            "capacity": t.capacity,
            "requires_ticket_type": _key_of(
                type_keys, t.requires_ticket_type, "ticket_types", t, "ticket_types"
            ),
            "max_per_required": t.max_per_required,
            "sort_order": t.sort_order,
            "is_active": t.is_active,
        }
        for key, t in rows["ticket_types"]
    ]
    extras = []
    for key, e in rows["extras"]:
        extras.append(
            {
                "key": key,
                "name": e.name,
                "price": _money(e.price),
                "per_attendee": e.per_attendee,
                "applies_to": e.applies_to,
                "requires_choice": e.requires_choice,
                "required": e.required,
                "default_selected": e.default_selected,
                "session": _key_of(session_keys, e.session, "extras", e, "sessions"),
                "sort_order": e.sort_order,
                "is_active": e.is_active,
                "choices": [
                    {
                        "key": ckey,
                        "label": c.label,
                        "price_delta": _money(c.price_delta),
                        "sort_order": c.sort_order,
                        "is_active": c.is_active,
                    }
                    for extra_key, ckey, c in rows["choices"]
                    if extra_key == key
                ],
            }
        )
    promos = [
        {
            "key": key,
            "code": p.code,
            "discount_type": p.discount_type,
            "discount_value": _money(p.discount_value),
            "applies_to_ticket_types": sorted(
                _key_of(type_keys, t, "promo_codes", p, "ticket_types")
                for t in p.applies_to_ticket_types.all()
            ),
            "unlocks_ticket_types": sorted(
                _key_of(type_keys, t, "promo_codes", p, "ticket_types")
                for t in p.unlocks_ticket_types.all()
            ),
            "max_uses": p.max_uses,
            "valid_from": _dt(p.valid_from),
            "valid_until": _dt(p.valid_until),
            "is_active": p.is_active,
        }
        for key, p in rows["promo_codes"]
    ]
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
