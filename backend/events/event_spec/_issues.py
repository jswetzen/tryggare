"""Issue messages and the exception that carries them; imported by every other module here.

One table maps an issue code to its message, so a call site is ``issue(path, code,
**params)``. Codes are part of the API; the texts are translated.
"""

from django.utils.translation import gettext_lazy as _

MESSAGES = {
    # The target event
    "event_not_found": _("The event does not exist."),
    "registration_open_on_target": _(
        "Registration is open on the target event; close registration first."
    ),
    "event_not_empty": _(
        "The target event already has registrations, tickets or check-ins, so its setup cannot be replaced."
    ),
    "integrity": _(
        "The database refused the spec and nothing was changed. A promo code may already be in use on this event."
    ),
    "cross_event_reference": _(
        "The %(kind)s '%(name)s' refers to the %(target)s '%(other)s', which belongs to another event."
    ),
    # Shape (pydantic error types)
    "missing": _("This field is required."),
    "extra_forbidden": _(
        "Unknown field. Remove it or check the schema for the right name."
    ),
    "literal_error": _("Must be one of: %(expected)s."),
    "string_pattern_mismatch": _(
        "Must be lowercase letters and digits separated by single hyphens."
    ),
    "invalid_value": _("Invalid value: %(detail)s"),
    # References and keys
    "duplicate_key": _("Key '%(key)s' is used more than once; keys must be unique."),
    "duplicate_code": _(
        "Code '%(code)s' appears more than once; codes are matched case-insensitively and must be unique."
    ),
    "wrong_kind_key": _(
        "'%(key)s' is the key of another kind of row (%(found)s); a key for %(expected)s is needed here."
    ),
    "unknown_key": _("No %(kind)s has the key '%(key)s'."),
    "duplicate_reference": _("'%(key)s' is listed more than once."),
    "registration_open": _(
        "Registration would already be open. Set registration_opens_at to a "
        "future moment; a person opens registration, not the spec."
    ),
    "age_bounds_inverted": _(
        "min_birthdate (%(min)s) is later than max_birthdate (%(max)s). min_birthdate is the earliest birth date "
        "allowed (the oldest attendee) and max_birthdate the latest (the youngest), so min_birthdate must be the "
        "earlier date. Swap them."
    ),
    # Warnings
    "registration_not_configured": _(
        "No registration window is set, so public self-serve registration is off."
    ),
    "registration_closed": _("The registration window has already closed."),
    "session_outside_event": _("The session starts outside the event's dates."),
    "requires_cycle": _(
        "These ticket types require each other in a loop. Buying one of each satisfies it, so this is likely a mistake."
    ),
    "key_not_derived": _(
        "The key '%(key)s' is not the one export derives ('%(derived)s'), so a later export will show this row as removed and added."
    ),
    "ambiguous_order": _(
        "These rows tie on their ordering fields; give them different sort_order or names."
    ),
    "age_tier_no_price": _("This age tier has price 0, so it is free. Intended?"),
    "hidden_not_unlocked": _(
        "This ticket type is hidden and no active promo code unlocks it, so nobody can buy it."
    ),
    "bundle_without_sessions": _("A session bundle lists no sessions."),
    "sessions_ignored": _(
        "Sessions are only used by session bundles; they are ignored here."
    ),
    "requires_inactive_ticket_type": _(
        "The ticket type this one requires is inactive, so it cannot be bought."
    ),
    "max_per_required_ignored": _(
        "max_per_required is ignored without requires_ticket_type."
    ),
    "no_active_choices": _("This extra requires a choice but has no active choices."),
    "choices_ignored": _("Choices are ignored unless requires_choice is true."),
    "extra_gate_unreachable": _(
        "No active ticket type in this extra's gate can be held by an attendee it applies to, so nobody can take it."
    ),
    "promo_ticket_types_inactive": _(
        "Every ticket type this code refers to is inactive."
    ),
    "bundle_replaces_pass": _(
        "This session bundle covers the same attendees as an event ticket. An attendee picks either this or the pass, not both. Intended?"
    ),
    "bundle_requires_own_pass": _(
        "This session bundle requires an event ticket for the same attendees, but an attendee holds only one ticket, so it can never be bought."
    ),
    "ticket_rule_open_with_tickets": _(
        "Check-in is open to everyone by default but the event sells tickets, so nobody needs a ticket at the door. Intended?"
    ),
    "event_price_ignored": _(
        "The flat event price is ignored while an active ticket type exists, and applies again if all of them are made inactive."
    ),
    "age_band_gap": _("No active ticket covers children aged %(start)s to %(end)s."),
    "age_band_overlap": _(
        "This age tier covers the same ages as '%(other)s'; an attendee in both gets two options. Intended?"
    ),
    "age_label_mismatch": _(
        "The name says ages %(label)s, but the age bounds admit ages %(actual)s on the event start date. "
        "For 'N and under', min_birthdate is the start date minus N+1 years plus one day; for 'at least M', "
        "max_birthdate is the start date minus M years."
    ),
    "discount_as_extra": _(
        "A free extra named like a discount does not discount anything; an extra only adds to the price. Use a promo code."
    ),
    "inactive_unreferenced": _(
        "This row is inactive and nothing refers to it, but it is still copied with the event. Delete it if it is not needed."
    ),
}


def issue(path: str, code: str, message=None, /, **params) -> dict:
    """``{"path", "code", "message"}``; the message is the table's text filled with
    ``params``, unless one is given (Django's own validation errors, view messages)."""
    if message is not None:
        return {"path": path, "code": code, "message": str(message)}
    return {
        "path": path,
        "code": code,
        "message": str(MESSAGES[code]) % params,
        # Kept (as strings) so a stored issue can be re-rendered by localize().
        "params": {k: str(v) for k, v in params.items()},
    }


def localize(issues: list[dict]) -> list[dict]:
    """Issues with ``message`` re-rendered in the active language. Only table-made
    issues (they carry ``params``) change; a draft stored in one language reads in another."""
    out = []
    for item in issues:
        if "params" in item and item.get("code") in MESSAGES:
            try:
                item = {**item, "message": str(MESSAGES[item["code"]]) % item["params"]}
            except (KeyError, TypeError, ValueError):
                pass  # the table's text changed since this was stored: keep the old text
        out.append(item)
    return out


class SpecError(Exception):
    """The spec was refused; nothing was written. ``errors`` are validate()'s issues."""

    def __init__(self, errors: list[dict], warnings: list[dict] | None = None):
        super().__init__("; ".join(f"{e['path']}: {e['message']}" for e in errors))
        self.errors = errors
        self.warnings = warnings or []
