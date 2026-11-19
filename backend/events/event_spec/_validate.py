"""Validate a spec dict. Writes nothing; reads the DB only to check a target event.

Layers: shape (pydantic), references, model rules (unsaved instances through
``full_clean()``), going live, setup-check warnings. Errors block; warnings
are advice. Each issue is ``{"path", "code", "message"}`` with a path such as
``ticket_types[2].min_birthdate``.
"""

from collections import Counter

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext as _
from pydantic import ValidationError as PydanticValidationError

from checkins.models import CheckInRecord
from registrations.models import Registration

from ..models import (
    EventTicket,
    SessionTicket,
    Ticket,
    Event,
    Extra,
    ExtraChoice,
    PromoCode,
    RegistrationWindowStatus,
    Session,
    TicketType,
)
from ._export import KeyAllocator
from .spec import EventSpec

Issue = dict

# Django's clean() errors carry no code; these keep the important ones distinguishable.
_CLEAN_CODES = {
    ("ticket_types", "min_birthdate"): "age_window",
    ("ticket_types", "max_birthdate"): "age_window",
    ("ticket_types", "requires_ticket_type"): "invalid_requires",
    ("event", "registration_closes_at"): "window_order",
    ("event", "end_date"): "end_before_start",
    ("sessions", "end_time"): "end_before_start",
    ("ticket_types", "available_until"): "window_order",
    ("promo_codes", "valid_until"): "window_order",
    ("promo_codes", "discount_value"): "percent_over_100",
}

_NOUNS = {
    "sessions": lambda: _("session"),
    "ticket_types": lambda: _("ticket type"),
    "extras": lambda: _("extra"),
    "promo_codes": lambda: _("promo code"),
}


def _issue(path: str, code: str, message: str) -> Issue:
    return {"path": path, "code": code, "message": str(message)}


def _path(loc) -> str:
    out = ""
    for part in loc:
        out += f"[{part}]" if isinstance(part, int) else (f".{part}" if out else part)
    return out


def validate(spec, event: Event | None = None) -> tuple[list[Issue], list[Issue]]:
    """Return ``(errors, warnings)``. ``event`` is the apply target, if any; it
    only supplies the id the unsaved rows are built against."""
    try:
        parsed = EventSpec.model_validate(spec)
    except PydanticValidationError as exc:
        return _shape_issues(exc), []

    errors = _target_issues(event)
    errors += _reference_issues(parsed)
    errors += _model_issues(parsed, event)
    ties = _ordering_issues(parsed)
    errors += _going_live_issues(parsed)
    warnings = _warnings(parsed)
    # Ties only matter when rows are matched against existing ones; a new event
    # has nothing to match, so they are a warning there.
    if event is None or event._state.adding:
        warnings += ties
    else:
        errors += ties
    return errors, warnings


# (model, lookup to the event) for every row that makes an event "in use". A test walks
# the relations of the spec-owned models and fails on a model missing here.
EMPTINESS_CHECKS = [
    (Registration, "event"),
    (EventTicket, "event"),
    (Ticket, "session__event"),
    (SessionTicket, "session__event"),
    (CheckInRecord, "session__event"),
]


def _target_issues(event: Event | None) -> list[Issue]:
    if event is None or event._state.adding:
        return []
    issues = []
    if event.registration_window_status == RegistrationWindowStatus.OPEN:
        issues.append(
            _issue(
                "event",
                "registration_open_on_target",
                _(
                    "Registration is open on the target event; close registration first."
                ),
            )
        )
    if any(
        m.objects.filter(**{lookup: event}).exists() for m, lookup in EMPTINESS_CHECKS
    ):
        issues.append(
            _issue(
                "event",
                "event_not_empty",
                _(
                    "The target event already has registrations, tickets or check-ins, so its setup cannot be replaced."
                ),
            )
        )
    return issues


def _shape_issues(exc: PydanticValidationError) -> list[Issue]:
    issues = []
    for err in exc.errors():
        kind = err["type"]
        if kind == "missing":
            message = _("This field is required.")
        elif kind == "extra_forbidden":
            message = _(
                "Unknown field. Remove it or check the schema for the right name."
            )
        elif kind == "literal_error":
            message = _("Must be one of: %(expected)s.") % {
                "expected": err.get("ctx", {}).get("expected", "")
            }
        elif kind == "string_pattern_mismatch":
            message = _(
                "Must be lowercase letters and digits separated by single hyphens."
            )
        else:
            message = _("Invalid value: %(detail)s") % {"detail": err["msg"]}
        issues.append(_issue(_path(err["loc"]), kind, message))
    return issues


# ---- references -----------------------------------------------------------


