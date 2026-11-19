"""Compare an event's current configuration with a spec. Read-only.

A change is ``{"kind", "key", "change", ...}`` where ``change`` is ``added``
(``new`` = the row), ``removed`` (``old`` = the row) or ``changed``
(``fields`` = ``{name: {"old", "new"}}``). Choices have kind ``choices`` and a
``parent`` extra key; an extra's own row never lists its choices. Output is
ordered by kind, then key; reference lists compare as sets.
"""

from decimal import Decimal

from ..models import Event
from ._export import _d, _dt, export
from .spec import EventSpec

KIND_ORDER = ["event", "sessions", "ticket_types", "extras", "choices", "promo_codes"]
_TWO_PLACES = Decimal("0.01")
_SET_FIELDS = {"sessions", "applies_to_ticket_types", "unlocks_ticket_types"}


def _money(value: Decimal | None):
    return None if value is None else format(value.quantize(_TWO_PLACES), "f")


def normalize(spec: dict | EventSpec) -> dict:
    """A spec in exactly the form ``export`` produces (Stockholm datetimes, 2-place
    money, rows in export order, reference lists sorted)."""
    parsed = spec if isinstance(spec, EventSpec) else EventSpec.model_validate(spec)
    e = parsed.event

    def row(model, money=(), dts=(), dates=(), drop=()):
        out = {}
        for name in type(model).model_fields:
            if name in drop:
                continue
            value = getattr(model, name)
            if name in money:
                value = _money(value)
            elif name in dts:
                value = _dt(value)
            elif name in dates:
                value = _d(value)
            elif name in _SET_FIELDS:
                value = sorted(value)
            out[name] = value
        return out

    sessions = [
        row(s, dts=("start_time", "end_time"))
        for s in sorted(parsed.sessions, key=lambda s: (s.start_time, s.name))
    ]
    ticket_types = [
        row(
            t,
            money=("price",),
            dts=("available_from", "available_until"),
            dates=("min_birthdate", "max_birthdate"),
        )
        for t in sorted(parsed.ticket_types, key=lambda t: (t.sort_order, t.name))
    ]
    extras = []
    for x in sorted(parsed.extras, key=lambda x: (x.sort_order, x.name)):
        data = row(x, money=("price",), drop=("choices",))
        data["choices"] = [
            row(c, money=("price_delta",))
            for c in sorted(x.choices, key=lambda c: (c.sort_order, c.label))
        ]
        extras.append(data)
    promos = [
        row(p, money=("discount_value",), dts=("valid_from", "valid_until"))
        for p in sorted(parsed.promo_codes, key=lambda p: p.code)
    ]
    return {
        "event_spec_version": 1,
        "event": row(
            e,
            money=("price",),
            dts=("registration_opens_at", "registration_closes_at"),
            dates=("start_date", "end_date"),
        ),
        "sessions": sessions,
        "ticket_types": ticket_types,
        "extras": extras,
        "promo_codes": promos,
    }


def _flat(spec: dict | None) -> dict:
    """``{kind: {key: row}}`` with choices lifted out as kind ``choices``."""
    out = {kind: {} for kind in KIND_ORDER}
    if spec is None:
        return out
    out["event"][None] = spec["event"]
    for kind in ("sessions", "ticket_types", "promo_codes"):
        for r in spec[kind]:
            out[kind][r["key"]] = r
    for x in spec["extras"]:
        out["extras"][x["key"]] = {k: v for k, v in x.items() if k != "choices"}
        for c in x["choices"]:
            out["choices"][(x["key"], c["key"])] = {**c, "parent": x["key"]}
    return out


def diff_normalized(current: dict | None, target: dict) -> list[dict]:
    """Diff two normalized specs; ``current=None`` means a new event (everything added)."""
    old_rows, new_rows = _flat(current), _flat(target)
    changes = []
    for kind in KIND_ORDER:
        old, new = old_rows[kind], new_rows[kind]
        for ident in sorted(old.keys() | new.keys(), key=lambda i: (i is None, str(i))):
            key = ident[1] if isinstance(ident, tuple) else ident
            base = {"kind": kind, "key": key}
            if isinstance(ident, tuple):
                base["parent"] = ident[0]
            if ident not in old:
                changes.append({**base, "change": "added", "new": _public(new[ident])})
            elif ident not in new:
                changes.append(
                    {**base, "change": "removed", "old": _public(old[ident])}
                )
            else:
                fields = {
                    name: {"old": old[ident].get(name), "new": value}
                    for name, value in _public(new[ident]).items()
                    if old[ident].get(name) != value
                }
                if fields:
                    changes.append({**base, "change": "changed", "fields": fields})
    return changes


def _public(row: dict) -> dict:
    return {k: v for k, v in row.items() if k != "parent"}


def diff(event: Event | None, spec: dict) -> list[dict]:
    """Changes needed to turn ``event`` into ``spec`` (no event: all added).

    Raises pydantic's ValidationError for a spec of the wrong shape; run
    ``validate`` first for path-addressed errors.
    """
    current = None if event is None else export(event)
    return diff_normalized(current, normalize(spec))
