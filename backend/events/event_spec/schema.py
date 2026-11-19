"""What an LLM (or script) needs to author a spec: JSON Schema, capabilities, example."""

import json
from pathlib import Path

from .spec import EventSpec

_EXAMPLE = Path(__file__).with_name("example.json")

# Named so a model can answer "not supported" instead of inventing a field.
CAPABILITIES = {
    "supported": [
        {
            "id": "event_settings",
            "description": "Event dates, default ticket rule, flat price, registration window, header image, accent colour.",
        },
        {
            "id": "sessions",
            "description": "Sessions with start/end and a per-session ticket rule.",
        },
        {
            "id": "ticket_types",
            "description": "Priced ticket types for parents or children, with age bounds judged on the event start date, sale window, capacity, hidden types, session bundles, and 'only together with' dependencies.",
        },
        {
            "id": "extras",
            "description": "Paid or free add-ons per attendee or per booking, optionally tied to a session, with a fixed list of choices (e.g. sizes) and per-choice price deltas.",
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
}


def json_schema() -> dict:
    return EventSpec.model_json_schema()


def capabilities() -> dict:
    return CAPABILITIES


def example_spec() -> dict:
    """'Test Conference 2027' from docs/registration-setup-walkthrough.md."""
    return json.loads(_EXAMPLE.read_text())
