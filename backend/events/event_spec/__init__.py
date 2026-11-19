"""Event spec: an authoring format for an event's registration setup."""

from .apply import SpecError, apply
from .diff import diff
from .export import export
from .schema import capabilities, example_spec, json_schema
from .spec import EventSpec
from .validate import validate

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
