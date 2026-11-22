"""JSON and markdown reports of an eval run."""

import dataclasses


def build_report(meta: dict, results, summary: dict) -> dict:
    return {
        "meta": meta,
        "summary": summary,
        "runs": [dataclasses.asdict(r) for r in results],
    }


def render_markdown(report: dict) -> str:
    meta, s = report["meta"], report["summary"]
    verdict = "MEETS" if s["meets_threshold"] else "DOES NOT MEET"
    lines = [
        f"# Assistant eval: {meta['model']}",
        "",
        f"- Provider: {meta['base_url']}; started {meta['started']}; runs per brief {meta['runs_per_brief']}",
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
        f"**{verdict} the threshold {s['threshold']}**: {s['passed']}/{s['runs']} runs passed "
        f"(need {s['required']}); PII/injection failures: {len(s['pii_injection_failures'])}"
        + (
            f" ({', '.join(s['pii_injection_failures'])})"
            if s["pii_injection_failures"]
            else ""
        ),
        "",
        f"- Wall: median {s['median_wall_s']} s, max {s['max_wall_s']} s",
        f"- Requests per run (median): {s['median_requests']}; prompt tokens per run (median): "
        f"{s['median_prompt_tokens']}; peak context used: {s['max_peak_context']}",
        f"- Totals (for cost): {s['total_requests']} requests, {s['total_tool_calls']} tool calls, "
        f"{s['total_prompt_tokens']} prompt tokens, {s['total_output_tokens']} output tokens",
        f"- Failed checks by category: {s['failures_by_category'] or 'none'}",
        "",
        "| brief | run | result | wall s | tool calls | requests | prompt tok | peak ctx | caps tok | why |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in report["runs"]:
        calls = sum(r["tool_calls"].values())
        why = (r["reason"] or "").replace("|", "/")
        lines.append(
            f"| {r['brief']} | {r['run']} | {'pass' if r['passed'] else 'FAIL'} | {r['wall_s']} | "
            f"{calls} | {r['requests']} | {r['prompt_tokens']} | {r['peak_context']} | "
            f"{r['capabilities_tokens'] or '-'} | {why} |"
        )
    return "\n".join(lines) + "\n"