def _reference_issues(spec: EventSpec) -> list[Issue]:
    issues: list[Issue] = []
    kinds = {
        "sessions": spec.sessions,
        "ticket_types": spec.ticket_types,
        "extras": spec.extras,
        "promo_codes": spec.promo_codes,
    }
    for name, rows in kinds.items():
        seen = Counter(r.key for r in rows)
        for i, row in enumerate(rows):
            if seen[row.key] > 1:
                issues.append(
                    _issue(
                        f"{name}[{i}].key",
                        "duplicate_key",
                        _("Key '%(key)s' is used more than once; keys must be unique.")
                        % {"key": row.key},
                    )
                )
    for i, extra in enumerate(spec.extras):
        seen = Counter(c.key for c in extra.choices)
        for j, choice in enumerate(extra.choices):
            if seen[choice.key] > 1:
                issues.append(
                    _issue(
                        f"extras[{i}].choices[{j}].key",
                        "duplicate_key",
                        _("Key '%(key)s' is used more than once; keys must be unique.")
                        % {"key": choice.key},
                    )
                )

    owner: dict[str, str] = {}
    for name, rows in kinds.items():
        for row in rows:
            owner.setdefault(row.key, name)
    valid = {name: {r.key for r in rows} for name, rows in kinds.items()}

    def check(path: str, key: str, target: str):
        if key in valid[target]:
            return
        if key in owner:
            issues.append(
                _issue(
                    path,
                    "wrong_kind_key",
                    _(
                        "'%(key)s' is the key of another kind of row (%(found)s); a key for %(expected)s is needed here."
                    )
                    % {
                        "key": key,
                        "found": _NOUNS[owner[key]](),
                        "expected": _NOUNS[target](),
                    },
                )
            )
        else:
            issues.append(
                _issue(
                    path,
                    "unknown_key",
                    _("No %(kind)s has the key '%(key)s'.")
                    % {"kind": _NOUNS[target](), "key": key},
                )
            )

    def check_list(path: str, keys: list[str], target: str):
        seen: set[str] = set()
        for j, key in enumerate(keys):
            if key in seen:
                issues.append(
                    _issue(
                        f"{path}[{j}]",
                        "duplicate_reference",
                        _("'%(key)s' is listed more than once.") % {"key": key},
                    )
                )
            seen.add(key)
            check(f"{path}[{j}]", key, target)

    for i, t in enumerate(spec.ticket_types):
        check_list(f"ticket_types[{i}].sessions", t.sessions, "sessions")
        if t.requires_ticket_type is not None:
            check(
                f"ticket_types[{i}].requires_ticket_type",
                t.requires_ticket_type,
                "ticket_types",
            )
    for i, extra in enumerate(spec.extras):
        if extra.session is not None:
            check(f"extras[{i}].session", extra.session, "sessions")
    for i, p in enumerate(spec.promo_codes):
        for field in ("applies_to_ticket_types", "unlocks_ticket_types"):
            check_list(f"promo_codes[{i}].{field}", getattr(p, field), "ticket_types")
    return issues


def _requires_cycles(spec: EventSpec) -> list[Issue]:
    # A type requiring itself is an error from TicketType.clean; longer loops are only suspicious.
    parent = {t.key: t.requires_ticket_type for t in spec.ticket_types}
    in_cycle: set[str] = set()
    done: set[str] = set()  # shared across start nodes: each chain is walked once
    for t in spec.ticket_types:
        path, node = [], t.key
        while node is not None and node not in done:
            if node in path:
                members = path[path.index(node) :]
                if len(members) > 1:  # a self-reference is TicketType.clean's error
                    in_cycle.update(members)
                break
            path.append(node)
            node = parent.get(node)
        done.update(path)
    issues = []
    for i, t in enumerate(spec.ticket_types):
        if t.key in in_cycle:
            issues.append(
                _issue(
                    f"ticket_types[{i}].requires_ticket_type",
                    "requires_cycle",
                    _(
                        "These ticket types require each other in a loop. Buying one of each satisfies it, so this is likely a mistake."
                    ),
                )
            )
    return issues


# ---- model rules ----------------------------------------------------------


def _clean(obj, exclude, path: str, section: str, fields: set[str]) -> list[Issue]:
    try:
        obj.full_clean(
            exclude=exclude, validate_unique=False, validate_constraints=False
        )
    except ValidationError as exc:
        issues = []
        for field, errs in exc.error_dict.items():
            target = f"{path}.{field}" if field in fields else path
            for err in errs:
                code = err.code or _CLEAN_CODES.get((section, field), "invalid")
                for message in err.messages:
                    issues.append(_issue(target, code, message))
        return issues
    return []


