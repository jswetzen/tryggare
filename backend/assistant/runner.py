"""Run the assistant on a stored conversation: load history, run, persist.

Transport-agnostic; the WebSocket consumer (step 2) and the management command
both call ``run_conversation``. Failures surface as ``RunFailed`` with a code from
the protocol, never provider text.
"""

import asyncio
import copy
import logging
import uuid
from dataclasses import dataclass
from datetime import timedelta

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import (
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    PartDeltaEvent,
    PartStartEvent,
    RetryPromptPart,
    SystemPromptPart,
    TextPart,
    TextPartDelta,
    ThinkingPart,
    ToolReturnPart,
    UserPromptPart,
)

from .agent import RUN_DEADLINE_SECONDS, build_agent, run_assistant
from events.models import Event

from .models import AssistantConversation, AssistantRun, LLMProvider
from .permissions import can_use_assistant, fresh_user
from .providers import ProviderError
from .tools import TOOL_NAMES, _pii_kind, build_toolset

logger = logging.getLogger(__name__)

# A run older than the deadline plus this is dead (worker killed), not running.
DEAD_RUN_SLACK_SECONDS = 60
# Big, reproducible tool output; stubbed in stored history (see trim_history).
STUBBED_TOOLS = frozenset({"get_capabilities", "get_current_spec"})
STUB = "[Output of an earlier run omitted. Call the tool again if you need it.]"
# pydantic-ai 2.71 has a ProcessHistory capability, but trimming on load keeps the
# stored copy small too and is testable without an agent.
MAX_HISTORY_TURNS = 12


class RunFailed(Exception):
    """``code`` is one of the protocol's run_failed codes."""

    def __init__(self, code: str, cause: BaseException | None = None):
        self.code = code
        super().__init__(code)
        if code not in ("busy", "notice_required"):
            # Type only: the message may hold chat text or a provider body.
            logger.warning(
                "assistant run refused or failed: %s (%s)",
                code,
                type(cause).__name__ if cause else "-",
            )


def group_name(conversation_id) -> str:
    """The channel group of a conversation's connections."""
    return f"assistant_{conversation_id.hex}"


def dump_messages(messages) -> list:
    """Storable form. The prompt is passed as ``instructions=`` and must reach the
    model fresh every run, so no system prompt or instructions copy is kept."""
    clean = []
    for msg in messages:
        if isinstance(msg, ModelRequest):
            msg = copy.copy(msg)
            msg.instructions = None
            msg.parts = [p for p in msg.parts if not isinstance(p, SystemPromptPart)]
            if not msg.parts:
                continue
        elif isinstance(msg, ModelResponse):
            # Reasoning is the provider's, can be long, and is never replayed to it.
            msg = copy.copy(msg)
            msg.parts = [p for p in msg.parts if not isinstance(p, ThinkingPart)]
            if not msg.parts:
                continue
        clean.append(msg)
    return ModelMessagesTypeAdapter.dump_python(clean, mode="json")


def load_messages(stored: list) -> list:
    return ModelMessagesTypeAdapter.validate_python(stored)


def _starts_turn(msg) -> bool:
    # A request that also answers a tool call is not a safe cut: its call would be dropped.
    return (
        isinstance(msg, ModelRequest)
        and any(isinstance(p, UserPromptPart) for p in msg.parts)
        and not any(isinstance(p, (ToolReturnPart, RetryPromptPart)) for p in msg.parts)
    )


def trim_history(messages: list, max_turns: int = MAX_HISTORY_TURNS) -> list:
    """Stub the big read-tool results and keep only the last ``max_turns`` user
    turns. Cuts fall on a user prompt, so no tool call loses its return."""
    messages = copy.deepcopy(messages)
    for msg in messages:
        if isinstance(msg, ModelRequest):
            for part in msg.parts:
                if isinstance(part, ToolReturnPart) and part.tool_name in STUBBED_TOOLS:
                    part.content = STUB
    starts = [i for i, m in enumerate(messages) if _starts_turn(m)]
    if len(starts) > max_turns:
        messages = messages[starts[-max_turns] :]
    return messages


def transcript(conversation: AssistantConversation) -> list[dict]:
    """User prompts and the assistant's text, in order (what the chat UI shows)."""
    out = []
    for msg in load_messages(conversation.messages):
        for part in msg.parts:
            kind = part.part_kind
            if kind == "user-prompt" and isinstance(part.content, str):
                out.append({"role": "user", "text": part.content})
            elif kind == "text" and part.content:
                out.append({"role": "assistant", "text": part.content})
    return out


