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
    RegistrationWindowStatus,
)
from ._export import KeyAllocator
from ._issues import issue
from ._kinds import KINDS, TOP_KINDS, nested, row_groups
from .spec import EventSection, EventSpec

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

    ev = Event(**parsed.event.model_dump())
    if event is not None:
        ev.pk = event.pk
    errors = _target_issues(event)
    errors += _reference_issues(parsed)
    errors += _model_issues(parsed, ev)
    ties = _ordering_issues(parsed)
    errors += _going_live_issues(ev)
    warnings = _warnings(parsed, ev)
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
            issue(
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
            issue(
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
        issues.append(issue(_path(err["loc"]), kind, message))
    return issues


# ---- references -----------------------------------------------------------


def _duplicate_keys(rows, path: str) -> list[Issue]:
    seen = Counter(r.key for r in rows)
    return [
        issue(
            f"{path}[{i}].key",
            "duplicate_key",
            _("Key '%(key)s' is used more than once; keys must be unique.")
            % {"key": row.key},
        )
        for i, row in enumerate(rows)
        if seen[row.key] > 1
    ]


def _reference_issues(spec: EventSpec) -> list[Issue]:
    issues: list[Issue] = []
    for kind in KINDS.values():
        for path, rows in row_groups(spec, kind):
            issues += _duplicate_keys(rows, path)

    owner: dict[str, str] = {}
    valid: dict[str, set[str]] = {}
    for kind in TOP_KINDS:
        valid[kind.name] = {r.key for r in getattr(spec, kind.name)}
        for row in getattr(spec, kind.name):
            owner.setdefault(row.key, kind.name)

    def check(path: str, key: str, target: str):
        if key in valid[target]:
            return
        if key in owner:
            issues.append(
                issue(
                    path,
                    "wrong_kind_key",
                    _(
                        "'%(key)s' is the key of another kind of row (%(found)s); a key for %(expected)s is needed here."
                    )
                    % {
                        "key": key,
                        "found": KINDS[owner[key]].noun,
                        "expected": KINDS[target].noun,
                    },
                )
            )
        else:
            issues.append(
                issue(
                    path,
                    "unknown_key",
                    _("No %(kind)s has the key '%(key)s'.")
                    % {"kind": KINDS[target].noun, "key": key},
                )
            )

    def check_list(path: str, keys: list[str], target: str):
        seen: set[str] = set()
        for j, key in enumerate(keys):
            if key in seen:
                issues.append(
                    issue(
                        f"{path}[{j}]",
                        "duplicate_reference",
                        _("'%(key)s' is listed more than once.") % {"key": key},
                    )
                )
            seen.add(key)
            check(f"{path}[{j}]", key, target)

    for kind in TOP_KINDS:
        for i, row in enumerate(getattr(spec, kind.name)):
            for name, target in kind.refs.items():
                value, path = getattr(row, name), f"{kind.name}[{i}].{name}"
                if kind.is_list_ref(name):
                    check_list(path, value, target)
                elif value is not None:
                    check(path, value, target)
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
                issue(
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
                    issues.append(issue(target, code, message))
        return issues
    return []


def _model_issues(spec: EventSpec, ev: Event) -> list[Issue]:
    issues = _clean(
        ev, ["cloned_from"], "event", "event", set(EventSection.model_fields)
    )

    # Build every row first so references can point at rows defined later.
    built = {
        kind.name: [
            kind.model(**{kind.parent: ev}, **kind.plain(row))
            for row in getattr(spec, kind.name)
        ]
        for kind in TOP_KINDS
    }
    by_key = {
        name: {r.key: obj for r, obj in zip(getattr(spec, name), objs)}
        for name, objs in built.items()
    }
    for kind in TOP_KINDS:
        for row, obj in zip(getattr(spec, kind.name), built[kind.name]):
            for name in kind.fk_refs:
                setattr(obj, name, by_key[kind.refs[name]].get(getattr(row, name)))

    def clean(kind, obj, path):
        return _clean(
            obj, kind.clean_exclude(), path, kind.name, set(kind.spec.model_fields)
        )

    codes = Counter(r.code for r in spec.promo_codes)
    for kind in TOP_KINDS:
        for i, (row, obj) in enumerate(zip(getattr(spec, kind.name), built[kind.name])):
            issues += clean(kind, obj, f"{kind.name}[{i}]")
            for child in nested(kind):
                for j, sub in enumerate(getattr(row, child.name)):
                    issues += clean(
                        child,
                        child.model(**{child.parent: obj}, **child.plain(sub)),
                        f"{kind.name}[{i}].{child.name}[{j}]",
                    )
            if kind.name == "promo_codes" and codes[row.code] > 1:
                issues.append(
                    issue(
                        f"promo_codes[{i}].code",
                        "duplicate_code",
                        _(
                            "Code '%(code)s' appears more than once; codes are matched case-insensitively and must be unique."
                        )
                        % {"code": row.code},
                    )
                )
    return issues


# ---- going live -----------------------------------------------------------


def _going_live_issues(ev: Event) -> list[Issue]:
    if ev.registration_window_status == RegistrationWindowStatus.OPEN:
        return [
            issue(
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


def _warnings(spec: EventSpec, ev: Event) -> list[Issue]:
    out: list[Issue] = []
    status = ev.registration_window_status
    if status == RegistrationWindowStatus.NOT_CONFIGURED:
        out.append(
            issue(
                "event.registration_opens_at",
                "registration_not_configured",
                _(
                    "No registration window is set, so public self-serve registration is off."
                ),
            )
        )
    elif status == RegistrationWindowStatus.CLOSED:
        out.append(
            issue(
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
                issue(
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
                issue(
                    f"{p}.price",
                    "age_tier_no_price",
                    _("This age tier has price 0, so it is free. Intended?"),
                )
            )
        if t.is_hidden and t.is_active and t.key not in active_unlocks:
            out.append(
                issue(
                    f"{p}.is_hidden",
                    "hidden_not_unlocked",
                    _(
                        "This ticket type is hidden and no active promo code unlocks it, so nobody can buy it."
                    ),
                )
            )
        if t.kind == "session_bundle" and not t.sessions:
            out.append(
                issue(
                    f"{p}.sessions",
                    "bundle_without_sessions",
                    _("A session bundle lists no sessions."),
                )
            )
        if t.kind == "event" and t.sessions:
            out.append(
                issue(
                    f"{p}.sessions",
                    "sessions_ignored",
                    _(
                        "Sessions are only used by session bundles; they are ignored here."
                    ),
                )
            )
        if t.is_active and t.requires_ticket_type in inactive:
            out.append(
                issue(
                    f"{p}.requires_ticket_type",
                    "requires_inactive_ticket_type",
                    _(
                        "The ticket type this one requires is inactive, so it cannot be bought."
                    ),
                )
            )
        if t.max_per_required is not None and t.requires_ticket_type is None:
            out.append(
                issue(
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
                issue(
                    f"{p}.choices",
                    "no_active_choices",
                    _("This extra requires a choice but has no active choices."),
                )
            )
        if not e.requires_choice and e.choices:
            out.append(
                issue(
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
                issue(
                    p,
                    "promo_ticket_types_inactive",
                    _("Every ticket type this code refers to is inactive."),
                )
            )
    return out


def _derive(rows, kind) -> dict[int, str]:
    """``{index: key}`` as export would allocate them over this ordering."""
    allocator = KeyAllocator()
    return {
        i: allocator.allocate(getattr(rows[i], kind.key_from))
        for i in sorted(range(len(rows)), key=lambda i: kind.sort_key(rows[i]))
    }


def _ties(rows, kind, path) -> list[Issue]:
    seen, out = set(), []
    for i, row in enumerate(rows):
        order = kind.sort_key(row)
        if order in seen:
            out.append(
                issue(
                    f"{path}[{i}].{kind.order[0]}",
                    "ambiguous_order",
                    _(
                        "These rows tie on their ordering fields; give them different sort_order or names."
                    ),
                )
            )
        seen.add(order)
    return out


def _ordering_issues(spec: EventSpec) -> list[Issue]:
    """Rows that tie on export's ordering get keys by database id: an error against an existing event, a warning for a new one."""
    out = []
    for kind in KINDS.values():
        if kind.ties:
            for path, rows in row_groups(spec, kind):
                out += _ties(rows, kind, path)
    return out


def _derived_key_warnings(spec: EventSpec) -> list[Issue]:
    out: list[Issue] = []
    for kind in KINDS.values():
        for path, rows in row_groups(spec, kind):
            for i, derived in _derive(rows, kind).items():
                if rows[i].key != derived:
                    out.append(
                        issue(
                            f"{path}[{i}].key",
                            "key_not_derived",
                            _(
                                "The key '%(key)s' is not the one export derives ('%(derived)s'), so a later export will show this row as removed and added."
                            )
                            % {"key": rows[i].key, "derived": derived},
                        )
                    )
    return sorted(out, key=lambda w: w["path"])
