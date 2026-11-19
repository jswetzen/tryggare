"""Apply a spec to a new or empty event in one transaction."""

import logging

from django.db import IntegrityError, transaction
from django.utils.translation import gettext as _

from ..models import Event, Extra, ExtraChoice, PromoCode, Session, TicketType
from ._diff import diff_normalized, normalize
from ._export import export, keyed_rows
from .spec import EventSpec
from ._validate import _issue, _target_issues, validate


logger = logging.getLogger(__name__)


class SpecError(Exception):
    """The spec was refused; nothing was written. ``errors`` are validate()'s issues."""

    def __init__(self, errors: list[dict], warnings: list[dict] | None = None):
        super().__init__("; ".join(f"{e['path']}: {e['message']}" for e in errors))
        self.errors = errors
        self.warnings = warnings or []


def apply(
    spec: dict, event: Event | None = None
) -> tuple[Event, list[dict], list[dict]]:
    """Make ``event`` (or a new event) match ``spec``; returns ``(event, diff, warnings)``.

    Use the returned event: the argument is not refreshed. Rows are matched by key so
    their ids stay stable. Registration is never opened: validation refuses a window
    that is open, and refuses a target whose registration is open. Raises SpecError,
    with no writes, on any validation error, a missing target, or a target that has
    registrations, tickets or check-ins.
    """
    if event is not None and (event._state.adding or event.pk is None):
        raise SpecError(
            [_issue("event", "event_not_found", _("The target event does not exist."))]
        )
    errors, warnings = validate(spec, event)
    if errors:
        raise SpecError(errors, warnings)
    parsed = EventSpec.model_validate(spec)
    try:
        with transaction.atomic():
            if event is None:
                current = None
                event = Event(**parsed.event.model_dump())
                event.save()
            else:
                try:
                    event = Event.objects.select_for_update().get(pk=event.pk)
                except Event.DoesNotExist:
                    raise SpecError(
                        [
                            _issue(
                                "event",
                                "event_not_found",
                                _("The target event does not exist."),
                            )
                        ]
                    ) from None
                # Same order as registrations.services, so a racing registration cannot deadlock.
                list(
                    TicketType.objects.select_for_update()
                    .filter(event=event)
                    .order_by("pk")
                )
                recheck = _target_issues(event)
                if recheck:
                    raise SpecError(recheck, warnings)
                current = export(event)
            changes = diff_normalized(current, normalize(parsed))
            _write(event, parsed)
    except IntegrityError as exc:
        logger.warning("event spec apply refused by the database: %s", exc)
        path = "promo_codes" if "unique_promo_code_per_event" in str(exc) else ""
        raise SpecError(
            [
                _issue(
                    path,
                    "integrity",
                    _(
                        "The database refused the spec and nothing was changed. A promo code may already be in use on this event."
                    ),
                )
            ],
            warnings,
        ) from exc
    return event, changes, warnings


def _write(event: Event, spec: EventSpec) -> None:
    existing = keyed_rows(event)
    old = {
        kind: {row[0]: row[-1] for row in rows}
        for kind, rows in existing.items()
        if kind != "choices"
    }
    old_choices = {(p, k): c for p, k, c in existing["choices"]}

    for field, value in spec.event.model_dump().items():
        setattr(event, field, value)
    event.save()

    # Unique (event, code): free the codes of removed promos before anything is written.
    wanted = {p.key for p in spec.promo_codes}
    stale_promos = [p for key, p in old["promo_codes"].items() if key not in wanted]
    for promo in stale_promos:
        promo.delete()

    sessions: dict[str, Session] = {}
    for s in spec.sessions:
        sessions[s.key] = _save(
            old["sessions"].get(s.key),
            Session,
            s.model_dump(exclude={"key"}),
            event=event,
        )

    types: dict[str, TicketType] = {}
    for t in spec.ticket_types:
        fields = t.model_dump(exclude={"key", "sessions", "requires_ticket_type"})
        # requires_ticket_type is set in a second pass (it may point forward); an update leaves it as is until then.
        types[t.key] = _save(
            old["ticket_types"].get(t.key),
            TicketType,
            fields,
            event=event,
        )
        types[t.key].sessions.set(sessions[k] for k in t.sessions)
    for t in spec.ticket_types:
        required = types[t.requires_ticket_type] if t.requires_ticket_type else None
        if types[t.key].requires_ticket_type_id != (required.pk if required else None):
            types[t.key].requires_ticket_type = required
            types[t.key].save(update_fields=["requires_ticket_type"])

    extras: dict[str, Extra] = {}
    for x in spec.extras:
        fields = x.model_dump(exclude={"key", "session", "choices"})
        session = sessions[x.session] if x.session else None
        extra = extras[x.key] = _save(
            old["extras"].get(x.key), Extra, {**fields, "session": session}, event=event
        )
        kept = set()
        for c in x.choices:
            kept.add(c.key)
            _save(
                old_choices.get((x.key, c.key)),
                ExtraChoice,
                c.model_dump(exclude={"key"}),
                extra=extra,
            )
        for (parent, key), choice in old_choices.items():
            if parent == x.key and key not in kept:
                choice.delete()

    for p in spec.promo_codes:
        fields = p.model_dump(
            exclude={"key", "applies_to_ticket_types", "unlocks_ticket_types"}
        )
        promo = _save(old["promo_codes"].get(p.key), PromoCode, fields, event=event)
        promo.applies_to_ticket_types.set(types[k] for k in p.applies_to_ticket_types)
        promo.unlocks_ticket_types.set(types[k] for k in p.unlocks_ticket_types)

    # Deletions last: a removed session cascades to extras, and PROTECT guards required types.
    for key, extra in old["extras"].items():
        if key not in extras:
            extra.delete()
    stale_types = [t for key, t in old["ticket_types"].items() if key not in types]
    TicketType.objects.filter(pk__in=[t.pk for t in stale_types]).update(
        requires_ticket_type=None
    )
    for t in stale_types:
        t.delete()
    for key, session in old["sessions"].items():
        if key not in sessions:
            session.delete()


def _save(obj, model, fields: dict, **parents):
    """Update ``obj`` in place (keeping its id) or create a new row."""
    if obj is None:
        obj = model(**fields, **parents)
    else:
        for name, value in fields.items():
            setattr(obj, name, value)
    obj.save()
    return obj
