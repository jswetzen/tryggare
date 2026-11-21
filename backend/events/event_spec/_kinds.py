"""The kinds of row a spec holds, in one table.

Export, normalize/diff, validate, apply and the event copy all walk this table, so
adding a field means touching the spec class (and the model), not each walker. A new
reference field also needs a line in ``_apply._write``, which sets references by hand.
How a field is written out comes from its spec annotation, see ``codecs``.
"""

import types
import typing
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from functools import cache
from operator import attrgetter

from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from pydantic import BaseModel

from ..models import Extra, ExtraChoice, PromoCode, Session, TicketType
from .spec import (
    EventSection,
    ExtraChoiceSpec,
    ExtraSpec,
    PromoCodeSpec,
    SessionSpec,
    TicketTypeSpec,
)

_TWO_PLACES = Decimal("0.01")


# ---- field codecs: how a spec value is written out ------------------------


def _base(annotation):
    """``Annotated[X | None, ...]`` -> ``X``."""
    while True:
        origin = typing.get_origin(annotation)
        if origin is typing.Annotated:
            annotation = typing.get_args(annotation)[0]
        elif origin in (typing.Union, types.UnionType):
            rest = [a for a in typing.get_args(annotation) if a is not type(None)]
            if len(rest) != 1:
                return annotation
            annotation = rest[0]
        else:
            return annotation


@cache
def codecs(spec_class) -> dict[str, str]:
    """``{field: "datetime" | "date" | "money" | "keys"}`` for the fields that need one."""
    found = {}
    for name, info in spec_class.model_fields.items():
        base = _base(info.annotation)
        if base is datetime:
            found[name] = "datetime"
        elif base is date:
            found[name] = "date"
        elif base is Decimal:
            found[name] = "money"
        elif typing.get_origin(base) is list:
            (item,) = typing.get_args(base)
            if not (isinstance(item, type) and issubclass(item, BaseModel)):
                found[name] = "keys"
    return found


def _datetime(value: datetime) -> str:
    return timezone.localtime(value, timezone.get_default_timezone()).isoformat()


_ENCODERS = {
    "datetime": _datetime,
    "date": lambda value: value.isoformat(),
    "money": lambda value: format(Decimal(str(value)).quantize(_TWO_PLACES), "f"),
    "keys": sorted,
}


def row_dict(spec_class, row, resolved: dict | None = None) -> dict:
    """``row`` (a spec row or a model instance) as export writes it, minus nested rows.

    ``resolved`` supplies values that are not attributes of ``row``: the key and
    references a model instance only holds as relations.
    """
    resolved = resolved or {}
    kinds = codecs(spec_class)
    out = {}
    for name, info in spec_class.model_fields.items():
        if name in NESTED_NAMES:
            continue
        value = resolved[name] if name in resolved else getattr(row, name)
        if value is not None and name in kinds:
            value = _ENCODERS[kinds[name]](value)
        out[name] = value
    return out


# ---- the table -------------------------------------------------------------


@dataclass(frozen=True)
class Kind:
    name: str  # the spec section, and the kind in a diff
    model: type
    spec: type
    parent: str  # FK field to the owner: the event, or the extra for choices
    related: str  # the owner's reverse accessor
    order: tuple  # export's ordering (the database adds id); also the spec sort
    key_from: str  # the field a key is derived from
    noun: object  # for messages; none for nested kinds, which no key refers to
    refs: dict = field(default_factory=dict)  # {spec field: kind it points at}
    under: str | None = None  # kind this one is nested in
    ties: bool = True  # a tie on `order` is ambiguous (False when the field is unique)

    @property
    def sort_key(self):
        return attrgetter(*self.order)

    def sort(self, rows):
        return sorted(rows, key=self.sort_key)

    def is_list_ref(self, name) -> bool:
        return codecs(self.spec).get(name) == "keys"

    @property
    def fk_refs(self) -> list[str]:
        return [f for f in self.refs if not self.is_list_ref(f)]

    @property
    def m2m_refs(self) -> list[str]:
        return [f for f in self.refs if self.is_list_ref(f)]

    def rows(self, owner):
        """The owner's rows in export order, references loaded."""
        rows = getattr(owner, self.related).all()
        if self.fk_refs:
            rows = rows.select_related(*self.fk_refs)
        return rows.prefetch_related(*self.m2m_refs).order_by(*self.order, "id")

    def plain(self, row) -> dict:
        """The model's own fields from a spec row: no key, references or nested rows.

        Refs are excluded here; ``_apply._write`` sets them by hand."""
        return row.model_dump(exclude={"key", *NESTED_NAMES, *self.refs})

    def clean_exclude(self) -> list[str]:
        """What ``full_clean`` must skip on an unsaved row: the owner, references, history."""
        history = ["cloned_from"] if hasattr(self.model, "cloned_from") else []
        return [self.parent, *self.fk_refs, *history]


KINDS: dict[str, Kind] = {
    k.name: k
    for k in (
        Kind(
            name="sessions",
            model=Session,
            spec=SessionSpec,
            parent="event",
            related="sessions",
            order=("start_time", "name"),
            key_from="name",
            noun=_("session"),
        ),
        Kind(
            name="ticket_types",
            model=TicketType,
            spec=TicketTypeSpec,
            parent="event",
            related="ticket_types",
            order=("sort_order", "name"),
            key_from="name",
            noun=_("ticket type"),
            refs={"sessions": "sessions", "requires_ticket_type": "ticket_types"},
        ),
        Kind(
            name="extras",
            model=Extra,
            spec=ExtraSpec,
            parent="event",
            related="extras",
            order=("sort_order", "name"),
            key_from="name",
            noun=_("extra"),
            refs={"session": "sessions", "ticket_types": "ticket_types"},
        ),
        Kind(
            name="choices",
            model=ExtraChoice,
            spec=ExtraChoiceSpec,
            parent="extra",
            related="choice_rows",
            order=("sort_order", "label"),
            key_from="label",
            noun=None,
            under="extras",
        ),
        Kind(
            name="promo_codes",
            model=PromoCode,
            spec=PromoCodeSpec,
            parent="event",
            related="promo_codes",
            order=("code",),
            key_from="code",
            noun=_("promo code"),
            refs={
                "applies_to_ticket_types": "ticket_types",
                "unlocks_ticket_types": "ticket_types",
            },
            ties=False,
        ),
    )
}
NESTED_NAMES = {k.name for k in KINDS.values() if k.under}
TOP_KINDS = [k for k in KINDS.values() if k.under is None]
KIND_ORDER = ["event", *KINDS]
SPEC_MODELS = ("event", *(k.model._meta.model_name for k in KINDS.values()))


def nested(kind: Kind) -> list[Kind]:
    return [k for k in KINDS.values() if k.under == kind.name]


def row_groups(spec, kind: Kind):
    """``(path, rows)`` for each list of rows of ``kind`` in a parsed spec."""
    if kind.under is None:
        yield kind.name, getattr(spec, kind.name)
    else:
        for i, owner in enumerate(getattr(spec, kind.under)):
            yield f"{kind.under}[{i}].{kind.name}", getattr(owner, kind.name)


def spec_dict_rows(spec: dict):
    """``(spec class, row dict)`` for every row of an exported spec, nested ones included."""
    yield EventSection, spec["event"]
    for kind in TOP_KINDS:
        for row in spec[kind.name]:
            yield kind.spec, row
            for child in nested(kind):
                for sub in row[child.name]:
                    yield child.spec, sub
