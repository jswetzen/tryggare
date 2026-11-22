"""Tools the event-creation assistant calls, bound to ONE event and the organizer's
permissions. Applying a spec is deliberately not a tool: it is a human action
through the staff REST API.

The logic is plain functions on ``EventTools`` that raise ``ToolFailure``; a
transport adapts them (``build_toolset`` here; ``mcp_server.build_server`` for MCP).
"""

import functools
import hashlib
import json
from datetime import date, datetime
from typing import Annotated

from asgiref.sync import sync_to_async
from django.core.exceptions import PermissionDenied
from pydantic import Field
from pydantic_ai import ModelRetry
from pydantic_ai.toolsets import FunctionToolset

from events import event_spec
from events.event_spec._diff import normalize
from events.models import Event
from feature_requests import services as feature_requests
from feature_requests.rules import FeatureRequestError

from .permissions import can_use_assistant
from .pii import _pii_kind, find_personal_data, strings_in  # noqa: F401

TOOL_RETRIES = 5

SpecArg = Annotated[
    dict | str,
    Field(
        description=(
            "The COMPLETE event spec as a JSON object with the top-level keys "
            "event_spec_version, event, sessions, ticket_types, extras, promo_codes "
            "(the shape get_current_spec returns)."
        )
    ),
]


class ToolFailure(Exception):
    """A tool call the model can fix by retrying; the message is shown to it."""


# --- personal-data backstop (roadmap, "The assistant (D)"; human review is the real control)
# The patterns live in ``pii``; the names below stay importable from here.

# --- helpers


def _json_default(obj):
    if isinstance(obj, date | datetime):
        return obj.isoformat()
    return str(obj)


def _plain(data):
    """Round-trip through JSON so lazy strings, Decimals and dates are plain values."""
    return json.loads(json.dumps(data, default=_json_default))


def _issues_message(errors: list[dict]) -> str:
    return "; ".join(
        f"{e['path'] or '(spec)'}: {e['message']} [{e['code']}]" for e in errors
    )


def _as_spec(spec) -> dict:
    """Some models send the object as a JSON string."""
    if isinstance(spec, str):
        try:
            spec = json.loads(spec)
        except ValueError:
            raise ToolFailure(
                "spec must be a JSON object, but it is not valid JSON."
            ) from None
    if not isinstance(spec, dict):
        raise ToolFailure("spec must be a JSON object.")
    return spec


def _canonical(data) -> str:
    return json.dumps(_plain(normalize(data)), sort_keys=True)


def base_hash(event: Event) -> str:
    """Hash of the event's current setup; changes when anything in it changes."""
    return hashlib.sha256(_canonical(event_spec.export(event)).encode()).hexdigest()[
        :16
    ]


def draft_token(event_pk, base: str, spec: dict) -> str:
    """Same event state and same proposal give the same token; a changed event gives a new one."""
    raw = json.dumps([str(event_pk), base, _canonical(spec)])
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class Drafts:
    """Proposals of one assistant session: ``items[token] = {"spec", "diff", "warnings", "base"}``.
    Nothing is written to the DB; applying goes through the REST API, which revalidates."""

    def __init__(self, event: Event, on_propose=None):
        self.event = event
        self.items: dict[str, dict] = {}
        # Called with (token, item) in the tool thread, so a draft survives a run that fails later.
        self.on_propose = on_propose

    def is_stale(self, token: str) -> bool:
        """True when the event changed since the draft was proposed (sync, hits the DB)."""
        fresh = Event.objects.get(
            pk=self.event.pk
        )  # the bound instance may be stale itself
        return self.items[token]["base"] != base_hash(fresh)