def chat_text_warning(text: str) -> str | None:
    """Warn-not-block check on what the organizer typed; None when it looks fine."""
    return _pii_kind(text)


def purge_idle(now=None) -> int:
    """Delete conversations idle past ASSISTANT_RETENTION_DAYS, and old run-log rows."""
    now = now or timezone.now()
    cutoff = now - timedelta(days=settings.ASSISTANT_RETENTION_DAYS)
    deleted, _ = AssistantConversation.objects.filter(updated_at__lt=cutoff).delete()
    AssistantRun.objects.filter(started_at__lt=now - timedelta(days=1)).delete()
    return deleted


def _is_dead(conv: AssistantConversation, now) -> bool:
    limit = timedelta(seconds=RUN_DEADLINE_SECONDS + DEAD_RUN_SLACK_SECONDS)
    return conv.run_started_at is None or now - conv.run_started_at > limit


def _begin(event, user) -> AssistantConversation:
    """Take the run lock and the rate-limit slot, or raise RunFailed."""
    now = timezone.now()
    with transaction.atomic():
        # Serialise per user: the cross-event busy check and the rate-limit count
        # below are check-then-act and would race between two events otherwise.
        locked = (
            get_user_model()
            .objects.select_for_update()
            .filter(pk=user.pk, is_active=True)
            .first()
        )
        # Before the conversation row and the rate-limit slot: a blocked run costs nothing.
        if locked is None or not can_use_assistant(locked, event)[0]:
            raise RunFailed("blocked")
        conv, _ = AssistantConversation.objects.select_for_update().get_or_create(
            event=event, user=user
        )
        if conv.status == conv.STATUS_RUNNING and not _is_dead(conv, now):
            raise RunFailed("busy")
        if conv.notice_accepted_at is None:
            raise RunFailed("notice_required")
        # One running conversation per user, across events.
        others = AssistantConversation.objects.filter(
            user=user, status=conv.STATUS_RUNNING
        ).exclude(pk=conv.pk)
        if any(not _is_dead(o, now) for o in others):
            raise RunFailed("busy")
        recent = AssistantRun.objects.filter(
            user=user, started_at__gt=now - timedelta(hours=1)
        ).count()
        if recent >= settings.ASSISTANT_RUNS_PER_HOUR:
            raise RunFailed("rate_limited")
        AssistantRun.objects.create(user=user, started_at=now)
        conv.status = conv.STATUS_RUNNING
        conv.run_started_at = now
        conv.save(update_fields=["status", "run_started_at", "updated_at"])
        return conv


def _owned(conv: AssistantConversation):
    """This run's row, only while it still holds the lock. A clear, or a newer run
    that declared this one dead, must not be overwritten by it."""
    return AssistantConversation.objects.filter(
        pk=conv.pk,
        status=AssistantConversation.STATUS_RUNNING,
        run_started_at=conv.run_started_at,
    )


def _release(conv: AssistantConversation, messages=None) -> None:
    fields = {"status": AssistantConversation.STATUS_IDLE, "run_started_at": None}
    if messages is not None:
        fields["messages"] = messages
    _owned(conv).update(updated_at=timezone.now(), **fields)


def _store_draft(conv: AssistantConversation, token: str, item: dict) -> None:
    with transaction.atomic():
        row = _owned(conv).select_for_update().first()
        if row is None:
            return
        row.draft_version += 1
        row.draft = {**item, "token": token, "version": row.draft_version}
        row.save(update_fields=["draft", "draft_version", "updated_at"])


class _LockLost(Exception):
    """The run's row was cleared, or a newer run took it over."""


def _failure_code(exc: Exception) -> str:
    if isinstance(exc, _LockLost):
        return "cancelled"
    if isinstance(exc, PermissionDenied):
        return "blocked"
    if isinstance(exc, TimeoutError):
        return "timeout"
    if isinstance(exc, UsageLimitExceeded):
        return "limit"
    if isinstance(exc, UnexpectedModelBehavior):
        return "model_error"
    if isinstance(exc, ProviderError):
        if exc.code == "auth_failed":
            return "auth_failed"
        if exc.code in ("http_error", "bad_response"):
            return "model_error"
        return "provider_unreachable"
    return "model_error"


