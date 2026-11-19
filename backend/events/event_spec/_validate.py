"""Validate a spec dict. Writes nothing; reads the DB only to check a target event.

Layers: shape (pydantic), references, model rules (unsaved instances through
``full_clean()``), going live, setup-check warnings. Errors block; warnings
are advice. Each issue is ``{"path", "code", "message"}`` with a path such as
``ticket_types[2].min_birthdate``.
"""

from collections import Counter
from datetime import date

from django.core.exceptions import ValidationError
from django.utils import timezone
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
from ._issues import MESSAGES, issue
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
        issues.append(issue("event", "registration_open_on_target"))
    if any(
        m.objects.filter(**{lookup: event}).exists() for m, lookup in EMPTINESS_CHECKS
    ):
        issues.append(issue("event", "event_not_empty"))
    return issues


def _shape_issues(exc: PydanticValidationError) -> list[Issue]:
    issues = []
    for err in exc.errors():
        kind = err["type"]
        params = {
            "expected": err.get("ctx", {}).get("expected", ""),
            "detail": err["msg"],
        }
        known = kind in MESSAGES
        message = str(MESSAGES[kind if known else "invalid_value"]) % params
        issues.append(issue(_path(err["loc"]), kind, message))
    return issues


# ---- references -----------------------------------------------------------


def _duplicate_keys(rows, path: str) -> list[Issue]:
    seen = Counter(r.key for r in rows)
    return [
        issue(f"{path}[{i}].key", "duplicate_key", key=row.key)
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
                    key=key,
                    found=KINDS[owner[key]].noun,
                    expected=KINDS[target].noun,
                )
            )
        else:
            issues.append(issue(path, "unknown_key", kind=KINDS[target].noun, key=key))

    def check_list(path: str, keys: list[str], target: str):
        seen: set[str] = set()
        for j, key in enumerate(keys):
            if key in seen:
                issues.append(issue(f"{path}[{j}]", "duplicate_reference", key=key))
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
                issue(f"ticket_types[{i}].requires_ticket_type", "requires_cycle")
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
                    issue(f"promo_codes[{i}].code", "duplicate_code", code=row.code)
                )
    return issues


# ---- going live -----------------------------------------------------------


def _going_live_issues(ev: Event) -> list[Issue]:
    if ev.registration_window_status == RegistrationWindowStatus.OPEN:
        return [issue("event.registration_opens_at", "registration_open")]
    return []


# ---- warnings -------------------------------------------------------------


def _warnings(spec: EventSpec, ev: Event) -> list[Issue]:
    return [
        *_event_warnings(ev),
        *_pricing_warnings(spec),
        *_age_band_warnings(spec),
        *_inactive_unreferenced_warnings(spec),
        *_session_warnings(spec),
        *_requires_cycles(spec),
        *_derived_key_warnings(spec),
        *_ticket_type_warnings(spec),
        *_extra_warnings(spec),
        *_promo_warnings(spec),
    ]


def _event_warnings(ev: Event) -> list[Issue]:
    status = ev.registration_window_status
    if status == RegistrationWindowStatus.NOT_CONFIGURED:
        return [issue("event.registration_opens_at", "registration_not_configured")]
    if status == RegistrationWindowStatus.CLOSED:
        return [issue("event.registration_closes_at", "registration_closed")]
    return []


def _session_warnings(spec: EventSpec) -> list[Issue]:
    first, last = spec.event.start_date, spec.event.end_date
    return [
        issue(f"sessions[{i}].start_time", "session_outside_event")
        for i, s in enumerate(spec.sessions)
        if not first <= timezone.localtime(s.start_time).date() <= last
    ]


def _inactive_ticket_types(spec: EventSpec) -> set[str]:
    return {t.key for t in spec.ticket_types if not t.is_active}


