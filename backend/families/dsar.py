"""
GDPR data-subject-rights helpers (DSAR) and PII scrubbing.

Two distinct operations share PII logic here:

* Right to access / portability: ``build_family_export`` produces a complete
  JSON dump of everything Tryggare holds about a family (parents, children,
  check-in history, and the audit-log entries that touch those children).
* Right to erasure / retention: ``scrub_family`` and ``scrub_audit_logs_for_children``
  redact PII in place. Retention (``anonymize_expired_data``) calls these to
  anonymise inactive families while keeping rows for aggregate/safeguarding
  integrity; DSAR erasure scrubs the audit trail before hard-deleting the
  family itself.
"""

from __future__ import annotations

import csv
import io

from django.utils import timezone

REDACTED = "REDACTED"

# Keys inside AuditLog.details that embed child PII (written by checkins/views.py).
_AUDIT_PII_KEYS = ("child_name", "picked_up_by")


def build_family_export(family) -> dict:
    """
    Build a complete export of everything held about ``family``.

    Reuses the existing nested serializer for family/parent/child PII and
    appends check-in history and audit-log entries that reference the family's
    children. The result is JSON-serializable (DRF ``Response`` or
    ``json.dumps``).
    """
    # Imported here to avoid a circular import (serializers import models).
    from checkins.models import AuditLog, CheckInRecord
    from .serializers import FamilyDetailSerializer

    data = dict(FamilyDetailSerializer(family).data)

    child_ids = [str(c.id) for c in family.children.all()]

    checkins = (
        CheckInRecord.objects.filter(child__family=family)
        .select_related("child", "session", "check_in_staff", "check_out_staff")
        .order_by("check_in_time")
    )
    data["checkin_history"] = [
        {
            "id": str(r.id),
            "child_id": str(r.child_id),
            "child_name": f"{r.child.first_name} {r.child.last_name}",
            "session": r.session.name,
            "check_in_time": r.check_in_time.isoformat() if r.check_in_time else None,
            "check_out_time": r.check_out_time.isoformat()
            if r.check_out_time
            else None,
            "picked_up_by": r.picked_up_by or "",
            "supervised": r.supervised,
        }
        for r in checkins
    ]

    audit_logs = AuditLog.objects.filter(
        entity_type="CheckInRecord",
        details__child_id__in=child_ids,
    ).order_by("timestamp")
    data["audit_logs"] = [
        {
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "action": log.action,
            "entity_type": log.entity_type,
            "entity_id": log.entity_id,
            "details": log.details,
        }
        for log in audit_logs
    ]

    data["exported_at"] = timezone.now().isoformat()
    return data


def family_export_to_csv(export: dict) -> str:
    """
    Flatten a ``build_family_export`` dict into a single CSV document with a
    section per record type. Returned as a string for an HTTP attachment.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)

    writer.writerow(["Section", "Field", "Value"])
    for field in ("id", "last_name", "display_name", "last_participation_date"):
        writer.writerow(["family", field, export.get(field, "")])

    writer.writerow([])
    writer.writerow(["parent_name", "relationship", "phone", "email"])
    for parent in export.get("parents", []):
        writer.writerow(
            [
                parent.get("name", ""),
                parent.get("relationship_type", ""),
                parent.get("phone", ""),
                parent.get("email", ""),
            ]
        )

    writer.writerow([])
    writer.writerow(
        ["child_first_name", "child_last_name", "birthdate", "allergies", "notes"]
    )
    for child in export.get("children", []):
        writer.writerow(
            [
                child.get("first_name", ""),
                child.get("last_name", ""),
                child.get("birthdate", ""),
                child.get("allergies", ""),
                child.get("notes", ""),
            ]
        )

    writer.writerow([])
    writer.writerow(
        ["checkin_child", "session", "check_in_time", "check_out_time", "picked_up_by"]
    )
    for record in export.get("checkin_history", []):
        writer.writerow(
            [
                record.get("child_name", ""),
                record.get("session", ""),
                record.get("check_in_time", ""),
                record.get("check_out_time", ""),
                record.get("picked_up_by", ""),
            ]
        )

    return buffer.getvalue()


def scrub_family(family, *, when=None) -> None:
    """
    Redact all PII on ``family`` and its parents/children in place, and scrub
    PII embedded in related check-in records. Keeps rows, UUIDs, timestamps and
    foreign keys intact so aggregate/safeguarding history stays referentially
    sound. Sets ``anonymized_at`` so the operation is idempotent.

    Does NOT touch audit logs — call ``scrub_audit_logs_for_children`` for that
    (separated so callers can choose, and so the child id list is gathered once).
    """
    from checkins.models import CheckInRecord

    when = when or timezone.now()

    family.last_name = REDACTED
    family.anonymized_at = when
    family.save(update_fields=["last_name", "anonymized_at"])

    for parent in family.parents.all():
        parent.name = REDACTED
        parent.phone = None
        parent.email = None
        parent.save(update_fields=["name", "phone", "email"])

    for child in family.children.all():
        child.first_name = REDACTED
        child.last_name = REDACTED
        child.birthdate = None
        child.allergies = None
        child.notes = None
        child.anonymized_at = when
        child.save(
            update_fields=[
                "first_name",
                "last_name",
                "birthdate",
                "allergies",
                "notes",
                "anonymized_at",
            ]
        )

    CheckInRecord.objects.filter(
        child__family=family, picked_up_by__isnull=False
    ).update(picked_up_by=REDACTED)


def scrub_audit_logs_for_children(child_ids) -> int:
    """
    Redact PII (``child_name``, ``picked_up_by``) embedded in ``AuditLog.details``
    for the given child ids. Returns the number of log rows modified.

    ``child_ids`` may be UUIDs or strings; they are normalised to strings to
    match the JSON-stored ``details.child_id``.
    """
    from checkins.models import AuditLog

    child_ids = [str(cid) for cid in child_ids]
    if not child_ids:
        return 0

    logs = AuditLog.objects.filter(details__child_id__in=child_ids)
    modified = 0
    for log in logs:
        details = log.details or {}
        changed = False
        for key in _AUDIT_PII_KEYS:
            if details.get(key):
                details[key] = REDACTED
                changed = True
        if changed:
            log.details = details
            log.save(update_fields=["details"])
            modified += 1
    return modified