def _permission_guard(event_pk, user, conv=None):
    """Sync check run before every tool call: permissions can be revoked mid-run,
    and a clear (from any process) ends the run here rather than at its end."""

    def check():
        if conv is not None and not _owned(conv).exists():
            raise _LockLost()
        fresh = fresh_user(user)
        event = Event.objects.filter(pk=event_pk).first()
        if fresh is None or event is None or not can_use_assistant(fresh, event)[0]:
            raise PermissionDenied("No longer allowed to use the assistant.")

    return check


def _draft_version(conv_pk) -> int:
    return (
        AssistantConversation.objects.filter(pk=conv_pk)
        .values_list("draft_version", flat=True)
        .first()
        or 0
    )


def _stream_forwarder(conv_pk, emit, last_version: int):
    """Event-stream handler turning agent events into protocol payloads. Tool
    arguments and results (they hold the spec) and thinking parts are never forwarded."""
    state = {"version": last_version}
    # The model picks tool names and call ids; only ours go over the wire.
    call_ids: dict[str, str] = {}

    def call_id(raw) -> str:
        return call_ids.setdefault(raw, f"t-{len(call_ids) + 1}")

    def tool(name) -> str:
        return name if name in TOOL_NAMES else "unknown"

    async def handler(_ctx, stream):
        async for ev in stream:
            if isinstance(ev, PartStartEvent) and isinstance(ev.part, TextPart):
                if ev.part.content:
                    await emit({"type": "text_delta", "text": ev.part.content})
            elif isinstance(ev, PartDeltaEvent) and isinstance(ev.delta, TextPartDelta):
                if ev.delta.content_delta:
                    await emit({"type": "text_delta", "text": ev.delta.content_delta})
            elif isinstance(ev, FunctionToolCallEvent):
                await emit(
                    {
                        "type": "tool_started",
                        "call_id": call_id(ev.part.tool_call_id),
                        "tool": tool(ev.part.tool_name),
                    }
                )
            elif isinstance(ev, FunctionToolResultEvent):
                ok = ev.part.outcome == "success"
                await emit(
                    {
                        "type": "tool_finished",
                        "call_id": call_id(ev.tool_call_id),
                        "tool": tool(ev.part.tool_name),
                        "ok": ok,
                    }
                )
                if ok and ev.part.tool_name == "propose_spec":
                    version = await sync_to_async(_draft_version)(conv_pk)
                    if version != state["version"]:
                        state["version"] = version
                        await emit({"type": "draft_updated", "draft_version": version})

    return handler


async def run_conversation(
    event, user, text: str, *, model=None, on_started=None, on_event=None
) -> dict:
    """Run one turn. Returns ``{"text", "draft_version"}``; raises RunFailed.

    A failed run stores no messages (a half-finished tool exchange must not become
    history) but keeps any draft already proposed. ``model`` is for tests.
    ``on_started()`` is awaited once the lock is held; ``on_event(payload)`` gets
    tool, text and draft events (the agent then streams its model requests).
    """
    provider = await sync_to_async(LLMProvider.load)()
    if not provider.enabled and model is None:
        raise RunFailed("not_enabled")

    def prepare():
        conv = _begin(event, user)
        try:
            toolset, _drafts = build_toolset(
                event,
                user,
                lambda token, item: _store_draft(conv, token, item),
                guard=_permission_guard(event.pk, user, conv),
            )
            return conv, toolset, trim_history(load_messages(conv.messages))
        except BaseException as exc:
            _release(conv)
            if isinstance(exc, PermissionDenied):
                raise RunFailed("blocked", exc) from None
            raise

    # The thread keeps running if we are cancelled; wait it out so its lock is released.
    prep = asyncio.ensure_future(sync_to_async(prepare)())
    try:
        conv, toolset, history = await asyncio.shield(prep)
    except asyncio.CancelledError:
        try:
            await _release_after(prep)
        finally:
            raise

    stored = None
    try:
        if on_started:
            await on_started()
        agent = build_agent(provider, toolset, model=model)
        handler = (
            _stream_forwarder(conv.pk, on_event, conv.draft_version)
            if on_event
            else None
        )
        result = await run_assistant(
            agent, text, message_history=history, event_stream_handler=handler
        )
        stored = dump_messages(result.all_messages())
    except Exception as exc:
        raise RunFailed(_failure_code(exc), exc) from None
    finally:
        # Also on cancellation, so a cancelled run does not hold the lock until it is declared dead.
        await sync_to_async(_release)(conv, stored)
    return {
        "text": result.output,
        "draft_version": await sync_to_async(_draft_version)(conv.pk) or None,
    }


