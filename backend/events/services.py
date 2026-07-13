"""Business logic that doesn't belong on a model or in a view/admin handler.

Currently just extra-duplication (see ``duplicate_extra_to_event``) — the
service-module pattern mirrors ``registrations/pricing.py`` and
``registrations/ticket_rules.py``.
"""

from .models import Event, Extra


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
