"""Copy as GitHub issue": markdown in the sections of .github/ISSUE_TEMPLATE/feature_request.md
and a prefilled link. The server makes no request; the operator's browser opens the link.
Local-only fields (event, people, times, comments) never reach this module's output."""

from urllib.parse import quote, urlencode

ISSUE_URL = "https://github.com/jswetzen/tryggare/issues/new"
# Browsers and GitHub truncate long URLs; past this the link is omitted, not cut.
MAX_LINK_CHARS = 7500
NOTICE = (
    "Check before posting: no names, personnummer, contact or health details. "
    "Describe the rule, not the people."
)
UNCAPTURED = "_Not recorded locally. Answer it before posting._"


def _bullets(items) -> str:
    return "\n".join(f"- {item}" for item in items)


def render(fr) -> dict:
    """``{"title", "body", "url"}``; ``url`` is None when it would be too long."""
    title = f"[Feature] {fr.title}"
    alternatives = []
    if fr.tried:
        alternatives.append(_bullets(fr.tried))
    if fr.workaround:
        alternatives.append(
            f"Workaround used: {fr.workaround['used']} (cost: {fr.workaround['cost']})"
        )
    context = [
        f"Severity: {fr.get_severity_display()}",
        f"Reach: {fr.get_reach_display()}",
        f"Source: {fr.get_source_display()}",
        f"Seen: {fr.seen} time{'s' if fr.seen != 1 else ''}",
        f"Touches: {', '.join(f'`{t}`' for t in fr.touches)}",
    ]
    if fr.layers:
        context.append(f"Layers: {', '.join(fr.layers)}")
    if fr.brief_fragment:
        context.append(f"Brief: {fr.brief_fragment}")
    if fr.evidence:
        refs = ", ".join(f"`{e['ref']}`" for e in fr.evidence)
        context.append(f"Evidence: {refs}")
    context.append(f"Dedupe key: `{fr.dedupe_key}`")
    body = "\n\n".join(
        [
            f"> {NOTICE}",
            f"## Problem description / use case\n\n{fr.problem}",
            f"## Proposed solution\n\n{fr.desired}",
            "## Alternatives considered\n\n" + ("\n\n".join(alternatives) or "_None._"),
            f"## Is this for a specific church or event type?\n\n{UNCAPTURED}",
            "## Additional context\n\n" + "\n".join(f"- {line}" for line in context),
        ]
    )
    labels = ",".join(["enhancement", f"fr:{fr.dedupe_key}"])
    link = f"{ISSUE_URL}?{urlencode({'title': title, 'body': body, 'labels': labels}, quote_via=quote)}"
    return {
        "title": title,
        "body": body,
        "url": link if len(link) <= MAX_LINK_CHARS else None,
    }
