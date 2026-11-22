"""Drafts, dedupe, merge and confirm. Nothing here is reachable without a person's
click (confirm) except filing a draft, which is never stored as confirmed."""

from django.db import transaction
from django.db.models import Q

from .models import FeatureRequest, FeatureRequestComment
from .rules import (
    INPUT_KEYS,
    REACH_THRESHOLDS,
    FeatureRequestError,
    clean_input,
    derive,
)


def can_file(user) -> bool:
    """Staff with event-change rights (decision 1). Administrators see all in the admin."""
    return bool(
        user is not None
        and user.is_authenticated
        and user.is_active
        and user.has_perm("events.change_event")
    )


def _reach_for_count(count: int) -> str:
    for minimum, label in REACH_THRESHOLDS:
        if count >= minimum:
            return label
    return "few_events"


def open_match(key: str, exclude_pk=None) -> FeatureRequest | None:
    """The oldest open request with this dedupe key that is not itself a duplicate."""
    rows = FeatureRequest.objects.filter(
        dedupe_key=key, status__in=FeatureRequest.OPEN_STATUSES
    )
    if exclude_pk is not None:
        rows = rows.exclude(pk=exclude_pk)
    return rows.order_by("pk").first()


def drafts_for(event, user):
    return FeatureRequest.objects.filter(
        event=event, filed_by=user, status="draft"
    ).order_by("pk")


def serialize(fr: FeatureRequest) -> dict:
    """What an organizer reviews, and what the WebSocket and tool report. No local fields."""
    match = open_match(fr.dedupe_key, exclude_pk=fr.pk)
    return {
        "id": fr.public_id,
        "title": fr.title,
        "problem": fr.problem,
        "desired": fr.desired,
        "tried": list(fr.tried or []),
        "workaround": fr.workaround,
        "brief_fragment": fr.brief_fragment,
        "touches": list(fr.touches),
        "severity": fr.severity,
        "matches_existing": (
            {"id": match.public_id, "seen": match.seen} if match else None
        ),
    }


def _stored_input(fr: FeatureRequest) -> dict:
    return {
        "title": fr.title,
        "problem": fr.problem,
        "desired": fr.desired,
        "tried": list(fr.tried or []),
        "workaround": fr.workaround,
        "brief_fragment": fr.brief_fragment,
        "touches": list(fr.touches),
        "severity": fr.severity,
    }


def _apply(fr: FeatureRequest, cleaned: dict) -> None:
    for name in INPUT_KEYS:
        setattr(fr, name, cleaned[name])
    for name, value in derive(cleaned).items():
        setattr(fr, name, value)


def reach_of(fr: FeatureRequest) -> str:
    """Distinct events among the request, and the requests merged into it."""
    events = (
        FeatureRequest.objects.filter(Q(pk=fr.pk) | Q(duplicate_of_id=fr.pk))
        .exclude(event=None)
        .values("event_id")
        .distinct()
        .count()
    )
    return _reach_for_count(max(events, 1))


def file_draft(
    event, user, data: dict, source: str
) -> tuple[FeatureRequest, dict | None]:
    """Store a draft. ``(request, matches_existing)``; raises FeatureRequestError."""
    fr = FeatureRequest(source=source, event=event, filed_by=user)
    _apply(fr, clean_input(data))
    match = open_match(fr.dedupe_key)
    fr.reach = _reach_for_count(_events_with_key(fr.dedupe_key, event_pk=fr.event_id))
    fr.save()
    return fr, ({"id": match.public_id, "seen": match.seen} if match else None)


def _events_with_key(key: str, event_pk=None) -> int:
    """Events that hit this key: the open requests' events, plus ``event_pk``."""
    events = set(
        FeatureRequest.objects.filter(
            dedupe_key=key, status__in=FeatureRequest.OPEN_STATUSES
        )
        .exclude(event=None)
        .values_list("event_id", flat=True)
    )
    if event_pk is not None:
        events.add(event_pk)
    return len(events)


def _merge_body(source: FeatureRequest) -> str:
    lines = [
        source.title,
        "",
        f"Problem: {source.problem}",
        f"Desired: {source.desired}",
    ]
    if source.workaround:
        lines.append(
            f"Workaround: {source.workaround['used']} (cost: {source.workaround['cost']})"
        )
    lines += [f"Tried: {item}" for item in source.tried or []]
    return "\n".join(lines)


def merge_into(source: FeatureRequest, target: FeatureRequest, by) -> FeatureRequest:
    """Mark ``source`` a duplicate of ``target``: seen goes up, evidence is appended,
    and the source's free text becomes a maintainer comment on ``target``."""
    if source.pk == target.pk or target.status not in FeatureRequest.OPEN_STATUSES:
        raise FeatureRequestError(
            [
                {
                    "path": "duplicate_of",
                    "code": "invalid_target",
                    "message": "Choose an open request.",
                }
            ]
        )
    with transaction.atomic():
        target = FeatureRequest.objects.select_for_update().get(pk=target.pk)
        if target.status not in FeatureRequest.OPEN_STATUSES:
            raise FeatureRequestError(
                [
                    {
                        "path": "duplicate_of",
                        "code": "invalid_target",
                        "message": "Choose an open request.",
                    }
                ]
            )
        FeatureRequestComment.objects.create(
            request=target, body=_merge_body(source), author=by
        )
        evidence = list(target.evidence or [])
        evidence += [e for e in source.evidence or [] if e not in evidence]
        target.evidence = evidence
        target.seen += 1
        target.save(update_fields=["seen", "evidence"])
        source.status = "duplicate"
        source.duplicate_of = target
        source.save(update_fields=["status", "duplicate_of"])
        target.reach = reach_of(target)
        target.save(update_fields=["reach"])
    return target


def confirm(fr: FeatureRequest, user, edits: dict | None = None) -> FeatureRequest:
    """Store a draft as confirmed, or merge it into an open match. ``edits`` replace the
    stored input, and the same checks run again on the whole."""
    with transaction.atomic():
        # Locked and re-read: two clicks on one draft must not merge it twice.
        locked = (
            FeatureRequest.objects.select_for_update()
            .filter(pk=fr.pk, status="draft")
            .first()
        )
        if locked is None:
            raise FeatureRequestError(
                [
                    {
                        "path": "",
                        "code": "not_a_draft",
                        "message": "Only a draft can be confirmed.",
                    }
                ]
            )
        fr = locked
        cleaned = clean_input({**_stored_input(fr), **(edits or {})})
        _apply(fr, cleaned)
        match = open_match(fr.dedupe_key, exclude_pk=fr.pk)
        fr.confirmed_by = user
        if match is not None:
            fr.save()
            return merge_into(fr, match, user)
        fr.status = "confirmed"
        fr.reach = _reach_for_count(_events_with_key(fr.dedupe_key, fr.event_id))
        fr.save()
        return fr


def discard(fr: FeatureRequest) -> None:
    """Drafts only: a discarded draft leaves nothing behind."""
    if fr.status == "draft":
        fr.delete()
