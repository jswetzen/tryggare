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


def _field(key: str, *, required: bool = False) -> FormField:
    return {"key": key, "visible": True, "required": required}


# Single declaration of the person fields the form asks for. `required` is the
# SERVER rule (families serializers + models); tests_form_spec.py proves it
# against the submit endpoint. Keys are the submit payload's field names.
PARENT_FIELDS: tuple[FormField, ...] = (
    _field("first_name", required=True),
    _field("last_name"),
    _field("phone", required=True),
    _field("email"),
    _field("relationship_type", required=True),
    _field("allergies"),
    _field("notes"),
    _field("health_consent_status"),
)
# birthdate is only enforced when the child's ticket type has an age band
# (views._child_ticket_age_error); last_name is blank=True on the model.
CHILD_FIELDS: tuple[FormField, ...] = (
    _field("first_name", required=True),
    _field("last_name"),
    _field("birthdate"),
    _field("allergies"),
    _field("notes"),
    _field("health_consent_status"),
)


def _ticket_type_payload(ticket_type, *, sold_count):
    """Public JSON shape of a TicketType, shared with validate_promo_code.

    ``available`` is a bool on purpose: sold counts or "3 left" would let
    anyone poll registration velocity on this unauthenticated endpoint.
    ``sold_count`` comes from one bulk query (sold_counts_for_event) to
    avoid an N+1 per ticket type.
    """
    return {
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


def _sessions_payload(visible_ticket_types, extras):
    """Sessions the form refers to: extras' session_id and the sessions of
    visible session-bundle ticket types. Returns (sessions, bundle_map).
    Queries only when something refers to a session."""
    bundle_ids = [
        t.id for t in visible_ticket_types if t.kind == TicketType.Kind.SESSION_BUNDLE
    ]
    bundle_map: dict[str, list[str]] = {}
    if bundle_ids:
        through = TicketType.sessions.through
        for row in through.objects.filter(tickettype_id__in=bundle_ids).order_by(
            "session__start_time", "session_id"
        ):
            bundle_map.setdefault(str(row.tickettype_id), []).append(
                str(row.session_id)
            )
    session_ids = {sid for ids in bundle_map.values() for sid in ids}
    session_ids.update(e["session_id"] for e in extras if e["session_id"])
    if not session_ids:
        return [], bundle_map
    sessions = [
        {
            "id": str(s.id),
            "name": s.name,
            "start_time": s.start_time.isoformat(),
            "end_time": s.end_time.isoformat(),
        }
        for s in Session.objects.filter(id__in=session_ids).order_by(
            "start_time", "name", "id"
        )
    ]
    return sessions, bundle_map


def build_form_spec(event) -> dict:
    sold_counts = sold_counts_for_event(event)
    active_ticket_types = event.ticket_types.filter(is_active=True)
    visible = list(
        active_ticket_types.filter(is_hidden=False).order_by("sort_order", "name")
    )
    ticket_types = [
        _ticket_type_payload(t, sold_count=sold_counts.get(str(t.id), 0))
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
                "choice_rows",
                queryset=ExtraChoice.objects.filter(is_active=True).order_by(
                    "sort_order", "label"
                ),
            )
        )
    ]
    sessions, bundle_map = _sessions_payload(visible, extras)
    for payload in ticket_types:
        if payload["id"] in bundle_map:
            payload["session_ids"] = bundle_map[payload["id"]]

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