def _ticket_type_warnings(spec: EventSpec) -> list[Issue]:
    unlocked = {
        k for p in spec.promo_codes if p.is_active for k in p.unlocks_ticket_types
    }
    inactive = _inactive_ticket_types(spec)
    out = []
    for i, t in enumerate(spec.ticket_types):
        checks = (
            (
                "price",
                "age_tier_no_price",
                t.price == 0 and (t.min_birthdate or t.max_birthdate),
            ),
            (
                "is_hidden",
                "hidden_not_unlocked",
                t.is_hidden and t.is_active and t.key not in unlocked,
            ),
            (
                "sessions",
                "bundle_without_sessions",
                t.kind == "session_bundle" and not t.sessions,
            ),
            ("sessions", "sessions_ignored", t.kind == "event" and t.sessions),
            (
                "requires_ticket_type",
                "requires_inactive_ticket_type",
                t.is_active and t.requires_ticket_type in inactive,
            ),
            (
                "max_per_required",
                "max_per_required_ignored",
                t.max_per_required is not None and t.requires_ticket_type is None,
            ),
        )
        out += [
            issue(f"ticket_types[{i}].{field}", code)
            for field, code, hit in checks
            if hit
        ]
    return out


def _pricing_warnings(spec: EventSpec) -> list[Issue]:
    # Event.price is ignored only while an active ticket type exists (pricing.calculate_total).
    out = []
    ev = spec.event
    active = any(t.is_active for t in spec.ticket_types)
    if ev.price and active:
        out.append(issue("event.price", "event_price_ignored"))
    # Session.ticket_rule overrides the event default, so the default only matters
    # for a session that leaves it empty (or when there are no sessions).
    follows_default = not spec.sessions or any(not s.ticket_rule for s in spec.sessions)
    if ev.ticket_rule_default == "open" and active and follows_default:
        out.append(issue("event.ticket_rule_default", "ticket_rule_open_with_tickets"))
    return out


_NO_AGE_LIMIT = 10**6
_UNBOUNDED = (0, _NO_AGE_LIMIT)


def _age_on_start(spec: EventSpec, born: date) -> int:
    start = spec.event.start_date
    return start.year - born.year - ((start.month, start.day) < (born.month, born.day))


def _age_range(spec: EventSpec, t) -> tuple[int, int]:
    """Whole ages on the event start the ticket admits. The bounds are birthdates:
    ``min_birthdate`` limits the oldest, ``max_birthdate`` the youngest."""
    youngest = _age_on_start(spec, t.max_birthdate) if t.max_birthdate else 0
    oldest = _age_on_start(spec, t.min_birthdate) if t.min_birthdate else _NO_AGE_LIMIT
    return youngest, oldest


def _audience(t) -> set[str]:
    return {"parent", "child"} if t.applies_to == "either" else {t.applies_to}


def _same_attendees(a, a_range, b, b_range) -> bool:
    # Age is only enforced for children (registrations/views.py), so parents always overlap.
    common = _audience(a) & _audience(b)
    return "parent" in common or (
        "child" in common and a_range[0] <= b_range[1] and b_range[0] <= a_range[1]
    )


def _sold_together(a, b) -> bool:
    """Whether the two sale windows intersect; an open end is unbounded."""
    return (
        a.available_from is None
        or b.available_until is None
        or a.available_from <= b.available_until
    ) and (
        b.available_from is None
        or a.available_until is None
        or b.available_from <= a.available_until
    )


