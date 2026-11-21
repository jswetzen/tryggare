"""Validate and diff in one call: what a caller needs to preview an apply."""

from pydantic import ValidationError as PydanticValidationError

from ..models import Event
from ._diff import diff
from ._issues import SpecError
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
