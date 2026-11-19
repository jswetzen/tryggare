"""Event spec: an authoring format for an event's registration setup."""

from ._apply import SpecError, apply
from ._diff import diff
from ._export import export
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
    "json_schema",
    "validate",
]