def _age_band_warnings(spec: EventSpec) -> list[Issue]:
    ranges = {i: _age_range(spec, t) for i, t in enumerate(spec.ticket_types)}
    out: dict[tuple[str, str], Issue] = {}
    active = [(i, t) for i, t in enumerate(spec.ticket_types) if t.is_active]

    # An attendee picks one ticket, so a bundle for the same attendees as an event
    # pass is an alternative to it. A bundle that only requires a pass of other
    # attendees (a child bundle behind a parent pass) is a normal family setup.
    index = {t.key: i for i, t in enumerate(spec.ticket_types)}
    passes = {i for i, t in active if t.kind == "event" and not t.is_hidden}
    for i, t in active:
        if t.kind != "session_bundle":
            continue
        required = index.get(t.requires_ticket_type)
        if required is not None and spec.ticket_types[required].kind != "event":
            required = None
        path = f"ticket_types[{i}].kind"
        # Requiring a pass for the same attendees can never be satisfied: they hold one ticket.
        if required is not None and _same_attendees(
            t, ranges[i], spec.ticket_types[required], ranges[required]
        ):
            out[(path, "bundle_requires_own_pass")] = issue(
                path, "bundle_requires_own_pass"
            )
        elif any(
            _same_attendees(t, ranges[i], spec.ticket_types[j], ranges[j])
            for j in passes
        ):
            out[(path, "bundle_replaces_pass")] = issue(path, "bundle_replaces_pass")

    # Age is only enforced for children, so only their tiers can leave a gap or overlap.
    groups: dict[tuple, list[tuple[int, object]]] = {}
    for i, t in active:
        if t.is_hidden or "child" not in _audience(t):
            continue
        scope = frozenset(t.sessions) if t.kind == "session_bundle" else None
        groups.setdefault((t.kind, scope), []).append((i, t))
    for tiers in groups.values():
        tiers.sort(key=lambda it: ranges[it[0]])
        covered = None
        for n, (i, t) in enumerate(tiers):
            low, high = ranges[i]
            path = f"ticket_types[{i}].min_birthdate"
            if covered is not None and low > covered + 1:
                out[(path, "age_band_gap")] = issue(
                    path, "age_band_gap", start=covered + 1, end=low - 1
                )
            for j, other in tiers[:n]:
                if (
                    ranges[i] != _UNBOUNDED
                    and ranges[j] != _UNBOUNDED
                    and low <= ranges[j][1]
                    and _sold_together(t, other)
                ):
                    out[(path, "age_band_overlap")] = issue(
                        path, "age_band_overlap", other=other.name
                    )
            covered = high if covered is None else max(covered, high)
    return sorted(out.values(), key=lambda w: (w["path"], w["code"]))


def _inactive_unreferenced_warnings(spec: EventSpec) -> list[Issue]:
    # Rows nothing active points at that are switched off still travel with an event copy.
    referenced: dict[str, set[str]] = {}
    for kind in TOP_KINDS:
        for row in getattr(spec, kind.name):
            if not getattr(row, "is_active", True):
                continue
            for name, target in kind.refs.items():
                value = getattr(row, name)
                keys = value if kind.is_list_ref(name) else [value]
                referenced.setdefault(target, set()).update(k for k in keys if k)
    out = []
    for kind in KINDS.values():
        if "is_active" not in kind.spec.model_fields:
            continue
        for path, rows in row_groups(spec, kind):
            out += [
                issue(f"{path}[{i}].is_active", "inactive_unreferenced")
                for i, row in enumerate(rows)
                if not row.is_active and row.key not in referenced.get(kind.name, ())
            ]
    return out


def _extra_warnings(spec: EventSpec) -> list[Issue]:
    out = []
    types = {t.key: t for t in spec.ticket_types}
    for i, e in enumerate(spec.extras):
        if e.requires_choice and not any(c.is_active for c in e.choices):
            out.append(issue(f"extras[{i}].choices", "no_active_choices"))
        if not e.requires_choice and e.choices:
            out.append(issue(f"extras[{i}].choices", "choices_ignored"))
        gate = [types[k] for k in e.ticket_types if k in types]
        if e.is_active and gate and not any(_gate_reaches(e, t) for t in gate):
            out.append(issue(f"extras[{i}].ticket_types", "extra_gate_unreachable"))
    return out


def _gate_reaches(e, t) -> bool:
    """Whether a holder of ticket type `t` can take extra `e`; a session-scoped
    per-attendee extra needs a pass that covers its session."""
    if not t.is_active:
        return False
    if not e.per_attendee:
        return True
    if not _fits(e.applies_to, t):
        return False
    return e.session is None or t.kind == "event" or e.session in t.sessions


def _fits(extra_applies_to: str, t) -> bool:
    return extra_applies_to == "either" or extra_applies_to in _audience(t)


def _promo_warnings(spec: EventSpec) -> list[Issue]:
    inactive = _inactive_ticket_types(spec)
    out = []
    for i, c in enumerate(spec.promo_codes):
        targets = [*c.applies_to_ticket_types, *c.unlocks_ticket_types]
        if targets and all(k in inactive for k in targets):
            out.append(issue(f"promo_codes[{i}]", "promo_ticket_types_inactive"))
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
            out.append(issue(f"{path}[{i}].{kind.order[0]}", "ambiguous_order"))
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
                            key=rows[i].key,
                            derived=derived,
                        )
                    )
    return sorted(out, key=lambda w: w["path"])
