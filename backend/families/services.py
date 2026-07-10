"""Plain-ORM family-creation logic shared by the staff and public registration paths.

No DRF coupling here (matches the `reports/services.py` naming convention) —
callers own validation; this just materializes rows.
"""

from django.conf import settings
from django.utils import timezone

from .models import Child, Family, Parent


def create_family_with_members(
    *,
    last_name: str = "",
    parents_data: list[dict],
    children_data: list[dict],
    consent_attestor_email: str | None = None,
) -> tuple[Family, list[Parent], list[Child]]:
    """Create a new Family with nested Parent/Child rows.

    Returns ``(family, created_parents, created_children)`` — both lists in
    the same order as ``parents_data``/``children_data`` — so a caller can
    zip its input dicts against the actual created rows. This matters
    because ``Attendee.id`` is a random UUID primary key with no
    ``Meta.ordering`` on ``Parent``/``Child``: re-querying
    ``family.parents.all()`` afterwards is not guaranteed to preserve
    creation order, so callers that need to attach more per-attendee data
    (e.g. a self-serve registration's ticket type/extras selections) must
    use these returned lists rather than re-fetching.

    ``consent_attestor_email``, when given, designates which of the parents
    being created here attests to any child health-data consent decision —
    matched against ``parents_data[*]["email"]``. This matters for a
    two-guardian public registration submission, where whoever verified their
    email may not be the first parent listed in the form. Falls back to the
    first created parent (the long-standing staff-flow default, since the
    staff form has no equivalent "which guardian is present" signal) when
    omitted or when no parent in this submission has a matching email.
    """
    family = Family.objects.create(last_name=last_name)

    created_parents = [
        Parent.objects.create(family=family, **parent_data)
        for parent_data in parents_data
    ]

    consented_by = None
    if consent_attestor_email:
        consented_by = next(
            (p for p in created_parents if p.email == consent_attestor_email),
            None,
        )
    if consented_by is None:
        consented_by = created_parents[0] if created_parents else None

    created_children = []
    for child_data in children_data:
        status = child_data.get(
            "health_consent_status", Child.HealthConsentStatus.NOT_APPLICABLE
        )
        if status in (
            Child.HealthConsentStatus.GRANTED,
            Child.HealthConsentStatus.DECLINED,
        ):
            child_data["health_consent_by"] = consented_by
            child_data["health_consent_at"] = timezone.now()
            child_data["health_consent_notice_version"] = (
                settings.HEALTH_CONSENT_NOTICE_VERSION
            )
        created_children.append(Child.objects.create(family=family, **child_data))

    return family, created_parents, created_children
