"""Compare an event's current configuration with a spec. Read-only.

A change is ``{"kind", "key", "change", ...}`` where ``change`` is ``added``
(``new`` = the row), ``removed`` (``old`` = the row) or ``changed``
(``fields`` = ``{name: {"old", "new"}}``). Choices have kind ``choices`` and a
``parent`` extra key; an extra's own row never lists its choices. Output is
ordered by kind, then key; reference lists compare as sets.
"""

from ..models import Event
from ._export import export
from ._kinds import KIND_ORDER, TOP_KINDS, nested, row_dict
from .spec import EventSection, EventSpec


def normalize(spec: dict | EventSpec) -> dict:
    """A spec in exactly the form ``export`` produces (Stockholm datetimes, 2-place
    money, rows in export order, reference lists sorted)."""
    parsed = spec if isinstance(spec, EventSpec) else EventSpec.model_validate(spec)
    out = {"event_spec_version": 1, "event": row_dict(EventSection, parsed.event)}
    for kind in TOP_KINDS:
        out[kind.name] = []
        for row in kind.sort(getattr(parsed, kind.name)):
            data = row_dict(kind.spec, row)
            for child in nested(kind):
                data[child.name] = [
                    row_dict(child.spec, c)
                    for c in child.sort(getattr(row, child.name))
                ]
            out[kind.name].append(data)
    return out


def _flat(spec: dict | None) -> dict:
    """``{kind: {key: row}}`` with nested rows lifted out under their own kind."""
    out = {kind: {} for kind in KIND_ORDER}
    if spec is None:
        return out
    out["event"][None] = spec["event"]
    for kind in TOP_KINDS:
        children = nested(kind)
        for row in spec[kind.name]:
            own = {k: v for k, v in row.items() if k not in {c.name for c in children}}
            out[kind.name][row["key"]] = own
            for child in children:
                for sub in row[child.name]:
                    out[child.name][(row["key"], sub["key"])] = {
                        **sub,
                        "parent": row["key"],
                    }
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
