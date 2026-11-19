"""Event spec: an authoring format for an event's registration setup."""

from ._apply import apply
from ._check import check
from ._diff import diff
from ._export import export
from ._issues import SpecError, issue
from .schema import CAPABILITIES, JSON_SCHEMA, example_spec
from .spec import EventSpec
from ._validate import validate

__all__ = [
    "EventSpec",
    "SpecError",
    "apply",
    "CAPABILITIES",
    "check",
    "diff",
    "example_spec",
    "export",
    "issue",
    "JSON_SCHEMA",
    "validate",
]