async def _release_after(prep) -> None:
    try:
        conv, _toolset, _history = await prep
    except Exception:
        return  # prepare released its own lock
    await sync_to_async(_release)(conv)


# --- running in the background, for a transport


@dataclass
class _Handle:
    task: asyncio.Task | None = None
    started: bool = False
    cancel_requested: bool = False


# Per process, like the task itself: a run outlives the connection that started it.
_RUNS: dict[tuple, _Handle] = {}
_TASKS: set[asyncio.Task] = set()


def start_run(event, user, text, *, reply_to, publish, refuse, model=None) -> None:
    """Run in a task that outlives the caller. ``publish(payload)`` reaches every
    connection of the conversation; ``refuse(payload)`` only the sender (used for
    refusals before a run exists). Payloads are protocol messages."""
    key = (event.pk, user.pk)
    handle = _Handle()
    if key in _RUNS:
        handle = None
    else:
        _RUNS[key] = handle
    run_id = f"r-{uuid.uuid4().hex[:8]}"

    async def drive():
        if handle is None:
            await refuse(_failed(None, reply_to, "busy"))
            return

        async def on_started():
            handle.started = True
            await publish(
                {"type": "run_started", "run_id": run_id, "reply_to": reply_to}
            )
            if handle.cancel_requested:
                handle.task.cancel()

        async def on_event(payload):
            await publish({**payload, "run_id": run_id})

        try:
            await run_conversation(
                event, user, text, model=model, on_started=on_started, on_event=on_event
            )
            await publish({"type": "run_finished", "run_id": run_id})
        except RunFailed as exc:
            sink = publish if handle.started else refuse
            await sink(_failed(run_id if handle.started else None, reply_to, exc.code))
        except asyncio.CancelledError:
            if handle.started:
                await publish(_failed(run_id, reply_to, "cancelled"))
        except Exception as exc:
            logger.warning("assistant run crashed: %s", type(exc).__name__)
            sink = publish if handle.started else refuse
            await sink(
                _failed(run_id if handle.started else None, reply_to, "model_error")
            )
        finally:
            if handle.task is asyncio.current_task():
                _RUNS.pop(key, None)

    task = asyncio.ensure_future(drive())
    # The loop holds tasks weakly; the busy refusal has no handle to keep it alive.
    _TASKS.add(task)
    task.add_done_callback(_TASKS.discard)
    if handle is not None:
        handle.task = task


def _failed(run_id, reply_to, code: str) -> dict:
    return {"type": "run_failed", "run_id": run_id, "reply_to": reply_to, "code": code}


def request_cancel(event_pk, user_pk) -> None:
    """Cancel this user's run on the event, if it is in this process. Before the
    lock is held it is only noted: cancelling mid-setup would orphan the lock."""
    handle = _RUNS.get((event_pk, user_pk))
    if handle is None or handle.task is None:
        return
    if handle.started:
        handle.task.cancel()
    else:
        handle.cancel_requested = True


def clear_conversation(conv: AssistantConversation) -> None:
    """Messages, draft and run state together; the notice and the version counter stay.
    A run still in flight finds the row no longer its own (``_owned``) and writes nothing."""
    AssistantConversation.objects.filter(pk=conv.pk).update(
        messages=[],
        draft=None,
        status=AssistantConversation.STATUS_IDLE,
        run_started_at=None,
        updated_at=timezone.now(),
    )


def discard_draft(conv: AssistantConversation, *, version=None, token=None) -> bool:
    """Drop the draft; True if one was dropped. With ``version``/``token`` only that
    draft goes, so a newer proposal that landed meanwhile (after an apply) survives."""
    rows = AssistantConversation.objects.filter(pk=conv.pk, draft__isnull=False)
    if version is not None:
        rows = rows.filter(draft__version=version)
    if token is not None:
        rows = rows.filter(draft__token=token)
    return bool(rows.update(draft=None, updated_at=timezone.now()))


def reset_if_dead(conv: AssistantConversation) -> bool:
    """Free the lock of a run whose worker died. Returns whether a run is live."""
    if conv.status != conv.STATUS_RUNNING:
        return False
    if _is_dead(conv, timezone.now()):
        # Only the dead run's lock: a run that took over since conv was read keeps its own.
        _owned(conv).update(status=conv.STATUS_IDLE, run_started_at=None)
        conv.status, conv.run_started_at = conv.STATUS_IDLE, None
        return False
    return True
