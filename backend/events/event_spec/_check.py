"""Validate and diff in one call: what a caller needs to preview an apply."""

import re

from django.utils.text import capfirst
from django.utils.translation import gettext_lazy as _
from pydantic import ValidationError as PydanticValidationError

from ..models import Event
from ._diff import diff
from ._export import export
from ._issues import SpecError
from ._kinds import KINDS
from ._validate import validate


def check(spec: dict, event: Event | None = None) -> dict:
    """``{"valid", "diff", "errors", "warnings"}``; writes nothing.

    The diff is empty for a spec of the wrong shape (the errors say where) and for a
    target that refers to another event's rows (reported as an error).
    """
    errors, warnings = validate(spec, event)
    try:
        changes = diff(event, spec)
    except PydanticValidationError:
        changes = []
    except SpecError as exc:
        changes, errors = [], errors + exc.errors
    return {
        "valid": not errors,
        "diff": changes,
        "errors": errors,
        "warnings": warnings,
    }


# Apply preconditions, not problems with the setup of an event that is already live.
APPLY_GUARDS = {"registration_open_on_target", "event_not_empty", "registration_open"}

_PATH_ROW = re.compile(r"^(\w+)\[(\d+)\](?:\.(\w+)\[(\d+)\])?")
_NAME_FIELD = {"promo_codes": "code", "choices": "label"}


def _row_label(spec: dict, path: str) -> str:
    """'Ticket type 'Child pass'' for ``ticket_types[2].price``; 'Event' for the event itself."""
    match = _PATH_ROW.match(path)
    if not match:
        return str(_("Event"))
    top, i, sub, j = match.groups()
    try:
        row, kind = spec[top][int(i)], KINDS[top]
        if sub:
            row, kind = row[sub][int(j)], KINDS[sub]
    except (KeyError, IndexError):
        return path
    noun = kind.noun or _("choice")
    name = row[_NAME_FIELD.get(kind.name, "name")]
    return f"{capfirst(noun)} '{name}'"


def check_setup(event: Event) -> dict:
    """``{"errors", "warnings"}`` of a live event's setup, each issue with a ``row`` label.

    ``validate(export(event), event)`` minus the apply guards; raises ``SpecError`` for an
    event that cannot be exported.
    """
    spec = export(event)
    errors, warnings = validate(spec, event)
    result = {}
    for name, issues in (("errors", errors), ("warnings", warnings)):
        result[name] = [
            {**i, "row": _row_label(spec, i["path"])}
            for i in issues
            if i["code"] not in APPLY_GUARDS
        ]
    return result
