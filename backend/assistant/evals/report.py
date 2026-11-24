"""JSON and markdown reports of an eval run."""

import dataclasses
import statistics

from .harness import step_rates


def build_report(meta: dict, results, summary: dict) -> dict:
    return {
        "meta": meta,
        "summary": summary,
        "runs": [dataclasses.asdict(r) for r in results],
    }


_REPORTED_LABEL = {
    "hygiene": "hygiene clean",
    "language": "language clean",
    "pii_echo": "no name echoed in the reply",
}


def _med(values):
    values = [v for v in values if v is not None]
    return round(statistics.median(values), 1) if values else None


def _p90(values):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    # Nearest rank: the smallest value with at least 90% of the values at or below it.
    return round(values[-(-9 * len(values) // 10) - 1], 1)


def timing_lines(runs: list[dict]) -> list[str]:
    """The Timing section; empty for result files from before steps were recorded.
    A step without usage counts for the TTFT but not the rates (shown as n/a)."""
    if not any(r.get("steps") for r in runs):
        return []

    def collect(rs):
        steps = [st for r in rs for st in r.get("steps", [])]
        rates = [step_rates(st) for st in steps]
        return (
            [st["ttft_s"] for st in steps],
            [x[0] for x in rates],
            [x[1] for x in rates],
        )

    ttft, out_rate, in_rate = collect(runs)
    walls = [r["wall_s"] for r in runs]
    n = sum(len(r.get("steps", [])) for r in runs)
    unmeasured = sum(
        st.get("output_tokens") is None for r in runs for st in r.get("steps", [])
    )
    na = lambda v: "n/a" if v is None else v  # noqa: E731
    lines = [
        "",
        "## Timing",
        "",
        f"{n} model steps (streamed, as in production). TTFT: request start to the first "
        "text or tool-call delta. Output tok/s: step output tokens over decode time "
        "(TTFT to end), so thinking tokens count. Input tok/s: prompt tokens over TTFT "
        f"(an upper bound under prompt caching). Steps without provider usage: {unmeasured}.",
        "",
        "| | median | p90 |",
        "| --- | --- | --- |",
        f"| TTFT s | {na(_med(ttft))} | {na(_p90(ttft))} |",
        f"| output tok/s | {na(_med(out_rate))} | {na(_p90(out_rate))} |",
        f"| input tok/s | {na(_med(in_rate))} | {na(_p90(in_rate))} |",
        f"| wall s per run | {na(_med(walls))} | {na(_p90(walls))} |",
        "",
        "| brief | runs | median wall s | median TTFT s | median output tok/s |",
        "| --- | --- | --- | --- | --- |",
    ]
    for brief in dict.fromkeys(r["brief"] for r in runs):
        rs = [r for r in runs if r["brief"] == brief]
        t, o, _ = collect(rs)
        lines.append(
            f"| {brief} | {len(rs)} | {na(_med([r['wall_s'] for r in rs]))} | "
            f"{na(_med(t))} | {na(_med(o))} |"
        )
    return lines


def render_markdown(report: dict) -> str:
    meta, s = report["meta"], report["summary"]
    verdict = "MEETS" if s["meets_threshold"] else "DOES NOT MEET"
    lines = [
        f"# Assistant eval: {meta['model']}",
        "",
        f"- Provider: {meta['base_url']}; started {meta['started']}; runs per brief {meta['runs_per_brief']}",
        f"- Code: commit {meta.get('git_commit') or 'unknown'}"
        + (" (uncommitted changes)" if meta.get("git_dirty") else "")
        + f"; system prompt sha256 {(meta.get('system_prompt') or {}).get('sha256', 'unknown')}"
        + f"; tool definitions sha256 {(meta.get('tools') or {}).get('sha256', 'unknown')}",
        f"- Context configured (Ollama num_ctx): {meta.get('num_ctx') or 'unknown'}",
        f"- `get_capabilities` payload: {meta['capabilities']['chars']} chars "
        f"(about {meta['capabilities']['approx_tokens']} tokens); measured prompt cost "
        f"{s['median_capabilities_tokens']} tokens (median)",
        *(
            [
                f"- System prompt (sent every request): {meta['system_prompt']['chars']} chars "
                f"(about {meta['system_prompt']['approx_tokens']} tokens)"
            ]
            if meta.get("system_prompt")
            else []
        ),
        "",
        f"**{verdict} the pass bar {s['pass_bar']}**: {s['passed']}/{s['runs']} substance passes "
        f"(need {s['required']}); PII (in a draft or feature request) / injection failures: "
        f"{len(s['pii_injection_failures'])}"
        + (
            f" ({', '.join(s['pii_injection_failures'])})"
            if s["pii_injection_failures"]
            else ""
        ),
        f"- Reported, not gating: hygiene, language and PII echo clean in {s['reported_clean_runs']}/{s['runs']} runs"
        + "".join(
            f"; {_REPORTED_LABEL.get(cat, cat)} {n}/{s['runs']}"
            for cat, n in (s.get("reported_clean_by_category") or {}).items()
        )
        + f"; failures {s['reported_failures'] or 'none'}; "
        f"graded score {s['graded_score'] if s['graded_score'] is not None else 'n/a'}",
        "",
        *(
            [
                f"- Refusals: {s['refusal_hits'][0]}/{s['refusal_hits'][1]} turns with personal data refused; "
                f"over-refusals {s['not_over_refused'][1] - s['not_over_refused'][0]}/{s['not_over_refused'][1]} "
                "runs of briefs without personal data"
            ]
            if "refusal_hits" in s
            else []
        ),
        f"- Wall: median {s['median_wall_s']} s, max {s['max_wall_s']} s",
        f"- Requests per run (median): {s['median_requests']}; prompt tokens per run (median): "
        f"{s['median_prompt_tokens']}; peak context used: {s['max_peak_context']}",
        f"- Totals (for cost): {s['total_requests']} requests, {s['total_tool_calls']} tool calls, "
        f"{s['total_prompt_tokens']} prompt tokens, {s['total_output_tokens']} output tokens",
        f"- Failed checks by category: {s['failures_by_category'] or 'none'}",
        "",
        "| brief | run | result | wall s | tool calls | requests | prompt tok | peak ctx | caps tok | why | reported | graded |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in report["runs"]:
        calls = sum(r["tool_calls"].values())
        why = (r["reason"] or "").replace("|", "/")
        graded = [c for c in r.get("graded", [])]
        score = f"{sum(c['ok'] for c in graded)}/{len(graded)}" if graded else "-"
        lines.append(
            f"| {r['brief']} | {r['run']} | {'pass' if r['passed'] else 'FAIL'} | {r['wall_s']} | "
            f"{calls} | {r['requests']} | {r['prompt_tokens']} | {r['peak_context']} | "
            f"{r['capabilities_tokens'] or '-'} | {why} | {', '.join(r.get('reported', [])) or '-'} | {score} |"
        )
    lines += timing_lines(report["runs"])
    return "\n".join(lines) + "\n"