def _model_issues(spec: EventSpec, target: Event | None) -> list[Issue]:
    issues: list[Issue] = []
    ev = Event(**spec.event.model_dump())
    if target is not None:
        ev.pk = target.pk
    issues += _clean(
        ev, ["cloned_from"], "event", "event", set(spec.event.model_fields)
    )

    sessions: dict[str, Session] = {}
    for i, s in enumerate(spec.sessions):
        obj = Session(event=ev, **s.model_dump(exclude={"key"}))
        sessions[s.key] = obj
        issues += _clean(
            obj, ["event"], f"sessions[{i}]", "sessions", set(s.model_fields)
        )

    types: dict[str, TicketType] = {}
    for t in spec.ticket_types:
        types[t.key] = TicketType(
            event=ev,
            **t.model_dump(exclude={"key", "sessions", "requires_ticket_type"}),
        )
    for i, t in enumerate(spec.ticket_types):
        obj = types[t.key]
        required = types.get(t.requires_ticket_type)
        if required is not None:
            obj.requires_ticket_type = required
        issues += _clean(
            obj,
            ["event", "requires_ticket_type"],
            f"ticket_types[{i}]",
            "ticket_types",
            set(t.model_fields),
        )

    for i, e in enumerate(spec.extras):
        extra = Extra(event=ev, **e.model_dump(exclude={"key", "session", "choices"}))
        issues += _clean(
            extra,
            ["event", "session", "cloned_from"],
            f"extras[{i}]",
            "extras",
            set(e.model_fields),
        )
        for j, c in enumerate(e.choices):
            choice = ExtraChoice(extra=extra, **c.model_dump(exclude={"key"}))
            issues += _clean(
                choice,
                ["extra"],
                f"extras[{i}].choices[{j}]",
                "choices",
                set(c.model_fields),
            )

    codes = Counter(p.code for p in spec.promo_codes)
    for i, p in enumerate(spec.promo_codes):
        promo = PromoCode(
            event=ev,
            **p.model_dump(
                exclude={"key", "applies_to_ticket_types", "unlocks_ticket_types"}
            ),
        )
        issues += _clean(
            promo, ["event"], f"promo_codes[{i}]", "promo_codes", set(p.model_fields)
        )
        if codes[p.code] > 1:
            issues.append(
                _issue(
                    f"promo_codes[{i}].code",
                    "duplicate_code",
                    _(
                        "Code '%(code)s' appears more than once; codes are matched case-insensitively and must be unique."
                    )
                    % {"code": p.code},
                )
            )
    return issues


# ---- going live -----------------------------------------------------------


def _going_live_issues(spec: EventSpec) -> list[Issue]:
    ev = Event(**spec.event.model_dump())
    if ev.registration_window_status == RegistrationWindowStatus.OPEN:
        return [
            _issue(
                "event.registration_opens_at",
                "registration_open",
                _(
                    "Registration would already be open. Set registration_opens_at to a "
                    "future moment; a person opens registration, not the spec."
                ),
            )
        ]
    return []


# ---- warnings -------------------------------------------------------------


def _warnings(spec: EventSpec) -> list[Issue]:
    out: list[Issue] = []
    ev = Event(**spec.event.model_dump())
    status = ev.registration_window_status
    if status == RegistrationWindowStatus.NOT_CONFIGURED:
        out.append(
            _issue(
                "event.registration_opens_at",
                "registration_not_configured",
                _(
                    "No registration window is set, so public self-serve registration is off."
                ),
            )
        )
    elif status == RegistrationWindowStatus.CLOSED:
        out.append(
            _issue(
                "event.registration_closes_at",
                "registration_closed",
                _("The registration window has already closed."),
            )
        )

    for i, s in enumerate(spec.sessions):
        if (
            not spec.event.start_date
            <= timezone.localtime(s.start_time).date()
            <= spec.event.end_date
        ):
            out.append(
                _issue(
                    f"sessions[{i}].start_time",
                    "session_outside_event",
                    _("The session starts outside the event's dates."),
                )
            )

    out += _requires_cycles(spec)
    out += _derived_key_warnings(spec)

    active_unlocks = {
        k for p in spec.promo_codes if p.is_active for k in p.unlocks_ticket_types
    }
    inactive = {t.key for t in spec.ticket_types if not t.is_active}
    for i, t in enumerate(spec.ticket_types):
        p = f"ticket_types[{i}]"
        if t.price == 0 and (t.min_birthdate or t.max_birthdate):
            out.append(
                _issue(
                    f"{p}.price",
                    "age_tier_no_price",
                    _("This age tier has price 0, so it is free. Intended?"),
                )
            )
        if t.is_hidden and t.is_active and t.key not in active_unlocks:
            out.append(
                _issue(
                    f"{p}.is_hidden",
                    "hidden_not_unlocked",
                    _(
                        "This ticket type is hidden and no active promo code unlocks it, so nobody can buy it."
                    ),
                )
            )
        if t.kind == "session_bundle" and not t.sessions:
            out.append(
                _issue(
                    f"{p}.sessions",
                    "bundle_without_sessions",
                    _("A session bundle lists no sessions."),
                )
            )
        if t.kind == "event" and t.sessions:
            out.append(
                _issue(
                    f"{p}.sessions",
                    "sessions_ignored",
                    _(
                        "Sessions are only used by session bundles; they are ignored here."
                    ),
                )
            )
        if t.is_active and t.requires_ticket_type in inactive:
            out.append(
                _issue(
                    f"{p}.requires_ticket_type",
                    "requires_inactive_ticket_type",
                    _(
                        "The ticket type this one requires is inactive, so it cannot be bought."
                    ),
                )
            )
        if t.max_per_required is not None and t.requires_ticket_type is None:
            out.append(
                _issue(
                    f"{p}.max_per_required",
                    "max_per_required_ignored",
                    _("max_per_required is ignored without requires_ticket_type."),
                )
            )

    for i, e in enumerate(spec.extras):
        p = f"extras[{i}]"
        active_choices = [c for c in e.choices if c.is_active]
        if e.requires_choice and not active_choices:
            out.append(
                _issue(
                    f"{p}.choices",
                    "no_active_choices",
                    _("This extra requires a choice but has no active choices."),
                )
            )
        if not e.requires_choice and e.choices:
            out.append(
                _issue(
                    f"{p}.choices",
                    "choices_ignored",
                    _("Choices are ignored unless requires_choice is true."),
                )
            )

    for i, c in enumerate(spec.promo_codes):
        p = f"promo_codes[{i}]"
        targets = [*c.applies_to_ticket_types, *c.unlocks_ticket_types]
        if targets and all(k in inactive for k in targets):
            out.append(
                _issue(
                    p,
                    "promo_ticket_types_inactive",
                    _("Every ticket type this code refers to is inactive."),
                )
            )
    return out


