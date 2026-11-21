"""Event -> spec dict. Read-only."""

import re
import unicodedata
from typing import NamedTuple


from ..models import Event
from ._issues import SpecError, issue
from ._kinds import KINDS, TOP_KINDS, nested, row_dict
from .spec import EventSection

_MAX_KEY = 64


def slugify_key(text: str) -> str:
    """'Child pass 0-12' -> 'child-pass-0-12'; never empty."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")
    return slug[:_MAX_KEY].strip("-") or "item"


class KeyAllocator:
    """Slugs unique within one kind: 'adult', 'adult-2', 'adult-3'."""

    def __init__(self):
        self._taken: set[str] = set()

    def allocate(self, text: str) -> str:
        base = slugify_key(text)
        key, n = base, 2
        while key in self._taken:
            suffix = f"-{n}"
            key = base[: _MAX_KEY - len(suffix)].strip("-") + suffix
            n += 1
        self._taken.add(key)
        return key


def _key_of(keys: dict, target, holder_kind: str, holder, target_kind: str):
    """The key of ``target`` (None passes through); a row of another event has none."""
    if target is None:
        return None
    if target.id not in keys:
        holder_kind, target_kind = KINDS[holder_kind], KINDS[target_kind]
        raise SpecError(
            [
                issue(
                    "event",
                    "cross_event_reference",
                    kind=holder_kind.noun,
                    name=getattr(holder, holder_kind.key_from),
                    target=target_kind.noun,
                    other=getattr(target, target_kind.key_from),
                )
            ]
        )
    return keys[target.id]


class Keyed(NamedTuple):
    parent: str | None  # the owner's key for a nested row, else None
    key: str
    obj: object


def keyed_rows(event: Event) -> dict[str, list[Keyed]]:
    """The event's rows in export order with their derived keys: ``{kind: [Keyed]}``.

    Ties in the ordering break on id so derived keys do not swap between runs.
    """
    rows = {}
    for kind in TOP_KINDS:
        allocator = KeyAllocator()
        rows[kind.name] = [
            Keyed(None, allocator.allocate(getattr(obj, kind.key_from)), obj)
            for obj in kind.rows(event)
        ]
    for kind in KINDS.values():
        if kind.under:
            rows[kind.name] = []
            for owner in rows[kind.under]:
                allocator = KeyAllocator()
                for obj in kind.rows(owner.obj):
                    key = allocator.allocate(getattr(obj, kind.key_from))
                    rows[kind.name].append(Keyed(owner.key, key, obj))
    return rows


def export(event: Event) -> dict:
    """The event's configuration as a JSON-ready spec; ids and live state are left out.

    Built as plain dicts, not through the spec models, so data the models allow
    but validation rejects (a negative price) still exports.
    """
    rows = keyed_rows(event)
    keys = {kind.name: {r.obj.id: r.key for r in rows[kind.name]} for kind in TOP_KINDS}
    spec = {"event_spec_version": 1, "event": row_dict(EventSection, event)}
    for kind in TOP_KINDS:
        spec[kind.name] = []
        for _owner, key, obj in rows[kind.name]:
            resolved = {"key": key}
            for name, target_kind in kind.refs.items():
                value = getattr(obj, name)
                if kind.is_list_ref(name):
                    resolved[name] = [
                        _key_of(keys[target_kind], t, kind.name, obj, target_kind)
                        for t in value.all()
                    ]
                else:
                    resolved[name] = _key_of(
                        keys[target_kind], value, kind.name, obj, target_kind
                    )
            row = row_dict(kind.spec, obj, resolved)
            for child in nested(kind):
                row[child.name] = [
                    row_dict(child.spec, c, {"key": ckey})
                    for owner_key, ckey, c in rows[child.name]
                    if owner_key == key
                ]
            spec[kind.name].append(row)
    return spec
