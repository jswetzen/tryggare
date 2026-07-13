"""Plain-ORM family-creation logic shared by the staff and public registration paths.

No DRF coupling here (matches the `reports/services.py` naming convention) —
callers own validation; this just materializes rows.
"""

from django.conf import settings
from django.utils import timezone

from .models import Child, Family, Parent

_LIVE_CONSENT_STATUSES = ("granted", "declined")


def _resolve_health_consent_stamp(
    *, old_status: str, new_status: str, consented_by: Parent | None
) -> dict | None:
    """Fields to apply when a consent decision is actually changing, or
    ``None`` if it isn't. A brand-new row's ``old_status`` is
    ``not_applicable`` (the model default), so a first-time granted/declined
    submission always stamps — same as an existing row's status genuinely
    changing. Editing an unrelated field (or allergy/note text under an
    already-decided consent) must never silently move the attestation
    timestamp forward.
    """
    if new_status in _LIVE_CONSENT_STATUSES and new_status != old_status:
        return {
            "health_consent_by": consented_by,
            "health_consent_at": timezone.now(),
            "health_consent_notice_version": settings.HEALTH_CONSENT_NOTICE_VERSION,
        }
    return None


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
            (
                p
                for p in created_parents
                if p.email and p.email.lower() == consent_attestor_email.lower()
            ),
            None,
        )
    if consented_by is None:
        consented_by = created_parents[0] if created_parents else None

    # Parents' own health-data consent (allergies/notes) is attested by
    # whoever is present submitting the form on behalf of the whole party —
    # same `consented_by` as children's, since a per-adult self-attestation
    # link doesn't exist until Phase 4 self-service edit is built. Applied
    # as a post-creation update (not passed into Parent.objects.create
    # above) because resolving `consented_by` itself depends on the parents
    # already existing.
    for parent in created_parents:
        stamp = _resolve_health_consent_stamp(
            old_status=Parent.HealthConsentStatus.NOT_APPLICABLE,
            new_status=parent.health_consent_status,
            consented_by=consented_by,
        )
        if stamp:
            for field, value in stamp.items():
                setattr(parent, field, value)
            parent.save(update_fields=list(stamp.keys()))

    created_children = []
    for child_data in children_data:
        child_data = dict(child_data)
        status = child_data.get(
            "health_consent_status", Child.HealthConsentStatus.NOT_APPLICABLE
        )
        stamp = _resolve_health_consent_stamp(
            old_status=Child.HealthConsentStatus.NOT_APPLICABLE,
            new_status=status,
            consented_by=consented_by,
        )
        if stamp:
            child_data.update(stamp)
        created_children.append(Child.objects.create(family=family, **child_data))

    return family, created_parents, created_children


def update_family_with_members(
    *,
    family: Family,
    last_name: str | None = None,
    parents_data: list[dict] | None = None,
    children_data: list[dict] | None = None,
    consent_attestor_email: str | None = None,
) -> tuple[Family, list[Parent], list[Child]]:
    """Update a Family in place: change ``last_name`` if given, and upsert
    each dict in ``parents_data``/``children_data`` — an ``"id"`` key updates
    that existing row (must already belong to ``family``, raises
    ``ValueError`` otherwise — never silently re-parents another family's
    member), no ``"id"`` creates a new row attached to ``family``. Members
    not mentioned in either list are left completely untouched: this
    function only ever creates or updates, never deletes, which is what
    makes "no removal via this path" true by construction rather than a
    documented-but-unenforced rule.

    Mirrors ``create_family_with_members``'s consent-attestor resolution
    (see there for the "whoever is present" rationale), except the
    candidate pool is the family's *current* full parent list (existing +
    any touched by this call) rather than only the parents in this
    submission, since an edit that only touches a child still needs a
    plausible attestor. Consent is only re-stamped when the decision is
    actually changing (via ``_resolve_health_consent_stamp``) — editing an
    unrelated field, or allergy/note text under an already-decided consent,
    must never silently move the attestation timestamp forward.
    """
    if last_name is not None:
        family.last_name = last_name
        family.save(update_fields=["last_name"])

    parents_data = parents_data or []
    children_data = children_data or []

    touched_parents: list[tuple[Parent, str]] = []
    for data in parents_data:
        data = dict(data)
        parent_id = data.pop("id", None)
        if parent_id:
            try:
                parent = family.parents.get(id=parent_id)
            except Parent.DoesNotExist:
                raise ValueError(
                    f"Parent {parent_id} does not belong to family {family.id}"
                )
            old_status = parent.health_consent_status
            for field, value in data.items():
                setattr(parent, field, value)
        else:
            parent = Parent(family=family, **data)
            old_status = Parent.HealthConsentStatus.NOT_APPLICABLE
        touched_parents.append((parent, old_status))

    touched_parent_ids = {p.id for p, _ in touched_parents if p.id}
    all_parents = [p for p, _ in touched_parents] + [
        p for p in family.parents.all() if p.id not in touched_parent_ids
    ]

    consented_by = None
    if consent_attestor_email:
        consented_by = next(
            (
                p
                for p in all_parents
                if p.email and p.email.lower() == consent_attestor_email.lower()
            ),
            None,
        )
    if consented_by is None:
        consented_by = all_parents[0] if all_parents else None

    updated_parents = []
    for parent, old_status in touched_parents:
        stamp = _resolve_health_consent_stamp(
            old_status=old_status,
            new_status=parent.health_consent_status,
            consented_by=consented_by,
        )
        if stamp:
            for field, value in stamp.items():
                setattr(parent, field, value)
        parent.save()
        updated_parents.append(parent)

    updated_children = []
    for data in children_data:
        data = dict(data)
        child_id = data.pop("id", None)
        if child_id:
            try:
                child = family.children.get(id=child_id)
            except Child.DoesNotExist:
                raise ValueError(
                    f"Child {child_id} does not belong to family {family.id}"
                )
            old_status = child.health_consent_status
            for field, value in data.items():
                setattr(child, field, value)
        else:
            child = Child(family=family, **data)
            old_status = Child.HealthConsentStatus.NOT_APPLICABLE

        stamp = _resolve_health_consent_stamp(
            old_status=old_status,
            new_status=child.health_consent_status,
            consented_by=consented_by,
        )
        if stamp:
            for field, value in stamp.items():
                setattr(child, field, value)
        child.save()
        updated_children.append(child)

    return family, updated_parents, updated_children
