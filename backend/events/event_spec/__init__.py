"""Event spec: an authoring format for an event's registration setup."""

from ._apply import apply
from ._diff import diff
from ._export import export
from ._issues import SpecError, issue
from .schema import capabilities, example_spec, json_schema
from .spec import EventSpec
from ._validate import validate

__all__ = [
    "EventSpec",
    "SpecError",
    "apply",
    "capabilities",
    "diff",
    "example_spec",
    "export",
    "issue",
    "json_schema",
    "validate",
]
