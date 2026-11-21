"""Read-only projection of an event's registration form for the public
register page. Models stay the source of truth; nothing here is stored and
nothing is priced (registrations/pricing.py owns that).
"""

from typing import TypedDict

from django.db.models import Prefetch

from events.models import ExtraChoice, Session, TicketType

from .services import sold_counts_for_event

SPEC_VERSION = 1


class FormField(TypedDict):
    key: str
    visible: bool
    required: bool


# `required` means "the form requires it" (what the page enforces today).
# These are enforced by the page only; the server accepts them blank. Step C
# must not loosen them. tests_form_spec.py keeps this set honest.
FORM_ONLY_REQUIRED = {("child", "last_name"), ("child", "birthdate")}


def _field(group: str, key: str, *, server_required: bool = False) -> FormField:
    required = server_required or (group, key) in FORM_ONLY_REQUIRED
    return {"key": key, "visible": True, "required": required}


# Single declaration of the person fields the form asks for. Keys are the
# submit payload's field names; server_required comes from the families
# serializers/models and is proven against submit by tests_form_spec.py.
PARENT_FIELDS: tuple[FormField, ...] = (
    _field("parent", "first_name", server_required=True),
    _field("parent", "last_name"),
    _field("parent", "relationship_type", server_required=True),
    _field("parent", "phone", server_required=True),
    _field("parent", "email"),
    _field("parent", "allergies"),
    _field("parent", "notes"),
    _field("parent", "health_consent_status"),
)
CHILD_FIELDS: tuple[FormField, ...] = (
    _field("child", "first_name", server_required=True),
    _field("child", "last_name"),
    _field("child", "birthdate"),
    _field("child", "allergies"),
    _field("child", "notes"),
    _field("child", "health_consent_status"),
)


def ticket_type_payload(ticket_type, *, sold_count, session_ids=None):
    """Public JSON shape of a TicketType, shared with validate_promo_code.
    ``available`` is a bool, never a count (no polling of sales on this public
    endpoint); ``sold_count`` comes from one bulk query to avoid an N+1."""
    payload = {
        "id": str(ticket_type.id),
        "name": ticket_type.name,
        "price": str(ticket_type.price),
        "applies_to": ticket_type.applies_to,
        "min_birthdate": (
            str(ticket_type.min_birthdate) if ticket_type.min_birthdate else None
        ),
        "max_birthdate": (
            str(ticket_type.max_birthdate) if ticket_type.max_birthdate else None
        ),
        "kind": ticket_type.kind,
        "requires_ticket_type_id": (
            str(ticket_type.requires_ticket_type_id)
            if ticket_type.requires_ticket_type_id
            else None
        ),
        "max_per_required": ticket_type.max_per_required,
        "available": ticket_type.capacity is None or sold_count < ticket_type.capacity,
    }
    if ticket_type.kind == TicketType.Kind.SESSION_BUNDLE:
        payload["session_ids"] = (session_ids or {}).get(str(ticket_type.id), [])
    return payload


def bundle_session_ids(ticket_types) -> dict[str, list[str]]:
    """Ticket type id -> session ids, for session-bundle types only (one
    query, none when there are no bundles)."""
    ids = [t.id for t in ticket_types if t.kind == TicketType.Kind.SESSION_BUNDLE]
    result: dict[str, list[str]] = {}
    if ids:
        rows = TicketType.sessions.through.objects.filter(tickettype_id__in=ids)
        for row in rows.order_by("session__start_time", "session_id"):
            result.setdefault(str(row.tickettype_id), []).append(str(row.session_id))
    return result


def sessions_payload(session_ids) -> list[dict]:
    """Session objects for the given ids; no query when empty."""
    if not session_ids:
        return []
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "start_time": s.start_time.isoformat(),
            "end_time": s.end_time.isoformat(),
        }
        for s in Session.objects.filter(id__in=set(session_ids)).order_by(
            "start_time", "name", "id"
        )
    ]


def build_form_spec(event) -> dict:
    sold_counts = sold_counts_for_event(event)
    active_ticket_types = event.ticket_types.filter(is_active=True)
    visible = list(
        active_ticket_types.filter(is_hidden=False).order_by("sort_order", "name")
    )
    bundle_ids = bundle_session_ids(visible)
    ticket_types = [
        ticket_type_payload(
            t, sold_count=sold_counts.get(str(t.id), 0), session_ids=bundle_ids
        )
        for t in visible
    ]
    # Lets the form show the promo box when every ticket type is code-only.
    has_hidden_ticket_types = active_ticket_types.filter(is_hidden=True).exists()
    extras = [
        {
            "id": str(extra.id),
            "name": extra.name,
            "price": str(extra.price),
            "session_id": str(extra.session_id) if extra.session_id else None,
            "per_attendee": extra.per_attendee,
            "applies_to": extra.applies_to,
            "requires_choice": extra.requires_choice,
            "required": extra.required,
            "default_selected": extra.default_selected,
            # Empty = offered to all. The form hides or disables the extra for
            # an attendee holding none of these; the server enforces the same.
            "ticket_type_ids": [str(t.id) for t in extra.ticket_types.all()],
            "ticket_type_names": [
                t.name
                for t in extra.ticket_types.all()
                if t.is_active and not t.is_hidden
            ],
            "choices": [
                {
                    "id": str(choice.id),
                    "label": choice.label,
                    "price_delta": str(choice.price_delta),
                }
                for choice in extra.choice_rows.all()
            ],
        }
        for extra in event.extras.filter(is_active=True)
        .order_by("sort_order", "name")
        .prefetch_related(
            Prefetch(
                "ticket_types",
                queryset=TicketType.objects.order_by("sort_order", "name"),
            ),
            Prefetch(
                "choice_rows",
                queryset=ExtraChoice.objects.filter(is_active=True).order_by(
                    "sort_order", "label"
                ),
            ),
        )
    ]
    referenced = {sid for ids in bundle_ids.values() for sid in ids}
    referenced.update(e["session_id"] for e in extras if e["session_id"])
    sessions = sessions_payload(referenced)

    return {
        "spec_version": SPEC_VERSION,
        "id": str(event.id),
        "name": event.name,
        "start_date": str(event.start_date),
        "end_date": str(event.end_date),
        "is_paid": event.is_paid,
        "price": str(event.price) if event.price is not None else None,
        "currency": "SEK",
        "header_image_url": event.header_image_url or None,
        "accent_color": event.accent_color or None,
        "ticket_types": ticket_types,
        "has_hidden_ticket_types": has_hidden_ticket_types,
        "extras": extras,
        "sessions": sessions,
        "fields": {
            "parent": [dict(f) for f in PARENT_FIELDS],
            "child": [dict(f) for f in CHILD_FIELDS],
        },
        "registration_window_status": event.registration_window_status,
        "registration_opens_at": (
            event.registration_opens_at.isoformat()
            if event.registration_opens_at
            else None
        ),
        "registration_closes_at": (
            event.registration_closes_at.isoformat()
            if event.registration_closes_at
            else None
        ),
    }