class EventTools:
    """The tools, as plain sync methods. Their docstrings are the model-facing descriptions."""

    def __init__(self, event: Event, user, on_propose=None):
        ok, issues = can_use_assistant(user, event)
        if not ok:
            raise PermissionDenied("; ".join(i["message"] for i in issues))
        self.event = event
        self.user = user
        self.drafts = Drafts(event, on_propose)

    def _current(self) -> Event:
        row = Event.objects.filter(pk=self.event.pk).first()
        if row is None:
            raise ToolFailure("The event no longer exists.")
        return row

    def _export(self, target: Event) -> dict:
        try:
            return _plain(event_spec.export(target))
        except event_spec.SpecError as exc:
            raise ToolFailure(_issues_message(exc.errors)) from exc

    def _refuse_personal_data(self, spec: dict, target: Event) -> None:
        try:
            known = strings_in(self._export(target))
        except ToolFailure:
            known = set()
        hits = find_personal_data(spec, known)
        if hits:
            where = "; ".join(f"{h['path']} looks like {h['found']}" for h in hits)
            raise ToolFailure(
                f"The spec was not used because it appears to contain personal data ({where}). "
                "Remove it and describe the rule instead; never put names, contact details "
                "or personnummer in a spec."
            )

    def _checked(self, spec) -> tuple[Event, dict, dict]:
        spec = _as_spec(spec)
        target = self._current()
        self._refuse_personal_data(spec, target)
        try:
            return target, spec, event_spec.check(spec, target)
        except event_spec.SpecError as exc:
            raise ToolFailure(_issues_message(exc.errors)) from exc

    def get_capabilities(self) -> dict:
        """The full JSON Schema (exact field names and types) and an example spec, plus
        the capabilities list already in your instructions. Large: call it only to look
        up fields of a row you add. Say "not supported" for anything under
        `unsupported` and offer its `closest` workaround if it has one."""
        return _plain(
            {
                "capabilities": event_spec.CAPABILITIES,
                "schema": event_spec.JSON_SCHEMA,
                "example": event_spec.example_spec(),
            }
        )

    def get_current_spec(self) -> dict:
        """The event's current configuration (event, sessions, ticket types, extras,
        promo codes) as a spec. Contains no registrations or people."""
        return self._export(self._current())

    def validate_spec(self, spec: SpecArg) -> dict:
        """Check a complete proposed spec. Returns `valid`, blocking `errors` and
        advisory `warnings`, each with a `path`, `code` and `message`."""
        spec = _as_spec(spec)
        target = self._current()
        self._refuse_personal_data(spec, target)
        errors, warnings = event_spec.validate(spec, target)
        return _plain({"valid": not errors, "errors": errors, "warnings": warnings})

    def diff_spec(self, spec: SpecArg) -> dict:
        """Changes the proposed spec would make to the current setup, with the
        validation `errors` and `warnings`. Writes nothing."""
        return _plain(self._checked(spec)[2])

    def propose_spec(self, spec: SpecArg) -> dict:
        """Store a valid spec as a draft for the organizer to review. Fails with the
        errors to fix if it is invalid. This does NOT change the event; the
        organizer applies it."""
        target, spec, result = self._checked(spec)
        if result["errors"]:
            raise ToolFailure(
                "The spec is invalid and was not stored: "
                + _issues_message(result["errors"])
            )
        base = base_hash(target)
        token = draft_token(target.pk, base, spec)
        draft = _plain({"diff": result["diff"], "warnings": result["warnings"]})
        self.drafts.items[token] = {"spec": _plain(spec), "base": base, **draft}
        if self.drafts.on_propose:
            self.drafts.on_propose(token, self.drafts.items[token])
        return {"draft": token, "applied": False, **draft}

    def file_feature_request(
        self,
        title: str,
        problem: str,
        desired: str,
        touches: list[str],
        severity: str,
        brief_fragment: str | None = None,
        tried: list[str] | None = None,
        workaround: dict | None = None,
    ) -> dict:
        """File a feature request as a draft for the organizer to confirm. Call it when a
        capability is `unsupported`, when you chose a workaround, or when a validator
        warning cannot be fixed; still build the closest valid setup. Describe the shape
        of the need only: never names, dates, contact details, references, or event and
        ticket names. `touches`: cap:<id> for a capability, code:<code> for a warning,
        spec:<path> or field:<Model.field>, or new:<name> for a need no id covers.
        `workaround`: {"used": what you built, "cost": none|extra_steps|wrong_result|
        not_possible}, or null. `severity`: blocks|wrong_result|risk|friction|cosmetic."""
        data = {
            "title": title,
            "problem": problem,
            "desired": desired,
            "touches": touches,
            "severity": severity,
            "brief_fragment": brief_fragment,
            "tried": tried or [],
            "workaround": workaround,
        }
        try:
            request, match = feature_requests.file_draft(
                self.event, self.user, data, source="assistant"
            )
        except FeatureRequestError as exc:
            raise ToolFailure(
                "The feature request was not stored: "
                + "; ".join(
                    f"{e['path'] or '(input)'}: {e['message']} [{e['code']}]"
                    for e in exc.errors
                )
            ) from exc
        return _plain(
            {"id": request.public_id, "status": "draft", "matches_existing": match}
        )


# No apply tool, on purpose: a model must never change a live event itself.
TOOL_NAMES = (
    "get_capabilities",
    "get_current_spec",
    "validate_spec",
    "diff_spec",
    "propose_spec",
    "file_feature_request",
)


def asyncify(fn, error_type: type[Exception]):
    """Run a sync tool on Django's thread-sensitive executor (ORM-safe), turning
    ``ToolFailure`` into the transport's error type."""

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            return await sync_to_async(fn)(*args, **kwargs)
        except ToolFailure as exc:
            raise error_type(str(exc)) from exc

    return wrapper


def _guarded(fn, guard):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        guard()  # raises PermissionDenied: not a ToolFailure, so it ends the run
        return fn(*args, **kwargs)

    return wrapper


def build_toolset(
    event: Event, user, on_propose=None, guard=None
) -> tuple[FunctionToolset, Drafts]:
    """Function tools for a Pydantic AI agent; errors become ``ModelRetry``.
    ``guard`` (sync) runs before every tool call, to re-check permission mid-run."""
    tools = EventTools(event, user, on_propose)
    toolset = FunctionToolset(max_retries=TOOL_RETRIES)
    for name in TOOL_NAMES:
        fn = getattr(tools, name)
        if guard:
            fn = _guarded(fn, guard)
        toolset.add_function(asyncify(fn, ModelRetry), name=name)
    return toolset, tools.drafts