def _ordering(spec: EventSpec) -> dict:
    """The (kind, ordering key) pairs export sorts by, minus the id tiebreak."""
    return {
        "sessions": (spec.sessions, lambda r: (r.start_time, r.name), "start_time"),
        "ticket_types": (
            spec.ticket_types,
            lambda r: (r.sort_order, r.name),
            "sort_order",
        ),
        "extras": (spec.extras, lambda r: (r.sort_order, r.name), "sort_order"),
    }


def _derive(rows, order, text):
    """``{index: key}`` as export would allocate them over this ordering."""
    allocator = KeyAllocator()
    return {
        i: allocator.allocate(text(rows[i]))
        for i in sorted(range(len(rows)), key=lambda i: order(rows[i]))
    }


def _ties(rows, order, path, field) -> list[Issue]:
    seen, out = set(), []
    for i, row in enumerate(rows):
        o = order(row)
        if o in seen:
            out.append(
                _issue(
                    f"{path}[{i}].{field}",
                    "ambiguous_order",
                    _(
                        "These rows tie on their ordering fields; give them different sort_order or names."
                    ),
                )
            )
        seen.add(o)
    return out


def _ordering_issues(spec: EventSpec) -> list[Issue]:
    """Rows that tie on export's ordering get keys by database id: an error against an existing event, a warning for a new one."""
    out = []
    for name, (rows, order, field) in _ordering(spec).items():
        out += _ties(rows, order, name, field)
    for i, e in enumerate(spec.extras):
        out += _ties(
            e.choices,
            lambda c: (c.sort_order, c.label),
            f"extras[{i}].choices",
            "sort_order",
        )
    return out


def _derived_key_warnings(spec: EventSpec) -> list[Issue]:
    out: list[Issue] = []

    def check(path: str, rows, order, text):
        for i, derived in _derive(rows, order, text).items():
            if rows[i].key != derived:
                out.append(
                    _issue(
                        f"{path}[{i}].key",
                        "key_not_derived",
                        _(
                            "The key '%(key)s' is not the one export derives ('%(derived)s'), so a later export will show this row as removed and added."
                        )
                        % {"key": rows[i].key, "derived": derived},
                    )
                )

    check("sessions", spec.sessions, lambda r: (r.start_time, r.name), lambda r: r.name)
    check(
        "ticket_types",
        spec.ticket_types,
        lambda r: (r.sort_order, r.name),
        lambda r: r.name,
    )
    check("extras", spec.extras, lambda r: (r.sort_order, r.name), lambda r: r.name)
    for i, e in enumerate(spec.extras):
        check(
            f"extras[{i}].choices",
            e.choices,
            lambda c: (c.sort_order, c.label),
            lambda c: c.label,
        )
    check("promo_codes", spec.promo_codes, lambda r: r.code, lambda r: r.code)
    return sorted(out, key=lambda w: w["path"])
