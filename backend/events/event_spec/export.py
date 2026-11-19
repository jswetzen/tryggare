"""Event -> spec dict. Read-only."""

import re
import unicodedata

from django.utils import timezone

from ..models import Event
from .spec import (
    EventSection,
    EventSpec,
    ExtraChoiceSpec,
    ExtraSpec,
    PromoCodeSpec,
    SessionSpec,
    TicketTypeSpec,
)

_MAX_KEY = 64


def slugify_key(text: str) -> str:
    """'Child pass 0-12' -> 'child-pass-0-12'; never empty."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug[:_MAX_KEY].strip("-") or "item"


class _KeyAllocator:
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
    return None if value is None else timezone.localtime(value)


def export(event: Event) -> dict:
    """The event's configuration as a JSON-ready spec; ids and live state are left out."""
    session_keys: dict = {}
    allocator = _KeyAllocator()
    sessions = []
    for s in event.sessions.order_by("start_time", "name"):
        session_keys[s.id] = allocator.allocate(s.name)
        sessions.append(
            SessionSpec(
                key=session_keys[s.id],
                name=s.name,
                start_time=_dt(s.start_time),
                end_time=_dt(s.end_time),
                ticket_rule=s.ticket_rule,
                adults_not_checked_in=s.adults_not_checked_in,
            )
        )

    type_rows = list(
        event.ticket_types.prefetch_related("sessions").order_by("sort_order", "name")
    )
    allocator = _KeyAllocator()
    type_keys = {t.id: allocator.allocate(t.name) for t in type_rows}
    ticket_types = [
        TicketTypeSpec(
            key=type_keys[t.id],
            name=t.name,
            price=t.price,
            applies_to=t.applies_to,
            min_birthdate=t.min_birthdate,
            max_birthdate=t.max_birthdate,
            available_from=_dt(t.available_from),
            available_until=_dt(t.available_until),
            is_hidden=t.is_hidden,
            kind=t.kind,
            sessions=sorted(
                session_keys[s.id] for s in t.sessions.all() if s.id in session_keys
            ),
            capacity=t.capacity,
            requires_ticket_type=type_keys.get(t.requires_ticket_type_id),
            max_per_required=t.max_per_required,
            sort_order=t.sort_order,
            is_active=t.is_active,
        )
        for t in type_rows
    ]

    allocator = _KeyAllocator()
    extras = []
    for e in event.extras.prefetch_related("choice_rows").order_by(
        "sort_order", "name"
    ):
        choice_alloc = _KeyAllocator()
        extras.append(
            ExtraSpec(
                key=allocator.allocate(e.name),
                name=e.name,
                price=e.price,
                per_attendee=e.per_attendee,
                applies_to=e.applies_to,
                requires_choice=e.requires_choice,
                required=e.required,
                default_selected=e.default_selected,
                session=session_keys.get(e.session_id),
                sort_order=e.sort_order,
                is_active=e.is_active,
                choices=[
                    ExtraChoiceSpec(
                        key=choice_alloc.allocate(c.label),
                        label=c.label,
                        price_delta=c.price_delta,
                        sort_order=c.sort_order,
                        is_active=c.is_active,
                    )
                    for c in e.choice_rows.all()
                ],
            )
        )

    allocator = _KeyAllocator()
    promos = []
    for p in event.promo_codes.prefetch_related(
        "applies_to_ticket_types", "unlocks_ticket_types"
    ).order_by("code"):
        promos.append(
            PromoCodeSpec(
                key=allocator.allocate(p.code),
                code=p.code,
                discount_type=p.discount_type,
                discount_value=p.discount_value,
                applies_to_ticket_types=sorted(
                    type_keys[t.id]
                    for t in p.applies_to_ticket_types.all()
                    if t.id in type_keys
                ),
                unlocks_ticket_types=sorted(
                    type_keys[t.id]
                    for t in p.unlocks_ticket_types.all()
                    if t.id in type_keys
                ),
                max_uses=p.max_uses,
                valid_from=_dt(p.valid_from),
                valid_until=_dt(p.valid_until),
                is_active=p.is_active,
            )
        )

    spec = EventSpec(
        event_spec_version=1,
        event=EventSection(
            name=event.name,
            start_date=event.start_date,
            end_date=event.end_date,
            ticket_rule_default=event.ticket_rule_default,
            price=event.price,
            registration_opens_at=_dt(event.registration_opens_at),
            registration_closes_at=_dt(event.registration_closes_at),
            header_image_url=event.header_image_url,
            accent_color=event.accent_color,
        ),
        sessions=sessions,
        ticket_types=ticket_types,
        extras=extras,
        promo_codes=promos,
    )
    return spec.model_dump(mode="json")
