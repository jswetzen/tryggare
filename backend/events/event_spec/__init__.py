"""Event spec: an authoring format for an event's registration setup (read/validate only so far)."""

from .export import export
from .schema import capabilities, example_spec, json_schema
from .spec import EventSpec
from .validate import validate

__all__ = [
    "EventSpec",
    "capabilities",
    "example_spec",
    "export",
    "json_schema",
    "validate",
]
