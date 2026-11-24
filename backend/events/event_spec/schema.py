"""What an LLM (or script) needs to author a spec: JSON Schema, capabilities, example."""

import json
from types import MappingProxyType
from pathlib import Path

from .spec import EventSpec

JSON_SCHEMA = MappingProxyType(EventSpec.model_json_schema())
_EXAMPLE = Path(__file__).with_name("example.json")

# Named so a model can answer "not supported" instead of inventing a field.
CAPABILITIES = {
    "supported": [
        {
            "id": "event_settings",
            "description": "Event dates, default ticket rule, flat price, registration window (opening in the future), header image, accent colour.",
        },
        {
            "id": "sessions",
            "description": "Sessions with start/end and a per-session ticket rule.",
        },
        {
            "id": "ticket_types",
            "description": "Priced ticket types for parents or children, with age bounds, sale window, capacity, hidden types, session bundles, and 'only together with' dependencies.",
        },
        {
            "id": "extras",
            "description": "Paid or free add-ons per attendee or per booking, optionally tied to a session, with a fixed list of choices (e.g. sizes) and per-choice price deltas.",
        },
        {
            "id": "extra_ticket_gate",
            "description": "An add-on limited to holders of given ticket types.",
        },
        {
            "id": "promo_codes",
            "description": "Percent or fixed discounts, optionally limited to ticket types, with validity window and use limit; codes can unlock hidden ticket types.",
        },
    ],
    "unsupported": [
        {
            "id": "sibling_discount",
            "description": "Discounts that depend on how many children or siblings register.",
            "closest": "Not automatic. With the organizer's agreement: a promo code (applies_to_ticket_types = the child ticket keys) that the organizer hands to families, one code per registration, never an extra.",
        },
        {
            "id": "multiple_promo_codes",
            "description": "More than one promo code on a single registration.",
        },
        {
            "id": "free_text_extras",
            "description": "Extras where the guardian types free text; only fixed choices exist.",
        },
        {"id": "waitlists", "description": "Waiting lists when a ticket type is full."},
        {
            "id": "family_groups",
            "description": "Family or group bookings as a unit with their own pricing.",
        },
        {
            "id": "line_items",
            "description": "Arbitrary invoice line items or custom pricing rules; prices are plain values.",
        },
        {
            "id": "form_fields",
            "description": "Configuring which person fields the registration form asks for.",
        },
    ],
    "notes": [
        "Ticket ages are judged on the event's own start date S. Ages N-M: min_birthdate = S minus M+1 years plus one day; max_birthdate = S minus N years, null when N is 0. 'Under N' is ages 0 to N-1. E.g. S on 10 May, ages 13-17: min 11 May 18 years before S, max 10 May 13 years before S.",
    ],
}


def example_spec() -> dict:
    """'Test Conference 2027' from docs/registration-setup-walkthrough.md."""
    return json.loads(_EXAMPLE.read_text())
