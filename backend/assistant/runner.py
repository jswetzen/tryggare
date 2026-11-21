"""Run the assistant on a stored conversation: load history, run, persist.

Transport-agnostic; the WebSocket consumer (step 2) and the management command
both call ``run_conversation``. Failures surface as ``RunFailed`` with a code from
the protocol, never provider text.
"""

import copy
from datetime import timedelta

from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from pydantic_ai.exceptions import UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.messages import (
    ModelMessagesTypeAdapter,
    ModelRequest,
    RetryPromptPart,
    SystemPromptPart,
    ToolReturnPart,
    UserPromptPart,
)

from .agent import RUN_DEADLINE_SECONDS, build_agent, run_assistant
from .models import AssistantConversation, AssistantRun, LLMProvider
from .providers import ProviderError
from .tools import _pii_kind, build_toolset

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

    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


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
        get_user_model().objects.select_for_update().filter(pk=user.pk).first()
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
        version = (row.draft or {}).get("version", 0) + 1
        row.draft = {**item, "token": token, "version": version}
        row.save(update_fields=["draft", "updated_at"])


def _failure_code(exc: Exception) -> str:
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


async def run_conversation(event, user, text: str, *, model=None) -> dict:
    """Run one turn. Returns ``{"text", "draft_version"}``; raises RunFailed.

    A failed run stores no messages (a half-finished tool exchange must not become
    history) but keeps any draft already proposed. ``model`` is for tests.
    """
    provider = await sync_to_async(LLMProvider.load)()
    if not provider.enabled and model is None:
        raise RunFailed("not_enabled")

    def prepare():
        conv = _begin(event, user)
        try:
            toolset, _drafts = build_toolset(
                event, user, lambda token, item: _store_draft(conv, token, item)
            )
            return conv, toolset, trim_history(load_messages(conv.messages))
        except BaseException as exc:
            _release(conv)
            if isinstance(exc, PermissionDenied):
                raise RunFailed("blocked") from None
            raise

    conv, toolset, history = await sync_to_async(prepare)()
    stored = None
    try:
        agent = build_agent(provider, toolset, model=model)
        result = await run_assistant(agent, text, message_history=history)
        stored = dump_messages(result.all_messages())
    except Exception as exc:
        raise RunFailed(_failure_code(exc)) from None
    finally:
        # Also on cancellation, so a cancelled run does not hold the lock until it is declared dead.
        await sync_to_async(_release)(conv, stored)
    draft = await sync_to_async(
        lambda: AssistantConversation.objects.filter(pk=conv.pk)
        .values_list("draft", flat=True)
        .first()
    )()
    return {"text": result.output, "draft_version": (draft or {}).get("version")}
