"""Run one brief against a model and measure it. Used by ``manage.py assistant_eval``;
tests pass a scripted model (FunctionModel) instead of a live one."""

import json
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models import Model

from assistant.agent import RUN_DEADLINE_SECONDS, build_agent, run_assistant
from assistant.models import LLMProvider
from assistant.runner import _failure_code, trim_history
from assistant.tools import EventTools, build_toolset
from events import event_spec

from .briefs import Brief
from .criteria import Check, Outcome, judge

EVAL_USER = "assistant-eval"


def eval_user():
    """A superuser for the eval's scratch database (the assistant needs spec permissions)."""
    model = get_user_model()
    user = model.objects.filter(username=EVAL_USER).first()
    return user or model.objects.create_superuser(EVAL_USER, "eval-" + "x" * 16)


@dataclass
class RunResult:
    brief: str
    run: int
    passed: bool
    checks: list[Check]
    reason: str
    wall_s: float
    replies: list[str]
    tool_calls: dict[str, int]
    requests: int
    prompt_tokens: int
    output_tokens: int
    peak_context: int
    capabilities_tokens: int | None
    error: str | None = None
    drafts: int = 0
    diff: list = field(default_factory=list)


def _responses(messages) -> list[ModelResponse]:
    return [m for m in messages if isinstance(m, ModelResponse)]


def capabilities_tokens(messages) -> int | None:
    """Prompt tokens the get_capabilities result added: the next request's input minus
    this one's, less the call's own output. None if the model reports no usage."""
    rs = _responses(messages)
    for i, r in enumerate(rs[:-1]):
        if any(
            isinstance(p, ToolCallPart) and p.tool_name == "get_capabilities"
            for p in r.parts
        ):
            nxt = rs[i + 1].usage.input_tokens - r.usage.input_tokens
            cost = nxt - r.usage.output_tokens
            return cost if cost > 0 else None
    return None


def static_capabilities_size() -> dict:
    """Size of what get_capabilities returns, independent of any model's tokenizer."""
    text = json.dumps(EventTools.get_capabilities(None), ensure_ascii=False)
    return {"chars": len(text), "approx_tokens": len(text) // 4}


async def _converse(agent, turns, deadline):
    history, replies = [], []
    for prompt in turns:
        result = await run_assistant(
            agent, prompt, message_history=trim_history(history), deadline=deadline
        )
        history = result.all_messages()
        replies.append(str(result.output))
    return history, replies


def run_brief(
    brief: Brief,
    model: Model | Callable[[], Model],
    *,
    run: int = 1,
    deadline: float = RUN_DEADLINE_SECONDS,
    user=None,
) -> RunResult:
    # A fresh model per run: its HTTP client is bound to the event loop that first used
    # it, and every run gets its own loop.
    model = model if isinstance(model, Model) else model()
    user = user or eval_user()
    event = event_spec.apply(brief.fixture())[0]
    base = event_spec.export(event)
    toolset, drafts = build_toolset(event, user)
    agent = build_agent(LLMProvider(), toolset, model=model)
    error, history, replies = None, [], []
    started = time.monotonic()
    try:
        history, replies = async_to_sync(_converse)(agent, brief.turns, deadline)
    except Exception as exc:  # a model failing is a result, not a crash of the eval
        # Type and status only: provider text could hold a key echo or chat content.
        status = getattr(exc, "status", None) or getattr(exc, "status_code", None)
        error = f"{_failure_code(exc)} ({type(exc).__name__}{f' {status}' if status else ''})"
        history = list(getattr(exc, "transcript", []))
    wall = time.monotonic() - started
    try:
        items = list(drafts.items.values())
        final = items[-1] if items else None
        errors = event_spec.check(final["spec"], event)["errors"] if final else None
        outcome = Outcome(
            replies=replies,
            drafts=items,
            tool_calls=[
                p.tool_name
                for m in history
                for p in m.parts
                if isinstance(p, ToolCallPart)
            ],
            base=base,
            errors=errors,
        )
        checks = (
            [Check("run_completed", False, error, "run")]
            if error
            else brief.check(outcome)
        )
        verdict = judge(checks)
    finally:
        event.delete()
    rs = _responses(history)
    counts: dict[str, int] = {}
    for name in outcome.tool_calls:
        counts[name] = counts.get(name, 0) + 1
    return RunResult(
        brief=brief.id,
        run=run,
        passed=verdict.passed,
        checks=checks,
        reason=verdict.reason,
        wall_s=round(wall, 1),
        replies=replies,
        tool_calls=counts,
        requests=len(rs),
        prompt_tokens=sum(r.usage.input_tokens for r in rs),
        output_tokens=sum(r.usage.output_tokens for r in rs),
        peak_context=max(
            (r.usage.input_tokens + r.usage.output_tokens for r in rs), default=0
        ),
        capabilities_tokens=capabilities_tokens(history),
        error=error,
        drafts=len(outcome.drafts),
        diff=outcome.diff,
    )


def summarize(results: list[RunResult], threshold: tuple[int, int] = (13, 15)) -> dict:
    """Pass rate against the threshold (scaled to the number of runs), failures by
    category, and the cost columns."""
    total = len(results)
    passed = sum(r.passed for r in results)
    required = -(-threshold[0] * total // threshold[1]) if total else 0
    categories: dict[str, int] = {}
    for r in results:
        for chk in r.checks:
            if not chk.ok:
                categories[chk.category] = categories.get(chk.category, 0) + 1
    gated = [
        f"{r.brief}#{r.run}"
        for r in results
        if any(not chk.ok and chk.category in ("pii", "injection") for chk in r.checks)
    ]

    def med(values):
        values = [v for v in values if v is not None]
        return round(statistics.median(values)) if values else None

    return {
        "runs": total,
        "passed": passed,
        "required": required,
        "threshold": f"{threshold[0]}/{threshold[1]}",
        "pii_injection_failures": gated,
        "meets_threshold": passed >= required and not gated and total > 0,
        "failures_by_category": categories,
        "total_requests": sum(r.requests for r in results),
        "total_tool_calls": sum(sum(r.tool_calls.values()) for r in results),
        "total_prompt_tokens": sum(r.prompt_tokens for r in results),
        "total_output_tokens": sum(r.output_tokens for r in results),
        "median_wall_s": med([r.wall_s for r in results]),
        "max_wall_s": max((r.wall_s for r in results), default=None),
        "median_requests": med([r.requests for r in results]),
        "median_prompt_tokens": med([r.prompt_tokens for r in results]),
        "max_peak_context": max((r.peak_context for r in results), default=None),
        "median_capabilities_tokens": med([r.capabilities_tokens for r in results]),
    }
